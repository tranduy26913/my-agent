"""SQLAlchemy 2.0 setup (tương đương DbContext của EF Core)."""

from collections.abc import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# connect_timeout: DB tắt/treo thì báo lỗi sau 5 giây thay vì treo vô hạn (/readyz cần trả 503 nhanh).
engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args={"connect_timeout": 5})
SessionLocal = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    """FastAPI dependency: mỗi request một session (scoped lifetime như AddDbContext)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Tạo extension pgvector + bảng. Production nên dùng Alembic migration."""
    from app import models  # noqa: F401  (đăng ký model vào metadata)

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent"))
        # unaccent() chỉ là STABLE nên Postgres không cho dùng trong generated column / index.
        # Bọc lại thành hàm IMMUTABLE với dictionary cố định -> an toàn vì dictionary không đổi.
        conn.execute(text(
            "CREATE OR REPLACE FUNCTION f_unaccent(text) RETURNS text "
            "LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT "
            "AS $$ SELECT public.unaccent('public.unaccent'::regdictionary, $1) $$"
        ))
    Base.metadata.create_all(engine)
