#!/usr/bin/env bash
# scripts/start.sh
PORT="${PORT:-80}"
HOST="${HOST:-0.0.0.0}"
exec uvicorn app.main:app --host "$HOST" --port "$PORT" --log-level info
