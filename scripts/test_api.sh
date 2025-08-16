#!/bin/bash
set -euo pipefail

# Comprehensive API Test Script for Telemetry API
# Tests all essential endpoints and functionality

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="${BASE_URL:-http://localhost}"
API_KEY="${API_KEY:-TEST_KEY}"
TIMEOUT=10

# Helper functions
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# Test function
test_endpoint() {
    local name="$1"
    local method="$2"
    local endpoint="$3"
    local data_file="${4:-}"
    local expected_status="${5:-200}"
    
    log_info "Testing $name..."
    
    local curl_cmd="curl -s -w '\n%{http_code}' -X $method '$BASE_URL$endpoint'"
    
    if [[ -n "$data_file" ]]; then
        curl_cmd="$curl_cmd -H 'Authorization: Bearer $API_KEY' -H 'Content-Type: application/json' --data @$data_file"
    elif [[ "$method" != "GET" ]]; then
        curl_cmd="$curl_cmd -H 'Authorization: Bearer $API_KEY'"
    fi
    
    local response
    response=$(eval "$curl_cmd" 2>/dev/null || echo "FAILED")
    
    if [[ "$response" == "FAILED" ]]; then
        log_error "$name failed - connection error"
        return 1
    fi
    
    local http_code
    http_code=$(echo "$response" | tail -n1)
    local body
    body=$(echo "$response" | sed '$d')
    
    if [[ "$http_code" == "$expected_status" ]]; then
        log_success "$name passed (HTTP $http_code)"
        if [[ -n "$body" ]]; then
            echo "$body" | jq . 2>/dev/null || echo "$body"
        fi
        return 0
    else
        log_error "$name failed - expected HTTP $expected_status, got $http_code"
        echo "$body"
        return 1
    fi
}

# Main test execution
main() {
    echo "🧪 Telemetry API Comprehensive Test Suite"
    echo "=========================================="
    echo "Base URL: $BASE_URL"
    echo "API Key: $API_KEY"
    echo ""
    
    local failed_tests=0
    local total_tests=0
    
    # Test 1: Health endpoint (no auth required)
    ((total_tests++))
    if test_endpoint "Health Check" "GET" "/v1/health"; then
        log_success "Health endpoint working"
    else
        ((failed_tests++))
    fi
    echo ""
    
    # Test 2: Version endpoint
    ((total_tests++))
    if test_endpoint "Version" "GET" "/v1/version"; then
        log_success "Version endpoint working"
    else
        ((failed_tests++))
    fi
    echo ""
    
    # Test 3: System info
    ((total_tests++))
    if test_endpoint "System Info" "GET" "/v1/system"; then
        log_success "System endpoint working"
    else
        ((failed_tests++))
    fi
    echo ""
    
    # Test 4: Metrics endpoint
    ((total_tests++))
    if test_endpoint "Metrics" "GET" "/v1/metrics" "" 200; then
        log_success "Metrics endpoint working"
    else
        ((failed_tests++))
    fi
    echo ""
    
    # Test 5: Ingest endpoint (with sample data)
    ((total_tests++))
    if [[ -f "samples/zeek_conn.json" ]]; then
        if test_endpoint "Ingest" "POST" "/v1/ingest" "samples/zeek_conn.json"; then
            log_success "Ingest endpoint working"
        else
            ((failed_tests++))
        fi
    else
        log_warning "Skipping ingest test - samples/zeek_conn.json not found"
    fi
    echo ""
    
    # Test 6: Logs endpoint
    ((total_tests++))
    if test_endpoint "Logs" "GET" "/v1/logs?limit=5"; then
        log_success "Logs endpoint working"
    else
        ((failed_tests++))
    fi
    echo ""
    
    # Test 7: Lookup endpoint
    ((total_tests++))
    local lookup_data='{"value": "8.8.8.8"}'
    if echo "$lookup_data" | curl -s -X POST "$BASE_URL/v1/lookup" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        --data @- > /dev/null 2>&1; then
        log_success "Lookup endpoint working"
    else
        log_warning "Lookup endpoint not available (optional)"
    fi
    echo ""
    
    # Test 8: Requests endpoint (optional)
    ((total_tests++))
    if test_endpoint "Requests" "GET" "/v1/requests?limit=10"; then
        log_success "Requests endpoint working"
    else
        log_warning "Requests endpoint not available (optional)"
    fi
    echo ""
    
    # Summary
    echo "=========================================="
    echo "Test Summary:"
    echo "  Total tests: $total_tests"
    echo "  Passed: $((total_tests - failed_tests))"
    echo "  Failed: $failed_tests"
    
    if [[ $failed_tests -eq 0 ]]; then
        log_success "All tests passed! 🎉"
        exit 0
    else
        log_error "Some tests failed. Check the output above."
        exit 1
    fi
}

# Run main function
main "$@"
