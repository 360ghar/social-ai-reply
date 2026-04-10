"""Shared test fixtures and configuration.

In test mode, we mock Supabase auth by:
1. Overriding verify_supabase_jwt to accept test tokens
2. Creating AccountUser records directly in the DB
3. Generating simple test tokens that our mock verifier accepts
"""

import uuid
from unittest.mock import patch

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import AccountUser, Membership, MembershipRole, Workspace
from app.db.session import get_db
from app.main import app
from app.middleware import reset_rate_limit_store
from app.services.product.entitlements import get_or_create_subscription, seed_plan_entitlements
from app.utils.slug import unique_slug

# ── Test token helpers ───────────────────────────────────────────

def _make_test_token(supabase_user_id: str) -> str:
    """Create a simple test token that encodes the Supabase user ID.

    This is NOT a real JWT — it's a test-only token that our mock
    verify_supabase_jwt function knows how to decode.
    """
    return f"test-token-{supabase_user_id}"


def _mock_verify_supabase_jwt(token: str) -> dict:
    """Mock JWT verifier for tests.

    Accepts tokens in the format 'test-token-<supabase_user_id>' and
    returns a payload matching what Supabase would return. Raises
    ``jwt.InvalidTokenError`` for unrecognized tokens so the route's
    ``_verify_bearer`` helper maps them to 401, matching the real
    ``verify_supabase_jwt`` behavior.
    """
    if not token.startswith("test-token-"):
        raise jwt.InvalidTokenError("Invalid test token")
    supabase_uid = token.removeprefix("test-token-")
    return {
        "sub": supabase_uid,
        "aud": "authenticated",
        "exp": 9999999999,
        "iat": 1000000000,
        "email": f"{supabase_uid}@test.local",
        "role": "authenticated",
    }


def _make_mock_supabase_signup():
    """Create a test-local Supabase signup mock with stable IDs per email."""
    email_to_uid: dict[str, str] = {}

    def _mock_supabase_signup(email: str, password: str, full_name: str) -> dict:
        del password
        uid = email_to_uid.setdefault(email, str(uuid.uuid4()))
        return {
            "access_token": _make_test_token(uid),
            "refresh_token": f"refresh-{uid}",
            "user": {
                "id": uid,
                "email": email,
                "email_confirmed_at": "2025-01-01T00:00:00Z",
                "user_metadata": {"full_name": full_name},
            },
        }

    return _mock_supabase_signup


# ── Database fixtures ────────────────────────────────────────────


@pytest.fixture
def db_engine():
    """Create an in-memory SQLite engine with all tables."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

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
    session_factory = sessionmaker(bind=db_engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session = session_factory()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def reset_rate_limits():
    """Keep the in-memory rate limiter isolated across tests."""
    reset_rate_limit_store()
    yield
    reset_rate_limit_store()


@pytest.fixture(autouse=True)
def mock_supabase_auth():
    """Keep the test suite offline by mocking auth verification + signup."""
    with (
        patch("app.api.v1.deps.verify_supabase_jwt", side_effect=_mock_verify_supabase_jwt),
        patch("app.api.v1.routes.auth.verify_supabase_jwt", side_effect=_mock_verify_supabase_jwt),
        patch("app.api.v1.routes.auth.sign_up", side_effect=_make_mock_supabase_signup()),
    ):
        yield


@pytest.fixture
def client(db_session):
    """Provide a FastAPI TestClient with DB dependency overridden and Supabase JWT mocked."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    yield TestClient(app)

    app.dependency_overrides.clear()


def _create_test_user(db_session: Session, email: str, full_name: str, workspace_name: str) -> dict:
    """Create a user + workspace + membership directly in the DB (bypassing Supabase).

    Returns a dict matching the AuthResponse shape so tests can use it as before.
    """
    supabase_uid = str(uuid.uuid4())

    user = AccountUser(
        supabase_user_id=supabase_uid,
        email=email,
        full_name=full_name,
    )
    db_session.add(user)
    db_session.flush()

    workspace = Workspace(
        name=workspace_name,
        slug=unique_slug(db_session, Workspace, workspace_name),
        owner_user_id=user.id,
    )
    db_session.add(workspace)
    db_session.flush()
    db_session.add(Membership(workspace_id=workspace.id, user_id=user.id, role=MembershipRole.OWNER))
    db_session.commit()
    seed_plan_entitlements(db_session)
    get_or_create_subscription(db_session, workspace)

    token = _make_test_token(supabase_uid)

    return {
        "access_token": token,
        "refresh_token": None,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "supabase_user_id": supabase_uid,
            "email": email,
            "full_name": full_name,
            "is_active": True,
        },
        "workspace": {
            "id": workspace.id,
            "name": workspace.name,
            "slug": workspace.slug,
            "role": "owner",
        },
    }


@pytest.fixture
def authed_client(client, db_session):
    """Client with a registered user and valid auth headers."""
    data = _create_test_user(db_session, "test@example.com", "Test User", "Test Workspace")
    client.headers.update({"Authorization": f"Bearer {data['access_token']}"})
    yield client, data


@pytest.fixture
def authed_headers(client, db_session):
    """Convenience fixture that returns just the auth headers."""
    data = _create_test_user(db_session, "headers@example.com", "Header User", "Headers WS")
    return {"Authorization": f"Bearer {data['access_token']}"}
