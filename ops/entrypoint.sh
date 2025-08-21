#!/usr/bin/env bash
set -euo pipefail

API_HOST="${API_HOST:-0.0.0.0}"
API_PORT="${API_PORT:-80}"                          # GUI/API on 80
COLLECTOR_LISTEN="${COLLECTOR_LISTEN:-netflow://:2055}" # NetFlow on 2055/udp
GOFLOW_ARGS="${GOFLOW_ARGS:--format=json -listen ${COLLECTOR_LISTEN}}"

MAPPER_API="${MAPPER_API:-http://127.0.0.1:${API_PORT}}"
MAPPER_KEY="${MAPPER_KEY:-TEST_KEY}"
MAPPER_COLLECTOR_ID="${MAPPER_COLLECTOR_ID:-gw-local}"

FIFO="/run/collector.ndjson"
mkdir -p /run
[ -p "$FIFO" ] || mkfifo "$FIFO"

echo "[BOOT] starting goflow2 -> $FIFO"
(goflow2 ${GOFLOW_ARGS} > "$FIFO") &
PID_GOFLOW=$!

echo "[BOOT] starting mapper (reads FIFO, posts to /v1/ingest)"
API="$MAPPER_API" KEY="$MAPPER_KEY" COLLECTOR_ID="$MAPPER_COLLECTOR_ID" \
  python /app/mapper/nf2ingest.py < "$FIFO" &
PID_MAPPER=$!

echo "[BOOT] running database bootstrap..."
python scripts/bootstrap.py

echo "[BOOT] running migrate_sqlite.py"
python /app/scripts/migrate_sqlite.py || {
  echo "[BOOT] migrate_sqlite failed"; exit 1;
}

echo "[BOOT] starting API on ${API_HOST}:${API_PORT}"
# Replace with your real API server command if different:
python -m uvicorn app.main:app --host "$API_HOST" --port "$API_PORT" &
PID_API=$!

trap 'echo "[BOOT] stopping..."; kill $PID_GOFLOW $PID_MAPPER $PID_API 2>/dev/null || true; wait || true' TERM INT
wait -n $PID_GOFLOW $PID_MAPPER $PID_API
STATUS=$?
echo "[BOOT] one process exited with code $STATUS, shutting down..."
kill $PID_GOFLOW $PID_MAPPER $PID_API 2>/dev/null || true
wait || true
exit $STATUS
