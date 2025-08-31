#!/usr/bin/env bash
set -euo pipefail
PORT="${PORT:-80}"
echo "[entrypoint] Starting API on 0.0.0.0:${PORT}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
