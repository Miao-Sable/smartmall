"""匹配度评分与过敏源匹配（核心业务规则，可解释红黄绿版本）

规则见 README「业务规则」与「差异化创新」：
- 基础 100 分；命中一种过敏源 -40；违反一项饮食偏好 -10；命中偏好标签 +5
- 营养警示：高糖（碳水 >= 60g）/-5、高钠（钠 >= 600mg）/-5、高脂（脂肪 >= 20g）/-5
- 价格：最新价低于近期均价 10% 以上 +5，高于 10% 以上 -5
- 红黄绿：命中过敏源 -> 红；score>=70 绿；50<=score<70 黄；score<50 红
- 90-100 非常适合 / 70-89 比较适合 / 50-69 一般 / 0-49 不适合
"""
from sqlmodel import Session, select

from app.models.user import Allergen, DietPreference, UserAllergen, UserDiet
from app.services.mock_data import load_price_history

# 红黄绿交通灯中文文案（唯一来源，前后端保持一致）
LIGHT_LABELS = {"green": "适合", "yellow": "谨慎", "red": "不建议"}


def light_label(light: str) -> str:
    return LIGHT_LABELS.get(light, "适合")


def load_user_allergens(session: Session, user_id: int) -> list[dict]:
    rows = session.exec(
        select(Allergen)
        .join(UserAllergen, UserAllergen.allergen_id == Allergen.id)
        .where(UserAllergen.user_id == user_id)
    ).all()
    return [{"name": a.name, "keywords": a.keywords or []} for a in rows]


def load_user_diets(session: Session, user_id: int) -> list[dict]:
    rows = session.exec(
        select(DietPreference)
        .join(UserDiet, UserDiet.diet_id == DietPreference.id)
        .where(UserDiet.user_id == user_id)
    ).all()
    return [{"name": d.name, "keywords": d.keywords or []} for d in rows]


def match_allergens(ingredients: list[str], user_allergens: list[dict]) -> list[dict]:
    """关键词匹配：命中返回 [{allergen_name, ingredient}]"""
    hits: list[dict] = []
    for ing in ingredients:
        for allergen in user_allergens:
            if any(kw in ing for kw in allergen["keywords"]):
                hits.append({"allergen_name": allergen["name"], "ingredient": ing})
    return hits


def match_diets(ingredients: list[str], tags: list[str], user_diets: list[dict]) -> list[str]:
    """返回被违反的饮食偏好名称列表（仅名称，用于软提示）。"""
    return [d["name"] for d in user_diets if violates_diet(ingredients, tags, d)]


def violates_diet(ingredients: list[str], tags: list[str], diet: dict) -> bool:
    """简单关键词判断：商品标签明确符合偏好（如“低糖”）视为不违规"""
    if diet["name"] in tags:
        return False
    return any(kw in ing for ing in ingredients for kw in diet["keywords"])


def score_level(score: int) -> str:
    if score >= 90:
        return "非常适合"
    if score >= 70:
        return "比较适合"
    if score >= 50:
        return "一般"
    return "不适合"


def _light_of(hits: list[dict], score: int) -> tuple[str, str]:
    """返回 (traffic_light, traffic_label)。命中过敏源一律红牌。"""
    if hits:
        light = "red"
    elif score >= 70:
        light = "green"
    elif score >= 50:
        light = "yellow"
    else:
        light = "red"
    return light, light_label(light)


def _nutrition_warnings(nutrition: list[dict]) -> list[dict]:
    """营养阈值判断，返回 [{type, label, delta}]。注意钠单位为 mg。"""
    reasons: list[dict] = []
    rules = [
        ("碳水化合物", 60.0, "碳水化合物偏高（高糖）"),
        ("钠", 600.0, "钠含量偏高"),
        ("脂肪", 20.0, "脂肪偏高"),
    ]
    by_name = {n["name"]: n for n in nutrition}
    for name, threshold, label in rules:
        item = by_name.get(name)
        if item is None:
            continue
        try:
            value = float(item["value"])
        except (TypeError, ValueError):
            continue
        if value >= threshold:
            reasons.append({"type": "nutrition", "label": f"{label}（{value:.0f}{item['unit']}/100g）", "delta": -5})
    return reasons


def _price_reason(product_id: int) -> dict | None:
    """价格相对近期均价判断，返回 {type, label, delta} 或 None"""
    history = load_price_history(product_id)
    points = history["points"] if history else []
    if len(points) < 2:
        return None
    prices = [p["price"] for p in points]
    latest, avg = prices[-1], sum(prices) / len(prices)
    if latest < avg * 0.9:
        return {"type": "price", "label": f"当前价 ¥{latest:.1f} 低于近期均价", "delta": 5}
    if latest > avg * 1.1:
        return {"type": "price", "label": f"当前价 ¥{latest:.1f} 高于近期均价", "delta": -5}
    return None


def analyze_product(product: dict, user_allergens: list[dict], user_diets: list[dict]) -> dict:
    ingredients = product.get("ingredients", [])
    tags = product.get("tags", [])
    nutrition = product.get("nutrition", [])
    reasons: list[dict] = []

    # 过敏源：每命中一种 -40（同种过敏源命中多个成分只扣一次，但明细保留全部成分）
    hits = match_allergens(ingredients, user_allergens)
    by_allergen: dict[str, list[str]] = {}
    for h in hits:
        by_allergen.setdefault(h["allergen_name"], []).append(h["ingredient"])
    for name, ings in by_allergen.items():
        reasons.append({"type": "allergen", "label": f"含{name}：{'、'.join(ings)}", "delta": -40})

    # 饮食偏好：标签匹配 +5，关键词违规 -10
    for diet in user_diets:
        if diet["name"] in tags:
            reasons.append({"type": "diet", "label": f"含「{diet['name']}」标签，符合偏好", "delta": 5})
        elif violates_diet(ingredients, tags, diet):
            reasons.append({"type": "diet", "label": f"不符合「{diet['name']}」饮食偏好", "delta": -10})

    # 营养警示
    reasons.extend(_nutrition_warnings(nutrition))

    # 价格
    price_reason = _price_reason(product.get("id"))
    if price_reason:
        reasons.append(price_reason)

    score = max(0, min(100, 100 + sum(r["delta"] for r in reasons)))
    light, label = _light_of(hits, score)

    return {
        "score": score,
        "level": score_level(score),
        "traffic_light": light,
        "traffic_label": label,
        "allergen_hits": hits,
        "reasons": reasons,
        "recommended": light == "green",
    }
