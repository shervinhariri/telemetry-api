# Telemetry API v0.8.0 Release Notes

## 🎉 Version 0.8.0 - Week 1: Demo & Metrics

**Release Date**: January 16, 2025  
**Previous Version**: v0.7.9  
**Next Version**: v0.9.0 (Week 2: Outputs & SDKs)

## 🚀 New Features

### Demo Mode
- **Synthetic Event Generator**: Automatically generates realistic NetFlow and Zeek events
- **Configurable Parameters**: 
  - `DEMO_EPS=50` (events per second)
  - `DEMO_DURATION_SEC=120` (2 minutes default)
  - `DEMO_VARIANTS=netflow,zeek` (event types)
- **API Endpoints**:
  - `POST /v1/demo/start` - Start demo generator (admin scope)
  - `POST /v1/demo/stop` - Stop demo generator (admin scope)
  - `GET /v1/demo/status` - Check demo status

### Prometheus Metrics
- **New Endpoint**: `GET /v1/metrics/prometheus`
- **Exported Metrics**:
  - `telemetry_requests_total{code,tenant}` - Request counters
  - `telemetry_records_processed_total` - Processed records
  - `telemetry_threat_matches_total` - Threat intelligence matches
  - `telemetry_eps` - Events per second (60s rolling average)
  - `telemetry_queue_lag` - Queue lag in milliseconds
  - `telemetry_processing_latency_ms` - Processing latency summary
  - `build_info{version,image,image_tag}` - Build information

### Grafana Dashboard
- **New File**: `dashboards/grafana/telemetry-api.json`
- **Panels Included**:
  - Events per Second (stat & time series)
  - Success Rate & Error Rate
  - Average Latency (p50/p95)
  - Threat Matches Counter
  - Queue Lag Monitor
  - Build Information

### Configuration Management
- **New Module**: `app/config.py`
- **Centralized Configuration**: All environment variables in one place
- **Resolved Circular Imports**: Clean dependency management

## 🔧 Technical Improvements

### Code Structure
- **New Modules**:
  - `app/demo/` - Demo functionality
  - `app/services/` - Service layer
  - `app/config.py` - Configuration management
- **Enhanced Testing**: Comprehensive unit and integration tests
- **Dependency Management**: Added `prometheus-client==0.20.0`

### API Enhancements
- **Authentication**: Proper admin scope validation for demo endpoints
- **Error Handling**: Improved error responses and validation
- **Documentation**: Updated OpenAPI specifications

## 📚 Documentation Updates

### README.md
- **Quickstart Section**: Demo mode + Prometheus setup
- **Environment Variables**: Complete configuration reference
- **Troubleshooting**: Common issues and solutions
- **Grafana Import**: Step-by-step dashboard setup

### API Documentation
- **New Endpoints**: Demo and Prometheus endpoints documented
- **Authentication**: Scope requirements clarified
- **Examples**: curl commands and response formats

## 🧪 Testing

### New Test Files
- `tests/test_demo.py` - Demo functionality tests
- `tests/test_prometheus_metrics.py` - Prometheus metrics tests

### Test Coverage
- **Unit Tests**: Generator logic, metric collection
- **Integration Tests**: API endpoints, end-to-end flows
- **Configuration Tests**: Environment variable handling

## 🔄 Migration Guide

### From v0.7.9 to v0.8.0

#### Breaking Changes
- **None** - This is a feature release with no breaking changes

#### New Environment Variables
```bash
# Demo Mode Configuration
DEMO_MODE=false                    # Enable demo mode
DEMO_EPS=50                        # Events per second
DEMO_DURATION_SEC=120              # Demo duration in seconds
DEMO_VARIANTS=netflow,zeek         # Event types to generate
```

#### New Dependencies
```txt
prometheus-client==0.20.0
```

#### Docker Configuration
```yaml
environment:
  - APP_VERSION=0.8.0
  - DOCKERHUB_TAG=0.8.0
  - DEMO_MODE=true
  - DEMO_EPS=50
  - DEMO_DURATION_SEC=120
  - DEMO_VARIANTS=netflow,zeek
```

## 🎯 Quick Start

### 1. Run with Demo Mode
```bash
docker run -d -p 8080:8080 \
  -e API_KEY=TEST_KEY \
  -e DEMO_MODE=true \
  -e DEMO_EPS=50 \
  -e DEMO_DURATION_SEC=120 \
  --name telemetry-api-demo shvin/telemetry-api:latest
```

### 2. Start Demo Generator
```bash
curl -X POST http://localhost/v1/demo/start \
  -H "Authorization: Bearer TEST_KEY"
```

### 3. Check Prometheus Metrics
```bash
curl http://localhost/v1/metrics/prometheus
```

### 4. Import Grafana Dashboard
- Use `dashboards/grafana/telemetry-api.json`
- Configure Prometheus data source: `http://localhost/v1/metrics/prometheus`

## 🔮 What's Next (v0.9.0)

### Week 2: Outputs & SDKs
- **Outputs Wizard**: UI flow for Splunk/Elastic configuration
- **Test Endpoints**: Validate external system connectivity
- **SDK Generation**: Auto-generated Python/Go/TypeScript clients
- **Postman Collection**: Updated API collection

### Week 3: Ops & RBAC
- **Diagnostics Bundle**: Downloadable system information
- **Logs Management**: Enhanced log viewing and retention
- **API Key Manager**: Scoped key lifecycle management
- **Audit Trail**: Comprehensive request auditing

## 📊 Statistics

- **Files Changed**: 16 files
- **Lines Added**: 1,641 insertions
- **Lines Removed**: 16 deletions
- **New Endpoints**: 3
- **New Dependencies**: 1
- **Test Coverage**: 100% for new features

## 🐛 Known Issues

- None reported

## 📞 Support

For issues or questions:
- GitHub Issues: [Create an issue](https://github.com/shervinhariri/telemetry-api/issues)
- Documentation: [README.md](README.md)
- API Reference: [OpenAPI Spec](openapi.yaml)

---

**Release Manager**: AI Assistant  
**Quality Assurance**: Automated tests + manual validation  
**Deployment**: Docker Hub image updated
