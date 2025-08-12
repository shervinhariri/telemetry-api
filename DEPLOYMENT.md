# Production Deployment Guide

## 🚀 Quick Start

### 1. Server Setup (Ubuntu 22.04+)
```bash
# Bootstrap the server
./scripts/bootstrap.sh

# Configure environment
cp .env.example .env
# Edit .env with your values
```

### 2. Deploy
```bash
# Deploy the application
./scripts/deploy.sh
```

### 3. Test
```bash
# Test health endpoint
./scripts/test_health.sh

# Test ingest endpoint
./scripts/test_ingest.sh
```

## 📁 File Structure

```
telemetry-api/
├── docker-compose.yml          # Production services
├── Caddyfile                   # Reverse proxy config
├── .env.example               # Environment template
├── scripts/
│   ├── bootstrap.sh           # Server setup
│   ├── deploy.sh              # Deploy application
│   ├── update.sh              # Update API image
│   ├── logs.sh                # View logs
│   ├── test_health.sh         # Health check
│   ├── test_ingest.sh         # Test ingest
│   ├── configure_splunk.sh    # Splunk HEC setup
│   └── configure_elastic.sh   # Elasticsearch setup
├── samples/
│   ├── zeek_conn.json         # Sample Zeek data
│   └── flows_v1.json          # Sample flows data
└── ops/
    ├── fail2ban.local         # Security config
    └── logrotate.d/caddy      # Log rotation
```

## 🔧 Configuration

### Environment Variables (.env)
- `API_KEY`: Bearer token for API authentication
- `API_IMAGE`: Docker image (default: shvin/telemetry-api:latest)
- `DOMAIN`: Your domain (e.g., api.yourdomain.com)
- `SPLUNK_HEC_URL`: Splunk HEC endpoint
- `SPLUNK_HEC_TOKEN`: Splunk HEC token
- `ELASTIC_URL`: Elasticsearch endpoint
- `ELASTIC_USERNAME`: Elasticsearch username
- `ELASTIC_PASSWORD`: Elasticsearch password
- `BASIC_AUTH_USER`: Metrics endpoint username
- `BASIC_AUTH_PASS`: Metrics endpoint password

### Security Features
- **HTTPS**: Automatic Let's Encrypt certificates
- **Rate Limiting**: 120 requests/minute on /v1/ingest
- **Firewall**: UFW with ports 22, 80, 443 only
- **Fail2ban**: Protection against brute force attacks
- **CORS**: Configured for cross-origin requests

## 📊 Monitoring

### Health Check
```bash
curl https://api.yourdomain.com/v1/health
```

### Version Info
```bash
curl https://api.yourdomain.com/v1/version
```

### Schema Information
```bash
curl https://api.yourdomain.com/v1/schema
```

### Metrics (Basic Auth)
```bash
curl -u metrics:password https://api.yourdomain.com/v1/metrics
```

### Logs
```bash
./scripts/logs.sh
```

## 🔄 Operations

### Update API
```bash
./scripts/update.sh
```

### Configure Outputs
```bash
# Splunk HEC
./scripts/configure_splunk.sh

# Elasticsearch
./scripts/configure_elastic.sh
```

### View Logs
```bash
./scripts/logs.sh
```

## 🛡️ Security

### Firewall Rules
- SSH (22): Allowed
- HTTP (80): Allowed (redirects to HTTPS)
- HTTPS (443): Allowed
- All other ports: Denied

### Rate Limiting
- `/v1/ingest`: 120 requests/minute per client (configurable via `RATE_LIMIT_INGEST_RPM`)
- Other endpoints: 600 requests/minute per client (configurable via `RATE_LIMIT_DEFAULT_RPM`)
- Burst: 10 requests for ingest, 50 for others

### Basic Auth
- `/v1/metrics`: Protected with basic authentication

## 📝 Logging

### Caddy Logs
- Location: `/var/log/caddy/`
- Format: JSON
- Rotation: Daily, 52 weeks retention

### Application Logs
- Format: JSON to stdout
- View: `docker compose logs -f api`

## 🚨 Troubleshooting

### Common Issues

1. **Domain not resolving**
   - Check DNS A record points to server IP
   - Verify domain in .env file

2. **HTTPS certificate issues**
   - Ensure port 80 is accessible for Let's Encrypt
   - Check Caddy logs: `docker compose logs caddy`

3. **API not responding**
   - Check API logs: `docker compose logs api`
   - Verify health check: `./scripts/test_health.sh`

4. **Rate limiting**
   - Check Caddy logs for 429 responses
   - Adjust rate limits in Caddyfile if needed

### Debug Commands
```bash
# Check service status
docker compose ps

# View all logs
docker compose logs

# Check firewall
sudo ufw status

# Check fail2ban
sudo fail2ban-client status
```

## 📈 Performance

### Rate Limits
- Ingest: 120 req/min per client
- Health: No limits
- Metrics: Basic auth required

### Resources
- API: Minimal resource usage
- Caddy: Lightweight reverse proxy
- Storage: Logs rotated daily

## 🔗 API Endpoints

- `GET /v1/health` - Health check
- `GET /v1/version` - API version info
- `GET /v1/schema` - Available schemas
- `POST /v1/ingest` - Ingest telemetry data (batch)
- `POST /v1/lookup` - Single IP enrichment
- `GET /v1/metrics` - Metrics (basic auth)
- `POST /v1/outputs/splunk` - Configure Splunk HEC
- `POST /v1/outputs/elastic` - Configure Elasticsearch
- `POST /v1/alerts/rules` - Configure alert rules

## 📞 Support

For issues or questions:
1. Check logs: `./scripts/logs.sh`
2. Verify configuration in `.env`
3. Test endpoints: `./scripts/test_health.sh`
