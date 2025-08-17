#!/usr/bin/env bash
set -euo pipefail

echo "[1/2] Health:"
curl -s http://localhost/v1/health || true
echo

echo "[2/2] Ingest:"
curl -s -X POST http://localhost/v1/ingest \
  -H "Authorization: Bearer ${API_KEY:-TEST_KEY}" \
  -H "Content-Type: application/json" \
  --data @samples/zeek_conn.json || true
echo

echo "Done."
