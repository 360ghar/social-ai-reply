"""Shared test fixtures and configuration."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app


@pytest.fixture
def db_engine():
    """Create an in-memory SQLite engine with all tables."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Enable foreign key support in SQLite
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """Provide a transactional test database session."""
    SessionLocal = sessionmaker(bind=db_engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def client(db_session):
    """Provide a FastAPI TestClient with DB dependency overridden."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def authed_client(client):
    """Client with a registered user and valid auth headers."""
    response = client.post(
        "/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "testpass123",
            "full_name": "Test User",
            "workspace_name": "Test Workspace",
        },
    )
    assert response.status_code == 201, f"Registration failed: {response.text}"
    token = response.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    yield client, response.json()


@pytest.fixture
def authed_headers(client):
    """Convenience fixture that returns just the auth headers."""
    response = client.post(
        "/v1/auth/register",
        json={
            "email": "headers@example.com",
            "password": "testpass123",
            "full_name": "Header User",
            "workspace_name": "Headers WS",
        },
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
