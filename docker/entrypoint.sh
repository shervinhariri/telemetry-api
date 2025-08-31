#!/usr/bin/env bash
set -euo pipefail
PORT="${PORT:-8080}"
HOST="${HOST:-0.0.0.0}"

echo "[entrypoint] Starting API on ${HOST}:${PORT}"
# Adjust the command if we use poetry or gunicorn; keeping uvicorn here:
exec uvicorn app.main:app --host "${HOST}" --port "${PORT}"
