"""数据库引擎与会话（SQLite 开发 / PostgreSQL 部署）"""
from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, echo=settings.debug, connect_args=connect_args)


def get_session():
    """FastAPI 依赖：每个请求一个会话"""
    with Session(engine) as session:
        yield session


def _migrate_schema() -> None:
    """轻量迁移：为已存在的 SQLite 表补充新增列（幂等）。

    create_all 不会为已有表追加列，这里用 ALTER TABLE 补上历史版本缺失的列，
    避免开发阶段删库重建导致数据丢失。
    """
    if not settings.database_url.startswith("sqlite"):
        return
    inspector = inspect(engine)
    if "analysis_result" not in inspector.get_table_names():
        return

    existing = {c["name"] for c in inspector.get_columns("analysis_result")}
    additions = {
        "traffic_light": "VARCHAR(16) NOT NULL DEFAULT 'green'",
        "reasons": "JSON",
    }
    with engine.begin() as conn:
        for col, ddl in additions.items():
            if col not in existing:
                conn.execute(text(f"ALTER TABLE analysis_result ADD COLUMN {col} {ddl}"))


def init_db() -> None:
    """建表并初始化字典数据（幂等，可重复调用）"""
    # 导入模型模块，确保全部注册到 SQLModel.metadata
    from app import models  # noqa: F401
    from app.services.seed import seed_dicts

    SQLModel.metadata.create_all(engine)
    _migrate_schema()
    with Session(engine) as session:
        seed_dicts(session)
