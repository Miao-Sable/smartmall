"""应用配置（通过环境变量 / .env 覆盖默认值）"""
import os
import sys
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _is_frozen() -> bool:
    """PyInstaller 打包后 sys.frozen 为 True，且数据解压到 sys._MEIPASS。"""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


if _is_frozen():
    # 打包环境：mock 数据随包解压到临时目录，DB 写到用户本地可写目录
    _DATA_DIR = Path(sys._MEIPASS) / "mock"
    _DB_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "SmartMall"
else:
    # 开发环境：项目根目录（backend/ 的上一级）
    PROJECT_ROOT = Path(__file__).resolve().parents[3]
    _DATA_DIR = PROJECT_ROOT / "mock"
    _DB_DIR = PROJECT_ROOT

# 确保 DB 目录存在（打包环境下 LOCALAPPDATA 首次运行可能还没有）
_DB_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "智慧购物 API"
    debug: bool = True

    # 生产环境务必通过环境变量覆盖！
    secret_key: str = "dev-secret-key-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7

    # SQLite 开发 / PostgreSQL 部署（如 postgresql://user:pass@host/db）
    database_url: str = f"sqlite:///{_DB_DIR / 'smartmall.db'}"

    # mock 数据目录
    mock_dir: Path = _DATA_DIR

    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


settings = Settings()
