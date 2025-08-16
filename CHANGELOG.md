# Changelog

All notable changes to the Telemetry API project will be documented in this file.

## [0.7.9] - 2025-08-16

### Added
- **OpenAPI 3.1 Specification**: Complete API documentation with Swagger UI at `/docs`
- **Scoped API Keys**: RBAC system with granular permissions (ingest, manage_indicators, export, read_requests, read_metrics)
- **Security & Privacy**: Configurable field redaction and security headers (CORS, HSTS, X-Frame-Options)
- **Dead Letter Queue (DLQ)**: Failed export handling with exponential backoff and retry logic
- **Idempotency Support**: `Idempotency-Key` header support for duplicate ingest prevention
- **Enhanced Observability**: Detailed metrics with latency percentiles, DLQ statistics, and backpressure signals
- **Real-time Dashboard**: Server-Sent Events (SSE) for live tailing with proper MIME type handling
- **Comprehensive Request Audit**: Complete request logging with detailed operation tracking
- **UI Authentication Wrapper**: Global fetch wrapper with automatic Authorization header injection
- **Status Chip**: Real-time API health monitoring with 30-second polling
- **Version Display**: Dynamic version loading from `/v1/system` endpoint
- **Empty State Handling**: User-friendly empty states for Requests tab with guidance
- **API Key Persistence**: localStorage-based API key saving with toast notifications
- **Compatibility Routes**: Backward compatibility for old UI paths (`/api/requests`)
- **Window Selection**: Time window dropdown (15m, 1h, 24h) with 24h default
- **Toast Notifications**: User feedback for API key saves and errors

### Changed
- **Header Redesign**: Removed Health button, added StatusChip and Version display
- **Requests Tab**: Default to 24h window, improved empty state UX
- **API Key Management**: Persistent storage with automatic loading
- **Error Handling**: Better 401 error messages and user guidance
- **SSE Implementation**: Fixed MIME type from `text/plain` to `text/event-stream`
- **JSON Serialization**: Proper datetime handling for SSE events

### Technical
- **API Wrapper**: Centralized authentication and error handling
- **CORS Support**: Proper CORS headers for cross-origin requests
- **Security Headers**: X-Content-Type-Options, X-Frame-Options, X-XSS-Protection
- **Redaction**: Configurable field and header redaction for privacy
- **Chart.js Integration**: Robust throughput chart initialization with error handling
- **Data Normalization**: Comprehensive data transformation utilities for UI consistency

## [0.7.8] - 2025-01-XX

### Added
- **Enhanced Dashboard**: Single throughput chart (events/sec) over 15 minutes with 4 compact stat cards
- **Requests Page UX**: State boxes (Total, Succeeded, Failed, Avg Latency) with right-side drawer for request details
- **New Ingest Endpoints**: 
  - `POST /v1/ingest/zeek` - Dedicated Zeek conn.log ingestion
  - `POST /v1/ingest/netflow` - Dedicated NetFlow/IPFIX ingestion with canonical schema mapping
  - `POST /v1/ingest/bulk` - Type-specified bulk ingestion
- **Threat Intelligence Management**:
  - `PUT /v1/indicators` - Add/update threat indicators
  - `DELETE /v1/indicators/:id` - Remove indicators by ID
- **Export Connectors**:
  - `POST /v1/export/splunk-hec` - Buffered bulk export to Splunk HEC
  - `POST /v1/export/elastic` - Bulk export to Elasticsearch
- **Data Download**: `GET /v1/download/json?limit=10000` - Stream enriched events as JSON lines
- **Enhanced Requests API**: `GET /api/requests?limit=500&window=15m` - Aggregated request data with time windows
- **Sample Data**: `samples/zeek_conn_small.json` and `samples/netflow_small.json`
- **Test Scripts**: `tests/test_endpoints.py` and `scripts/load_test.py` for comprehensive testing
- **Postman Collection**: Complete API testing collection with sample payloads

### Changed
- **Dashboard Layout**: Replaced 6-card grid with single chart + 4 state cards for better performance visibility
- **Requests Table**: Simplified columns (Time, Method, Path, Status, Latency, Source IP, Records, Risk Avg, Actions)
- **UI Version**: Updated to v0.7.8 across frontend and backend
- **README**: Complete rewrite with concise v0.7.8 documentation and quick start guide

### Fixed
- **Request Details**: Right-side drawer now shows comprehensive request information including headers, payload summary, enrichment results, and export actions
- **Validation Errors**: Multi-status (207) responses with per-record validation errors for malformed payloads
- **Performance**: Optimized dashboard rendering and request loading

### Technical
- **Backend Version**: Updated to 0.7.8 in `app/api/version.py`
- **Threat Intelligence**: Added dynamic indicator management with in-memory storage
- **Audit System**: Enhanced request tracking with detailed operation logging
- **Error Handling**: Improved validation and error reporting across all endpoints

## [0.7.5] - 2024-XX-XX

### Added
- Professional dashboard with 6 KPI cards and live sparklines
- Request audit system with operations tracking
- System information endpoint
- Enhanced UI with status codes and performance indicators

### Changed
- Improved dashboard design and performance
- Enhanced request monitoring capabilities

## [0.7.2] - 2024-XX-XX

### Added
- Basic ingest pipeline
- GeoIP and ASN enrichment
- Threat intelligence matching
- Risk scoring system

### Changed
- Initial MVP release with core functionality

---

For detailed documentation of each stage, see the `/docs/` directory and PDF files.
