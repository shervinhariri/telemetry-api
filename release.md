# Release Guide

## Pre-Release Checklist

- [ ] All tests passing
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] VERSION file updated (e.g., `0.8.9`)
- [ ] Docker image builds successfully

## Release Commands

### 1. Tag & Push Release

```bash
# Commit all changes
git add -A && git commit -m "release: v$(cat VERSION) (golden) + release workflow"

# Create and push tag
git tag -a "v$(cat VERSION)" -m "Telemetry API v$(cat VERSION)"
git push origin main --tags
```

### 2. Watch Actions

Monitor the GitHub Actions:
- **Docker CI**: Builds and publishes `:latest`, `:v$(cat VERSION)`, `:v$(cat VERSION)-golden`
- **Release**: Creates GitHub Release with SBOM and artifacts

### 3. Verify Golden Release

```bash
# Pull golden image
docker pull shvin/telemetry-api:"v$(cat VERSION)"-golden

# Test golden release
docker rm -f telemetry-api-clean || true
docker run -d --name telemetry-api-clean -p 80:80 shvin/telemetry-api:"v$(cat VERSION)"-golden
sleep 5 && curl -s http://localhost/v1/health

# Full verification
export API_KEY=TEST_KEY
bash scripts/verify_allinone.sh
```

### 4. Post-Release Tasks

- [ ] Run post-release smoke test workflow
- [ ] Verify all images are published
- [ ] Check GitHub Release page
- [ ] Update any external documentation

## Release Assets

- **Docker Images**: `shvin/telemetry-api:"v$(cat VERSION)"-golden`
- **GitHub Release**: https://github.com/shervinhariri/telemetry-api/releases/tag/v$(cat VERSION)
- **SBOM**: SPDX JSON format for security audit
- **Checksums**: File integrity verification

## Rollback Instructions

```bash
# Stop current deployment
docker stop telemetry-api-current

# Pull and run golden release
docker pull shvin/telemetry-api:"v$(cat VERSION)"-golden
docker run -d -p 80:80 \
  -e API_KEY=YOUR_API_KEY \
  --name telemetry-api-golden \
  shvin/telemetry-api:"v$(cat VERSION)"-golden

# Verify rollback
curl -s http://localhost/v1/health | jq
```

## Next Development Cycle

After release, the repository is automatically bumped to `0.8.7-rc1` for the next development cycle.
