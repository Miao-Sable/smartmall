"""商品查询（MVP：mock 数据；预留第三方 API 接入位置）"""
from fastapi import APIRouter, HTTPException

from app.schemas.product import PriceHistoryOut, ProductOut
from app.schemas.shopping_list import ProductBrief
from app.services.mock_data import find_product_by_barcode, load_price_history, search_products

router = APIRouter()


@router.get("/search", response_model=list[ProductBrief])
def search_products_by_name(name: str) -> list[ProductBrief]:
    """按名称搜索商品（供发评价选择商品），返回精简信息列表。"""
    return [ProductBrief(**p) for p in search_products(name)]


@router.get("/{barcode}", response_model=ProductOut)
def get_product_by_barcode(barcode: str) -> ProductOut:
    product = find_product_by_barcode(barcode)
    if product is None:
        raise HTTPException(status_code=404, detail="暂无该商品数据，请尝试扫描其他条码")
    return ProductOut(**product)


@router.get("/{product_id}/price-history", response_model=PriceHistoryOut)
def get_price_history(product_id: int) -> PriceHistoryOut:
    """MVP 阶段返回模拟价格数据"""
    item = load_price_history(product_id)
    if item is None:
        return PriceHistoryOut(product_id=product_id, barcode="", points=[])
    return PriceHistoryOut(**item)
