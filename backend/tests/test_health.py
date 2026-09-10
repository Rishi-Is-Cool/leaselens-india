from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_200():
    response = client.get("/health")
    assert response.status_code == 200


def test_health_payload_shape():
    body = client.get("/health").json()
    assert body["status"] in {"ok", "degraded"}
    assert body["service"]
    assert "connected" in body["database"]


def test_health_never_leaks_credentials():
    """A failed DB connect must not surface the DSN (and its password) to callers."""
    body = client.get("/health").json()
    error = body["database"]["error"]
    assert error is None or "://" not in error
