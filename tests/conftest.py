import os
import shutil
import tempfile
import pytest
from fastapi.testclient import TestClient

# Configure test environment variables before importing app
os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = "sqlite:///./test_database.db"
temp_storage = tempfile.mkdtemp()
os.environ["LOCAL_STORAGE_DIR"] = temp_storage

from backend.main import app
from backend.database.session import init_db, engine
from backend.database.base import Base


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test database and clean up temporary storage after test session."""
    init_db()
    yield
    # Teardown
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists("./test_database.db"):
        try:
            os.remove("./test_database.db")
        except Exception:
            pass
    if os.path.exists(temp_storage):
        shutil.rmtree(temp_storage, ignore_errors=True)


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    with TestClient(app) as test_client:
        yield test_client
