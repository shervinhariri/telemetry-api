# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.8.x   | :white_check_mark: |
| < 0.8   | :x:                |

## Secrets Handling Policy

### Environment Variables
- **Never commit real secrets** to the repository
- Use `.env` files for local development (not committed)
- Use GitHub Secrets for CI/CD
- Reference `.env.example` for required variables

### Required Environment Variables
```bash
# API Authentication
API_KEY=your-api-key-here
ADMIN_API_KEY=your-admin-api-key-here
BOOTSTRAP_ADMIN_API_KEY=your-bootstrap-admin-key-here

# Docker Registry
DOCKERHUB_USERNAME=your-dockerhub-username
DOCKERHUB_TOKEN=your-dockerhub-token

# External Services
MAXMIND_LICENSE_KEY=your-maxmind-license-key
SPLUNK_HEC_TOKEN=your-splunk-hec-token
ELASTIC_API_KEY=your-elastic-api-key
```

### Token Rotation
1. **API Keys**: Rotate via admin interface or database update
2. **Docker Tokens**: Update GitHub Secrets and redeploy
3. **External Service Tokens**: Update environment variables and restart

## Secret Scanning

### Automated Scanning
- **Gitleaks** runs on every push/PR to `main`
- **Weekly scheduled scans** for historical secrets
- **Fails builds** on detected secrets
- **SARIF reports** uploaded to GitHub Security tab

### Local Secret Scanning
```bash
# Run gitleaks locally
docker run --rm -v ${PWD}:/path zricethezav/gitleaks:latest detect --source="/path" --verbose

# Or with custom config
docker run --rm -v ${PWD}:/path zricethezav/gitleaks:latest detect --source="/path" --config="/path/.gitleaks.toml"
```

### False Positives
- Test keys (`TEST_KEY`, `DEV_ADMIN_KEY_*`) are allowed
- Example values (`your-*-here`) are allowed
- Documentation files are excluded
- Test files are excluded

## Container Security

### Base Image Pinning
- Python base image pinned to specific digest
- Reproducible builds across environments
- Regular updates for security patches

### Vulnerability Scanning
- **Trivy** scans built images for OS/library vulnerabilities
- **Fails on HIGH/CRITICAL** severity issues
- **SARIF reports** uploaded to GitHub Security tab

### Local Image Scanning
```bash
# Install Trivy
brew install trivy  # macOS
# or
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin

# Scan local image
trivy image telemetry-api:latest

# Scan with specific severity
trivy image --severity HIGH,CRITICAL telemetry-api:latest
```

## Dependency Security

### Python Dependencies
- Pinned versions in `requirements.txt`
- Hash verification for critical packages
- Regular dependency updates

### Node.js Dependencies (UI)
- `package-lock.json` ensures reproducible installs
- CI uses `npm ci` for exact version matching

## Reporting Security Issues

### Vulnerability Disclosure
1. **Private disclosure**: Email security@yourdomain.com
2. **GitHub Security Advisories**: Use repository security tab
3. **CVE coordination**: For critical issues

### Response Timeline
- **Critical**: 24 hours
- **High**: 72 hours  
- **Medium**: 1 week
- **Low**: 2 weeks

## Security Best Practices

### Development
- Use pre-commit hooks for secret detection
- Run security scans before commits
- Never commit `.env` files
- Use strong, unique API keys

### Deployment
- Rotate secrets regularly
- Use least-privilege access
- Monitor for suspicious activity
- Keep dependencies updated

### Monitoring
- Log authentication failures
- Monitor API usage patterns
- Alert on unusual access patterns
- Regular security audits
