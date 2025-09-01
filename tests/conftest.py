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
    In e2e we talk to the running container on http://localhost:80.
    This fixture returns a Session that automatically prefixes the base URL,
    so tests can call client.get('/v1/health') without schema errors.
    """
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
