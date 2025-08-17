# Telemetry API Scripts

This directory contains essential scripts for managing, testing, and deploying the Telemetry API.

## 🚀 Deployment & Setup

### `bootstrap.sh`
Initial setup script for the Telemetry API environment.
```bash
./scripts/bootstrap.sh
```

### `deploy.sh`
Deployment script for production environments.
```bash
./scripts/deploy.sh
```

### `update.sh`
Update script for applying patches and updates.
```bash
./scripts/update.sh
```

## 🧪 Testing

### `test_api.sh`
Comprehensive API test suite that validates all endpoints.
```bash
# Test with default settings
./scripts/test_api.sh

# Test with custom settings
BASE_URL=http://localhost API_KEY=YOUR_KEY ./scripts/test_api.sh
```

**Tests included:**
- Health endpoint
- Version endpoint
- System information
- Metrics endpoint
- Ingest functionality
- Logs endpoint
- Lookup functionality
- Requests endpoint

### `load_test.py`
Performance testing script for load testing the API.
```bash
python scripts/load_test.py
```

### `create_testkit.py`
Creates a comprehensive test package with sample data.
```bash
python scripts/create_testkit.py
```

## 🔧 Configuration

### `configure_elastic.sh`
Configure Elasticsearch output connector.
```bash
./scripts/configure_elastic.sh
```

### `configure_splunk.sh`
Configure Splunk HEC output connector.
```bash
./scripts/configure_splunk.sh
```

## 📋 Monitoring

### `logs.sh`
View and follow service logs.
```bash
./scripts/logs.sh
```

## 📁 Sample Data

The `samples/` directory contains example data files for testing:

- `zeek_conn.json` - Zeek connection logs
- `flows_v1.json` - Network flow data

## 🎯 Quick Start

1. **Setup**: `./scripts/bootstrap.sh`
2. **Test**: `./scripts/test_api.sh`
3. **Deploy**: `./scripts/deploy.sh`
4. **Monitor**: `./scripts/logs.sh`

## 📝 Notes

- All scripts use environment variables for configuration
- Test scripts include colored output for better readability
- Scripts are designed to be idempotent and safe to run multiple times
- Error handling is included in all scripts
