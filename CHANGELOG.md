# Changelog

All notable changes to the Telemetry API project will be documented in this file.

## [0.8.10] - 2025-08-25

### Fixed
- **Feature Gates Stability**: Prevent crashes when `/system` endpoint is slow or fails by normalizing features and guarding `applyFeatureGates()` against undefined values.
- **API Base Join**: Fix URL construction to prevent `/v1/v1/*` requests by implementing safe URL joining with proper base normalization.
- **Hard-Refresh UX**: Logo click now preserves current tab/hash and performs clean full reload without adding `?r=` query parameters.

### Changed
- **UI Cache Bust**: Updated `app.js` cache-bust parameter to `vefix53` for development.
- **Feature Normalization**: Added `normalizeFeatures()` and `setFeatures()` methods to ensure consistent feature state.

## [0.8.9] - 2025-08-25

### Changed
- Unified versioning to read from `VERSION` across API, Docker labels, and CI.
- Updated docs and workflows to standardize on 0.8.9 and remove stale fallbacks.
- Split production vs dev/CI dependencies to slim runtime image.

### Fixed
- Release smoke tests now compare `/v1/version` to `VERSION` instead of hard-coded values.
- README references `scripts/verify_allinone.sh` (removed `*_final.sh` confusion).

## [0.8.6] - 2025-08-21

[Full Changelog](https://github.com/shervinhariri/telemetry-api/compare/v0.8.4...v0.8.6)

**Highlights:**
- **Phase 1**: Single source of truth for version management
- **Phase 2**: Consolidated verification scripts with environment variable support
- **Phase 3**: CI pipeline improvements with proper failure handling
- **Phase 4**: Security hardening with secret scanning and vulnerability scanning
- **Phase 5**: Centralized logging with structured JSON and live streaming
- **Phase 6**: UI polish with modern components and improved reliability
- **Phase 7**: SSE browser compatibility and authentication fixes

### Added
- **Single Source of Truth for Version**: VERSION file at repo root for centralized version management
- **Dynamic Version Reading**: Backend version endpoints now read from VERSION file with fallback to environment variables
- **UI Version Integration**: Both legacy and React UIs now fetch version from API instead of hardcoded values
- **Consolidated Verification Scripts**: Merged and parameterized verification scripts with environment variable support
- **CI Pipeline Improvements**: Removed `|| true` workarounds, added Python dependency caching, proper exit codes
- **Security Hardening**: Secret scanning with Gitleaks, container vulnerability scanning with Trivy, dependency pinning
- **Centralized Logging**: JSON structured logging with request tracing, in-memory ring buffer, and SSE streaming
- **UI Polish & Reliability**: Modern donut gauges, consistent button components, improved layouts, and live logs streaming

### Changed
- **Version Management**: Moved from hardcoded version strings to VERSION file-based system
- **Docker CI**: Updated workflow to use VERSION file for tag generation, added GHCR mirror
- **Backend Version Logic**: Unified version reading across all version endpoints
- **Verification Scripts**: Single canonical `scripts/verify_allinone.sh` with environment variable configuration
- **CI Pipeline**: Fails on real test failures, faster runs with dependency caching
- **Security Posture**: Base image pinning, dependency hashes, secret scanning, vulnerability scanning
- **Logging System**: Structured JSON logging with trace correlation and live streaming capabilities
- **UI Components**: Consistent design tokens, improved accessibility, and modern styling

### Fixed
- **SSE Browser Compatibility**: SSE logs stream now uses correct media type (`text/event-stream`) for `/v1/logs/stream`
- **EventSource Authentication**: UI now passes API key via `?key=` query parameter and backend accepts query key for SSE
- **Browser Limitations**: Workaround for EventSource not supporting custom headers in browsers

### Technical
- **VERSION File**: New file at repo root containing "0.8.6"
- **API Endpoints**: Updated /v1/version and /v1/api/version to read from VERSION file
- **Fallback Chain**: VERSION file → APP_VERSION env var → config.py API_VERSION
- **Docker Tags**: CI now generates both "latest" and "v0.8.6" tags
- **Security Tools**: Gitleaks configuration, Trivy scanning, SARIF uploads
- **Logging Infrastructure**: Custom JsonFormatter, MemoryLogHandler, ASGI middleware for tracing
- **UI Framework**: Design tokens, component library, and improved state management
- **SSE Implementation**: Proper EventSource handling with query parameter authentication

## [Unreleased] - 2025-XX-XX

### Added
- Development version for next release cycle

## [0.8.4] - 2025-08-19

### Added
- **All-in-One Container**: Single container with goflow2→FIFO→mapper→API pipeline
- **Sources Backend**: Complete sources management with database, API endpoints, and metrics tracking
- **Sources UI Tab**: New Sources page with table, filters, pagination, and real-time updates
- **Real-time Metrics**: In-memory EPS, error rate, and risk scoring for sources
- **Status Management**: Automatic healthy/degraded/stale status based on activity and errors
- **10-second Polling**: Lightweight updates for Status, EPS(1m), Last Seen without full table reload

### Changed
- **Port Configuration**: API/GUI now serves on port 80 (was 8080)
- **NetFlow Collection**: UDP port 2055 exposed for NetFlow/IPFIX ingestion
- **Multi-architecture Support**: goflow2 compiled from source for AMD64/ARM64 compatibility

### Technical
- **Database**: Added sources table with proper indexes and migration
- **API Endpoints**: POST/GET /v1/sources, GET /v1/sources/{id}/metrics
- **Ingest Hook**: Automatic source last_seen updates and metrics recording
- **Authentication**: Proper scope-based access (admin for create, read_metrics for view)
- **UI Components**: Sources table, filters, pagination, and right-drawer details

## [0.8.3] - 2025-08-19

### Added
- Version bump to 0.8.3; UI “Set API Key” modal with Test & Save; URL key bootstrap & scrub
- Multi-tenancy support retained with DB-backed auth, optional Redis, idempotency, rate limiting

### Changed
- Authentication middleware preserves HTTPException; public allowlist refined
- UI dashboard improvements; version moved to main page; system tab removed

### Technical
- SQLAlchemy/Alembic kept; AUTO_MIGRATE optional; persistent SQLite volume
- Idempotent seeder and optional ADMIN_BOOTSTRAP_KEY / SEED_DEFAULT_TENANT

## [0.8.1] - 2025-01-XX

### Added
- Inline API key editing within the oval chip (no popover)
- Balanced button styling with gray for most buttons, green for important actions
- Clean header design with Online status moved to right side
- Improved error handling and user feedback
- API key synchronization across all pages

### Changed
- Updated version from 0.8.0 to 0.8.1
- Removed old data files and unnecessary logs
- Cleaned up version history and documentation

### Fixed
- Backend null handling in requests endpoint
- API key management and persistence
- UI responsiveness and user experience

## [0.8.0] - 2025-08-17

### Added
- Admin timelines with max 6 canonical events and per-row donut gauges
- In-memory audit ring buffer with TTL pruning and configurable size
- Admin endpoint with filters (limit, status, path, exclude_monitoring) and ETag support
- Prometheus metrics: `telemetry_requests_total` and `telemetry_request_fitness`
- Security and privacy: scope-based access, header/field redaction
- Comprehensive tests: fitness unit tests and admin requests API tests

### Changed
- Standardized internal port to 80; removed hardcoded 8080 from code
- Reduced log noise; structured logging with sampling and excludes

### Fixed
- Trace propagation across pipeline; X-Trace-Id on responses

---

## [0.8.0] - 2025-08-17

### Added
- **Demo Mode**: Configurable demo data generation with customizable EPS and duration
- **Enhanced Metrics**: Prometheus metrics with demo-specific counters and gauges
- **Week 1 Features**: Demo & Metrics implementation for v0.8.0 milestone
- **Comprehensive Release Notes**: Detailed documentation for v0.8.0 features

### Changed
- **Version Update**: Bumped from v0.7.9 to v0.8.0 across all components
- **Docker Configuration**: Updated APP_VERSION and DOCKERHUB_TAG to 0.8.0

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

## 0.8.5 — Golden (2025-08-20)
- Sources "Access & Limits" drawer (View/Edit/Delete) ✅
- "Add Source" modal (right-side drawer version) ✅
- HTTP & UDP admission control with allowlists and EPS caps ✅
- Feature flags with runtime toggles + audit trail ✅
- Prometheus metrics for blocked/rate-limit/FIFO/UDP ✅
- nftables allowlist API with dry-run & status ✅
- Resilience caps (FIFO bounds, container resources) ✅
- Docs & Makefile targets for ops flows ✅
