# Authentication Fixes Summary

## Problem
The e2e tests were failing with 401/403 errors on admin-gated endpoints because:
1. The API was not recognizing the test admin key
2. Header parsing was not flexible enough
3. Admin endpoints were not properly protected

## Solution Implemented

### 1. Centralized Key Management (`app/auth/keys.py`)
- Created a new centralized key management system
- Environment-driven configuration with sensible defaults
- Support for multiple admin and user keys
- Legacy compatibility with existing `API_KEY` env var

**Key Environment Variables:**
- `DEV_ADMIN_KEY`: Default admin key (defaults to `DEV_ADMIN_KEY_5a8f9ffdc3`)
- `DEV_USER_KEY`: Default user key (defaults to `DEV_USER_KEY_2c9d1a4b61`)
- `ALLOW_DEV_KEYS`: Whether to include dev keys (defaults to `true`)
- `ADMIN_KEYS`: Comma-separated additional admin keys
- `USER_KEYS`: Comma-separated additional user keys

### 2. Enhanced Header Parsing (`app/auth/__init__.py`)
- **Bearer format**: `Authorization: Bearer <key>` (primary)
- **Raw format**: `Authorization: <key>` (fallback)
- **X-API-Key format**: `X-API-Key: <key>` (alternative)
- Lenient parsing that accepts multiple formats

### 3. Proper Admin Protection
- **System endpoint** (`/v1/system`): Now requires admin scope
- **Outputs endpoints** (`/v1/outputs/*`): All require admin scope
- **Jobs endpoints** (`/v1/jobs/*`): Already properly protected
- **Geo download** (`/v1/geo/download`): Properly protected in jobs.py

### 4. Updated Test Configuration
- **`tests/conftest.py`**: Updated to use new key system
- **`tests/e2e/test_p1_features.py`**: Updated to use environment variables
- **`.github/workflows/scenario-tests.yml`**: Added proper environment variables

### 5. Fixed Duplicate Routes
- Removed duplicate `/geo/download` endpoint from `geo.py`
- Kept the properly protected version in `jobs.py`

## Files Modified

### New Files
- `app/auth/keys.py` - Centralized key management

### Modified Files
- `app/auth/__init__.py` - Enhanced auth with lenient header parsing
- `app/api/system.py` - Added admin requirement
- `app/api/outputs.py` - Added admin requirement to all endpoints
- `app/api/geo.py` - Removed duplicate endpoints
- `app/main.py` - Moved system router to secured section
- `tests/conftest.py` - Updated to use new key system
- `tests/e2e/test_p1_features.py` - Updated to use environment variables
- `.github/workflows/scenario-tests.yml` - Added environment variables
- `test_auth.py` - Test script for verification

## Expected Behavior

### Public Endpoints (no auth required)
- `/v1/health` - Health check
- `/v1/version` - Version info
- `/docs` - Swagger UI
- `/openapi.json` - OpenAPI spec

### Admin-Protected Endpoints (require admin scope)
- `/v1/system` - System information
- `/v1/outputs/*` - All outputs operations
- `/v1/jobs/*` - All jobs operations
- `/v1/geo/download` - GeoIP download

### Header Formats Accepted
1. `Authorization: Bearer DEV_ADMIN_KEY_5a8f9ffdc3` ✓
2. `Authorization: DEV_ADMIN_KEY_5a8f9ffdc3` ✓
3. `X-API-Key: DEV_ADMIN_KEY_5a8f9ffdc3` ✓

## Testing

### Local Testing
```bash
# Start the API
docker-compose up -d

# Run the test script
python3 test_auth.py
```

### Expected Results
- Health endpoint: 200 (no auth)
- System endpoint with admin key: 200
- System endpoint with user key: 403
- System endpoint without auth: 401
- All header formats should work with admin key

### CI Testing
The GitHub Actions workflow now includes:
- `DEV_ADMIN_KEY: DEV_ADMIN_KEY_5a8f9ffdc3`
- `DEV_USER_KEY: DEV_USER_KEY_2c9d1a4b61`
- `ALLOW_DEV_KEYS: "true"`
- `TEST_API_KEY: DEV_ADMIN_KEY_5a8f9ffdc3`

## Benefits

1. **Flexible Authentication**: Multiple header formats supported
2. **Environment-Driven**: Easy to configure for different environments
3. **Proper Security**: Admin endpoints properly protected
4. **Test Compatibility**: E2E tests should now pass
5. **Maintainable**: Centralized key management
6. **Backward Compatible**: Existing `API_KEY` still works

## Next Steps

1. **Test Locally**: Run `test_auth.py` to verify fixes
2. **Run E2E Tests**: Verify all tests pass
3. **Deploy to CI**: Push changes and verify CI passes
4. **Monitor**: Watch for any remaining auth issues

## Troubleshooting

### If tests still fail:
1. Check environment variables are set correctly
2. Verify API is running and accessible
3. Check logs for authentication errors
4. Ensure Bearer prefix is included in test headers

### Common Issues:
- **401 errors**: Check if key is recognized by the system
- **403 errors**: Check if key has admin scope
- **Header parsing**: Ensure Authorization header format is correct
