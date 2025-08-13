# Changelog

## v0.5.0 — Stage 5 (2025-08-13)
- Robust ingest pipeline: queue-based processing, gzip support, proper error handling
- Dual format support: raw JSON arrays `[...]` and wrapped `{"records": [...]}`
- Background worker: async processing with error isolation and dead letter queue
- Backpressure handling: 429 responses when queue is full (10k limit)
- Enhanced validation: timestamp required, size limits, JSON structure validation
- Public health endpoint: `/v1/health` no longer requires authentication
- Queue metrics: real-time queue depth and processing status via `/v1/metrics`

## v0.4.0 — Stage 4 (2025-08-13)
- Single container: API + Dashboard UI served from `/`
- Attractive KPIs + Events/min chart; tabs for Ingest, Outputs, Lookup, System
- README cleaned: title neutral, stages in body
- CI: build & push to Docker Hub on main and tags
