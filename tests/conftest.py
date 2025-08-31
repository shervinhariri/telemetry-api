import os, time, requests, pytest

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:80")
API_KEY  = os.getenv("API_KEY", "TEST_ADMIN_KEY")

@pytest.fixture(scope="session", autouse=True)
def wait_for_api():
    # Only wait for API if we're in CI/CD or explicitly testing against a container
    if os.getenv("CI") or os.getenv("GITHUB_ACTIONS") or BASE_URL != "http://localhost:80":
        for i in range(60):
            try:
                r = requests.get(f"{BASE_URL}/v1/health", timeout=1.5)
                if r.status_code == 200:
                    print(f"✅ API ready at {BASE_URL} (attempt {i+1})")
                    return
            except Exception:
                pass
            time.sleep(1)
        pytest.fail("API did not become healthy in time")
    else:
        # For local testing, skip the wait
        print("⏭️ Skipping API health check for local testing")

@pytest.fixture(scope="function")
def client():
    # For local testing, use FastAPI TestClient
    if BASE_URL == "http://localhost:80" and not os.getenv("CI") and not os.getenv("GITHUB_ACTIONS"):
        from fastapi.testclient import TestClient
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from app.main import app
        with TestClient(app) as test_client:
            # Add Authorization header to TestClient
            test_client.headers = {"Authorization": f"Bearer {API_KEY}"}
            yield test_client
    else:
        # For container testing, use requests Session
        s = requests.Session()
        s.headers.update({"Authorization": f"Bearer {API_KEY}"})
        try:
            yield s
        finally:
            s.close()
