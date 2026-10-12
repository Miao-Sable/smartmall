"""购物清单预检与重匹配（rematch）。

规则见 README「差异化创新 · 购物清单预检」：
- 商品名先精确匹配、再模糊匹配（包含关系）；查不到标记 not_found，不报错
- 命中用户过敏源 -> 高风险，推荐同品类、不含任一用户过敏源的替代品（最多 2 个）
- 饮食偏好违规仅作为 diet_hits 软提示，不影响高风险判定与替代推荐
- rematch：返回该商品名的其它候选（排除已看过的 id，最多 2 个，不足按实际）
"""
from sqlmodel import Session

from app.services.matching import load_user_allergens, load_user_diets, match_allergens, match_diets
from app.services.mock_data import latest_price, load_products, match_product

MAX_ALTERNATIVES = 2
REMATCH_BATCH = 2


def _brief(product: dict) -> dict:
    """商品精简信息：id / 名称 / 条码 / 品类 / 当前价"""
    return {
        "id": product.get("id"),
        "name": product.get("name", ""),
        "barcode": product.get("barcode", ""),
        "category": product.get("category", ""),
        "price": latest_price(product.get("id")),
    }


def precheck_items(session: Session, user_id: int, names: list[str]) -> list[dict]:
    allergens = load_user_allergens(session, user_id)
    diets = load_user_diets(session, user_id)
    return [precheck_one(name, allergens, diets) for name in names if (name or "").strip()]


def precheck_one(name: str, allergens: list[dict], diets: list[dict]) -> dict:
    name = name.strip()
    match_type, candidates = match_product(name)
    if match_type == "not_found":
        return {
            "name": name,
            "match_type": "not_found",
            "product": None,
            "is_high_risk": False,
            "allergen_hits": [],
            "diet_hits": [],
            "alternatives": [],
        }

    product = candidates[0]
    hits = match_allergens(product.get("ingredients", []), allergens)
    diet_hits = match_diets(product.get("ingredients", []), product.get("tags", []), diets)
    alternatives = find_alternatives(product, allergens) if hits else []

    return {
        "name": name,
        "match_type": match_type,
        "product": _brief(product),
        "is_high_risk": bool(hits),
        "allergen_hits": hits,
        "diet_hits": diet_hits,
        "alternatives": alternatives,
    }


def find_alternatives(product: dict, allergens: list[dict]) -> list[dict]:
    """同品类、不含任一用户过敏源的替代品，最多 MAX_ALTERNATIVES 个"""
    result: list[dict] = []
    category = product.get("category", "")
    for candidate in load_products():
        if candidate.get("id") == product.get("id"):
            continue
        if candidate.get("category") != category:
            continue
        if match_allergens(candidate.get("ingredients", []), allergens):
            continue
        result.append(_brief(candidate))
        if len(result) >= MAX_ALTERNATIVES:
            break
    return result


def rematch_candidates(name: str, exclude_ids: list[int]) -> list[dict]:
    """返回该商品名匹配到、且不在 exclude_ids 里的候选，最多 REMATCH_BATCH 个；没有则空数组"""
    _, candidates = match_product(name)
    excluded = set(exclude_ids or [])
    result: list[dict] = []
    for c in candidates:
        if c.get("id") in excluded:
            continue
        result.append(_brief(c))
        if len(result) >= REMATCH_BATCH:
            break
    return result
