#!/bin/sh
set -e

echo "Waiting for database..."
python <<'PY'
import sys
import time

from sqlalchemy import create_engine, text

from app.config import settings

for attempt in range(30):
    try:
        engine = create_engine(settings.database_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        break
    except Exception as exc:  # noqa: BLE001
        print(f"DB not ready ({exc}); retrying...", file=sys.stderr)
        time.sleep(2)
else:
    print("Database never became ready.", file=sys.stderr)
    sys.exit(1)
PY

echo "Initializing database (pgvector extension + tables)..."
python -m app.db.init_db

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting application..."
exec "$@"
