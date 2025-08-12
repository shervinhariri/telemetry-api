#!/bin/bash
set -euo pipefail

# Test Runner Script for Telemetry API

echo "🧪 Running Telemetry API tests..."

# Check if we're in a virtual environment
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Consider using a virtual environment"
fi

# Install test dependencies if needed
if ! python -c "import pytest" 2>/dev/null; then
    echo "📦 Installing test dependencies..."
    pip install -r requirements.txt
fi

# Run unit and integration tests
echo "🔍 Running API tests..."
python -m pytest tests/test_api.py -v

# Validate schemas
echo "📋 Validating schemas..."
python tests/validate_schemas.py

echo "✅ All tests completed!"
