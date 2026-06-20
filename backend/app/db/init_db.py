"""Owner: M1. Dev-convenience initializer: creates the pgvector extension and all
tables. Quick alternative to alembic for the hackathon. Run:

    python -m app.db.init_db
"""
from sqlalchemy import text

from app.db.models import Base
from app.db.session import engine


def init_db() -> None:
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)
    print("Database initialized: pgvector extension + all tables.")


if __name__ == "__main__":
    init_db()
