#!/bin/sh
set -e

echo "Waiting for database to accept connections..."
until python - <<'PY'
import os, sys

import psycopg

url = os.environ["DATABASE_URL"]
# Normalize the SQLAlchemy-style URL for raw psycopg.
dsn = url.replace("postgresql+psycopg://", "postgresql://")
try:
    with psycopg.connect(dsn, connect_timeout=3) as conn:
        conn.execute("SELECT 1")
except Exception as exc:  # noqa: BLE001
    print(f"db not ready: {exc}", flush=True)
    sys.exit(1)
PY
do
  sleep 2
done
echo "Database is ready."

echo "Applying database migrations..."
alembic upgrade head
echo "Migrations applied."

# PORT can be overridden by the deployment platform (defaults to 8000).
PORT="${PORT:-8000}"
echo "Starting API server on port ${PORT}..."
exec uvicorn backend.app.main:app \
    --host 0.0.0.0 \
    --port "${PORT}" \
    --timeout-keep-alive 30 \
    --timeout-graceful-shutdown 30
