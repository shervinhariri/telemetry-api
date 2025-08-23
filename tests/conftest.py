import pytest
import os
import sys
from fastapi.testclient import TestClient

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.main import app
from app.db import engine, Base
from app.models.tenant import Tenant
from app.models.apikey import ApiKey
import hashlib

@pytest.fixture(scope="session")
def test_db():
    """Set up test database"""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Set up test tenant and API key
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Create test tenant
    tenant = session.query(Tenant).filter_by(tenant_id="default").one_or_none()
    if not tenant:
        tenant = Tenant(tenant_id="default", name="Test Tenant")
        session.add(tenant)
        session.commit()
    
    # Create test admin API key
    test_admin_key = "TEST_ADMIN_KEY"
    key_hash = hashlib.sha256(test_admin_key.encode()).hexdigest()
    
    api_key = session.query(ApiKey).filter_by(key_id="admin", tenant_id="default").one_or_none()
    if not api_key:
        api_key = ApiKey(
            key_id="admin", 
            tenant_id="default", 
            hash=key_hash,
            scopes=["admin", "ingest", "read_metrics", "export", "manage_indicators"]
        )
        session.add(api_key)
        session.commit()
    
    session.close()
    
    yield
    
    # Clean up
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(test_db):
    """Test client with initialized database"""
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def admin_headers():
    """Headers with admin API key"""
    return {"Authorization": "Bearer TEST_ADMIN_KEY"}

@pytest.fixture
def user_headers():
    """Headers with user API key (no admin)"""
    return {"Authorization": "Bearer user-key"}
