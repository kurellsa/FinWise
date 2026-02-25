"""
Shared test fixtures.

env vars must be set BEFORE any app module is imported because auth.py,
ai_service.py, database.py, and login.py read them at module-load time.
"""
import os
import sys
import bcrypt

# --- env vars set first, before any app imports ---
os.environ["SECRET_KEY"] = "test-secret-key-finwise-pytest"
os.environ["DATABASE_URL"] = "sqlite://"   # overridden via get_db; kept for safety
os.environ["GROQ_API_KEY"] = "fake-groq-key-for-tests"

# login.py reads APP_USERNAME / APP_PASSWORD_HASH at import time (module level)
TEST_USERNAME = "testadmin"
TEST_PASSWORD = "testpassword123"
TEST_PASSWORD_HASH = bcrypt.hashpw(TEST_PASSWORD.encode(), bcrypt.gensalt(rounds=4)).decode()
os.environ["APP_USERNAME"] = TEST_USERNAME
os.environ["APP_PASSWORD_HASH"] = TEST_PASSWORD_HASH

# pytest.ini sets pythonpath = app, but set it explicitly too for IDE compatibility
_APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app"))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture(scope="session", autouse=True)
def set_working_dir():
    """Change CWD to app/ so templates/, static/, uploads/ resolve correctly."""
    original = os.getcwd()
    os.chdir(_APP_DIR)
    yield
    os.chdir(original)


@pytest.fixture()
def db_session():
    """Fresh in-memory SQLite DB per test function. Isolated — never touches Neon."""
    from database import Base

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def client(db_session):
    """Authenticated TestClient backed by an in-memory SQLite DB."""
    from main import app
    from database import get_db
    from fastapi.testclient import TestClient
    from auth import _serializer, COOKIE_NAME

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app, raise_server_exceptions=True) as c:
        token = _serializer.dumps("testuser")
        c.cookies.set(COOKIE_NAME, token)
        yield c

    app.dependency_overrides.clear()


@pytest.fixture()
def anon_client(db_session):
    """Unauthenticated TestClient — used to verify redirect-to-login behaviour."""
    from main import app
    from database import get_db
    from fastapi.testclient import TestClient

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app, raise_server_exceptions=True, follow_redirects=False) as c:
        yield c

    app.dependency_overrides.clear()
