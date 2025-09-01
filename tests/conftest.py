# tests/conftest.py
import os
import pytest
import requests

BASE_URL = os.getenv("BASE_URL") or os.getenv("APP_BASE_URL") or "http://localhost:80"

class BaseUrlSession(requests.Session):
    def __init__(self, base_url: str):
        super().__init__()
        self._base = base_url.rstrip("/")

    def request(self, method, url, *args, **kwargs):
        # Allow relative paths like "/v1/health"
        if not url.lower().startswith("http"):
            url = f"{self._base}/{url.lstrip('/')}"
        return super().request(method, url, *args, **kwargs)

@pytest.fixture(scope="session")
def client():
    """
    Detect test environment:
    - Unit test mode: return TestClient (no running container needed)
    - E2E mode: return BaseUrlSession (connects to running container)
    """
    # Check if we're in unit test mode (no running container)
    try:
        # Try to import FastAPI TestClient
        from fastapi.testclient import TestClient
        from app.main import app
        
        # Create TestClient for unit tests
        test_client = TestClient(app)
        # Add a flag to indicate this is a TestClient
        test_client.app = app
        return test_client
        
    except (ImportError, ModuleNotFoundError):
        # Fallback to BaseUrlSession for e2e tests
        return BaseUrlSession(BASE_URL)

@pytest.fixture
def admin_headers():
    # Use new key management system with fallback to legacy
    admin_key = os.getenv("TEST_API_KEY") or os.getenv("DEV_ADMIN_KEY") or os.getenv("API_KEY") or "DEV_ADMIN_KEY_5a8f9ffdc3"
    return {"Authorization": f"Bearer {admin_key}"}

@pytest.fixture
def user_headers():
    # Non-admin key used by several tests
    user_key = os.getenv("DEV_USER_KEY") or "***"
    return {"Authorization": f"Bearer {user_key}"}
