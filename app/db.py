from collections.abc import Generator
from pathlib import Path
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

ROOT = Path(__file__).resolve().parent.parent


def resolve_database_url() -> str:
    """SQLite locally; PostgreSQL in production via DATABASE_URL.

    Cloudflare Python Workers have no writable disk, so they keep an in-memory
    SQLite fallback. Durable production data should use Postgres (or Hyperdrive),
    not a SQLite file and not D1 (D1 would replace SQLAlchemy).
    """
    if sys.platform == "emscripten" and not settings.database_url.startswith("postgresql"):
        return "sqlite:///:memory:"

    url = settings.database_url
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url.removeprefix("postgres://")
    elif url.startswith("postgresql://") and "+psycopg" not in url:
        url = "postgresql+psycopg://" + url.removeprefix("postgresql://")
    if url.startswith("sqlite:///./"):
        url = f"sqlite:///{ROOT / url.removeprefix('sqlite:///./')}"
    return url


def _engine_kwargs(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_pre_ping": True, "pool_size": 5, "max_overflow": 10}


database_url = resolve_database_url()
engine: Engine = create_engine(database_url, **_engine_kwargs(database_url))
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def is_sqlite() -> bool:
    return engine.dialect.name == "sqlite"


def ping_db() -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


def init_schema() -> None:
    """Create missing tables. SQLite local: also create missing indexes.

    PostgreSQL production should run `alembic upgrade head` so schema changes
    are versioned. create_all is still safe (it does not drop columns).
    """
    Base.metadata.create_all(bind=engine)
    for table in Base.metadata.tables.values():
        for index in table.indexes:
            index.create(bind=engine, checkfirst=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
