#!/bin/bash

# Generate checksums for Telemetry API project files
# Usage: ./tools/checksums.sh [VERSION]

set -e

VERSION=${1:-0.8.10}
OUTPUT_FILE="checksums-${VERSION}.txt"

echo "Generating checksums for version ${VERSION}..."

# Clear output file
> ${OUTPUT_FILE}

# Function to add checksum if file exists
add_checksum() {
    local file="$1"
    if [ -f "$file" ]; then
        echo "Adding checksum for $file"
        sha256sum "$file" >> ${OUTPUT_FILE}
    else
        echo "Warning: $file not found, skipping"
    fi
}

# Add checksums for key files
add_checksum "docker-compose.yml"
add_checksum "docker-compose.override.yml"
add_checksum "Dockerfile"
add_checksum "requirements.txt"
add_checksum "VERSION"
add_checksum "CHANGELOG.md"
add_checksum "README.md"

# Add checksums for scripts
add_checksum "scripts/verify_allinone.sh"
add_checksum "scripts/generate_test_netflow.py"

# Add checksums for configuration files
add_checksum "LOGGING.yaml"
add_checksum ".env.example"
add_checksum "gitleaks.toml"

# Add checksums for documentation
add_checksum "docs/LOGGING.md"
add_checksum "SECURITY.md"

# Add checksums for SBOM files if they exist
add_checksum "sbom-${VERSION}.spdx.json"
add_checksum "sbom-${VERSION}.txt"

echo "Checksums saved to ${OUTPUT_FILE}"
echo "Total files checksummed: $(wc -l < ${OUTPUT_FILE})"
