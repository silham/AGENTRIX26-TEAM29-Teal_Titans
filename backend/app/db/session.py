"""Owner: M1. SQLAlchemy engine + session + FastAPI dependency.

SQLite is the default so the demo works without PostgreSQL. Tables are created
automatically on startup so there is no migration step required for development.
"""
import logging
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)

# SQLite needs WAL mode and foreign-key enforcement enabled per connection.
_is_sqlite = settings.database_url.startswith("sqlite")

engine = create_engine(
    settings.database_url,
    pool_pre_ping=not _is_sqlite,  # pre-ping is meaningless for SQLite files
    future=True,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)

if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# Auto-create all tables at import time (idempotent; skips existing tables).
# NOTE: create_all() creates MISSING TABLES but never ALTERs existing ones, so
# column additions must go through Alembic (app/db/migrations/versions/).
try:
    from app.db.models import Base
    Base.metadata.create_all(bind=engine)
except Exception:
    # A failure here means the engine is unusable (bad URL, missing driver,
    # unreachable host). Outside development that must not look like a healthy
    # boot — the old bare `print` let the app serve 500s from every route.
    logger.error("Could not create tables — the database engine is unusable.", exc_info=True)
    if settings.environment != "development":
        raise


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
