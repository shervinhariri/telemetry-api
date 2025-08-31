import pytest
import os
import sys
import time
import requests
from fastapi.testclient import TestClient

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.main import app

@pytest.fixture(scope="session")
def api():
    """
    HTTP-only API fixture that waits for the container to be ready.
    Returns base URL and API key for making HTTP requests.
    """
    # Read configuration from environment
    base_url = os.getenv("API_BASE_URL", "http://localhost")
    api_key = os.getenv("API_KEY", "DEV_ADMIN_KEY_5a8f9ffdc3")
    
    # If we're in CI/CD or explicitly testing against a container, wait for the API
    if os.getenv("CI") or os.getenv("GITHUB_ACTIONS") or base_url != "http://localhost":
        # Wait for the API to be ready (up to 60 seconds)
        health_url = f"{base_url}/v1/health"
        max_wait = 60
        wait_interval = 2
        
        for attempt in range(max_wait // wait_interval):
            try:
                response = requests.get(health_url, timeout=5)
                if response.status_code == 200:
                    print(f"✅ API ready at {base_url} (attempt {attempt + 1})")
                    break
            except requests.RequestException:
                pass
            
            if attempt < (max_wait // wait_interval) - 1:
                print(f"⏳ Waiting for API at {base_url}... (attempt {attempt + 1})")
                time.sleep(wait_interval)
        else:
            raise RuntimeError(f"API not ready after {max_wait} seconds at {base_url}")
    
    return {
        "base": base_url,
        "key": api_key
    }

@pytest.fixture
def client(api):
    """
    Test client for local testing (when not using container)
    """
    # If we're testing against a remote API, use requests
    if api["base"] != "http://localhost":
        return None
    
    # For local testing, use FastAPI TestClient
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def admin_headers(api):
    """Headers with admin API key"""
    return {"Authorization": f"Bearer {api['key']}"}

@pytest.fixture
def user_headers(api):
    """Headers with user API key (no admin) - for testing permission boundaries"""
    # For now, use the same key but this could be extended
    return {"Authorization": f"Bearer {api['key']}"}
