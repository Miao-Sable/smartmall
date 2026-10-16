"""MVP 商品数据：从本地 mock JSON 读取。

后续接入真实商品 API（阿里云、聚合数据等）时，替换本模块实现即可，
routers 层无需改动。
"""
import json
from functools import lru_cache

from app.core.config import settings


@lru_cache(maxsize=None)
def _load(name: str) -> list:
    with open(settings.mock_dir / name, encoding="utf-8") as f:
        return json.load(f)


def find_product_by_barcode(barcode: str) -> dict | None:
    for product in _load("products.json"):
        if str(product.get("barcode")) == str(barcode):
            return product
    return None


def find_product_by_id(product_id: int) -> dict | None:
    for product in _load("products.json"):
        if product.get("id") == product_id:
            return product
    return None


def load_price_history(product_id: int) -> dict | None:
    for item in _load("price_history.json"):
        if item.get("product_id") == product_id:
            return item
    return None


def load_allergens() -> list:
    return _load("allergens.json")


def load_diet_preferences() -> list:
    return _load("diet_preferences.json")


def load_scenario_templates() -> list:
    return _load("scenario_templates.json")


def load_products() -> list:
    return _load("products.json")


def match_product(name: str) -> tuple[str, list[dict]]:
    """按商品名匹配，返回 (match_type, candidates)。

    match_type：exact / fuzzy / not_found
    - exact：商品名与输入完全相等（忽略大小写与首尾空白）
    - fuzzy：包含关系（输入含于商品名，或商品名含于输入）
    - not_found：无匹配

    candidates 按 mock 原始顺序（同 id 顺序）排列。
    """
    keyword = (name or "").strip().lower()
    if not keyword:
        return "not_found", []
    products = load_products()
    exact = [p for p in products if p.get("name", "").strip().lower() == keyword]
    if exact:
        return "exact", exact
    fuzzy = [
        p
        for p in products
        if keyword in p.get("name", "").lower() or p.get("name", "").lower() in keyword
    ]
    if fuzzy:
        return "fuzzy", fuzzy
    return "not_found", []


def latest_price(product_id: int) -> float:
    """返回商品最近一次价格；无价格数据时返回 0.0。"""
    history = load_price_history(product_id)
    points = history["points"] if history else []
    if not points:
        return 0.0
    return float(points[-1]["price"])


def search_products(name: str, limit: int = 20) -> list[dict]:
    """按名称搜索已收录商品，返回精简信息（供发评价选择商品等）。"""
    _, candidates = match_product(name)
    result: list[dict] = []
    for c in candidates[:limit]:
        result.append(
            {
                "id": c.get("id"),
                "name": c.get("name", ""),
                "barcode": str(c.get("barcode", "")),
                "category": c.get("category", ""),
                "price": latest_price(c.get("id")),
            }
        )
    return result
