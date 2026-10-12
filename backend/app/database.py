"""数据库引擎与会话（SQLite 开发 / PostgreSQL 部署）"""
from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine, select

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
    existing_tables = set(inspector.get_table_names())

    # 表名 -> {列名: DDL}
    additions: dict[str, dict[str, str]] = {
        "analysis_result": {
            "traffic_light": "VARCHAR(16) NOT NULL DEFAULT 'green'",
            "reasons": "JSON",
        },
        "scan_history": {
            "profile_id": "INTEGER",
        },
    }
    with engine.begin() as conn:
        for table, cols in additions.items():
            if table not in existing_tables:
                continue
            existing = {c["name"] for c in inspector.get_columns(table)}
            for col, ddl in cols.items():
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}"))


def _migrate_profiles(session: Session) -> None:
    """幂等数据迁移：把账号级过敏源/偏好迁到「家庭档案」模型。

    - 为没有默认档案的老账号创建默认档案「我」；
    - 把 UserAllergen / UserDiet 复制为 ProfileAllergen / ProfileDiet；
    - 回填该账号扫描历史的 profile_id（原为 NULL）。
    """
    from app.models.scan import ScanHistory
    from app.models.user import Profile, ProfileAllergen, ProfileDiet, User, UserAllergen, UserDiet

    users = session.exec(select(User)).all()
    for user in users:
        default = session.exec(
            select(Profile).where(Profile.user_id == user.id, Profile.is_default.is_(True))
        ).first()
        if default is None:
            default = Profile(user_id=user.id, name="我", is_default=True)
            session.add(default)
            session.flush()  # 取得 default.id

            for ua in session.exec(select(UserAllergen).where(UserAllergen.user_id == user.id)):
                session.add(ProfileAllergen(profile_id=default.id, allergen_id=ua.allergen_id))
            for ud in session.exec(select(UserDiet).where(UserDiet.user_id == user.id)):
                session.add(ProfileDiet(profile_id=default.id, diet_id=ud.diet_id))

        # 回填该账号名下 profile_id 为 NULL 的扫描历史
        for scan in session.exec(
            select(ScanHistory).where(ScanHistory.user_id == user.id, ScanHistory.profile_id.is_(None))
        ):
            scan.profile_id = default.id
    session.commit()


def init_db() -> None:
    """建表并初始化字典数据（幂等，可重复调用）"""
    # 导入模型模块，确保全部注册到 SQLModel.metadata
    from app import models  # noqa: F401
    from app.services.seed import seed_dicts

    SQLModel.metadata.create_all(engine)
    _migrate_schema()
    with Session(engine) as session:
        seed_dicts(session)
        _migrate_profiles(session)
