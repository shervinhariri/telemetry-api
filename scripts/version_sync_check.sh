#!/bin/bash
set -euo pipefail

# Version sync check script
# Fails CI if curl /v1/version ≠ v$(cat VERSION)

VERSION_FILE="$(cat VERSION)"
EXPECTED_VERSION="v${VERSION_FILE}"

echo "Checking version sync..."
echo "VERSION file: ${VERSION_FILE}"
echo "Expected API version: ${EXPECTED_VERSION}"

# Wait for container to be ready
for i in {1..30}; do
    if curl -sf http://localhost/v1/health >/dev/null 2>&1; then
        break
    fi
    echo "Waiting for health endpoint... ($i/30)"
    sleep 2
done

# Get actual version from API
ACTUAL_VERSION=$(curl -sf http://localhost/v1/version | jq -r '.version')

echo "Actual API version: ${ACTUAL_VERSION}"

if [ "$ACTUAL_VERSION" = "$EXPECTED_VERSION" ]; then
    echo "✅ Version sync check passed"
    exit 0
else
    echo "❌ Version sync check failed"
    echo "Expected: $EXPECTED_VERSION"
    echo "Got: $ACTUAL_VERSION"
    exit 1
fi
