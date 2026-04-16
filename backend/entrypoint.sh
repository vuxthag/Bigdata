#!/bin/sh
# entrypoint.sh
# =============
# Container startup: run Alembic migrations then start uvicorn.
# Using `alembic upgrade head` here means every container restart
# is idempotent — migrations that have already been applied are skipped.

set -e

echo "[entrypoint] Running Alembic migrations..."
alembic upgrade head
echo "[entrypoint] Migrations complete. Starting API server..."

exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --log-level info
