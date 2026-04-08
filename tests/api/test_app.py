"""API smoke tests for public app endpoints."""

from unittest.mock import patch


def test_health_endpoint(client):
    resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json()["checks"]["api"] == "ok"
    assert resp.json()["checks"]["database"] == "ok"


def test_ready_endpoint(client):
    resp = client.get("/ready")

    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"
    assert resp.json()["checks"]["api"] == "ok"
    assert resp.json()["checks"]["database"] == "ok"


def test_ready_endpoint_returns_503_when_db_unavailable(client):
    with patch("app.main._service_checks", return_value={"api": "ok", "database": "error"}):
        resp = client.get("/ready")

    assert resp.status_code == 503
    assert resp.json()["status"] == "not_ready"
    assert resp.json()["checks"]["database"] == "error"
