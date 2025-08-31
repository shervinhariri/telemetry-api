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
    # Admin key used by the app bootstrap (see db_boot)
    return {"Authorization": os.getenv("API_KEY", "TEST_ADMIN_KEY")}

@pytest.fixture
def user_headers():
    # Non-admin key used by several tests
    return {"Authorization": os.getenv("USER_API_KEY", "***")}
