"""数据库模型汇总（导入以注册到 SQLModel.metadata）"""
from app.models.community import Review
from app.models.product import (
    KeywordLibrary,
    PriceHistory,
    Product,
    ProductBarcode,
    ProductIngredient,
    ProductNutrition,
)
from app.models.scan import AnalysisResult, ScanHistory
from app.models.user import (
    Allergen,
    DietPreference,
    Profile,
    ProfileAllergen,
    ProfileDiet,
    User,
    UserAllergen,
    UserDiet,
    UserProfile,
)

__all__ = [
    "Allergen",
    "AnalysisResult",
    "DietPreference",
    "KeywordLibrary",
    "PriceHistory",
    "Product",
    "ProductBarcode",
    "ProductIngredient",
    "ProductNutrition",
    "Profile",
    "ProfileAllergen",
    "ProfileDiet",
    "Review",
    "ScanHistory",
    "User",
    "UserAllergen",
    "UserDiet",
    "UserProfile",
]
