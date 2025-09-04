#!/bin/bash

# Build SBOM for Telemetry API Docker image
# Usage: ./tools/build_sbom.sh [VERSION] [IMAGE_NAME]

set -e

VERSION=${1:-0.8.11}
IMAGE_NAME=${2:-shvin/telemetry-api}

echo "Generating SBOM for ${IMAGE_NAME}:${VERSION}"

# Generate SPDX JSON format
echo "Creating SPDX JSON SBOM..."
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  anchore/syft:latest \
  ${IMAGE_NAME}:${VERSION} \
  -o spdx-json > sbom-${VERSION}.spdx.json

# Generate table format for readability
echo "Creating table format SBOM..."
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  anchore/syft:latest \
  ${IMAGE_NAME}:${VERSION} \
  -o table > sbom-${VERSION}.txt

echo "SBOM files created:"
echo "  - sbom-${VERSION}.spdx.json (SPDX JSON format)"
echo "  - sbom-${VERSION}.txt (Table format)"

# Generate checksums
echo "Generating checksums..."
sha256sum sbom-${VERSION}.spdx.json > checksums-${VERSION}.txt
sha256sum sbom-${VERSION}.txt >> checksums-${VERSION}.txt

echo "Checksums saved to checksums-${VERSION}.txt"
