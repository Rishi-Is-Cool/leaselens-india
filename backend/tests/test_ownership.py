"""On a shared host, a browser sees only the leases it uploaded, and expensive endpoints
are rate-limited per visitor."""

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal, create_tables
from app.main import app
from app.models import Document
from app.ratelimit import RateLimiter

pytestmark = pytest.mark.skipif(SessionLocal is None, reason="DATABASE_URL not configured")

LEASE = Path(__file__).resolve().parents[2] / "data" / "test-leases" / "01_maharashtra_leave_license_mumbai.pdf"
client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _tables():
    create_tables()


@pytest.fixture
def alice():
    """A lease uploaded by one browser; yields (client id, document id)."""
    client_id = f"alice-{uuid.uuid4()}"
    body = client.post(
        "/documents",
        files={"file": (LEASE.name, LEASE.read_bytes(), "application/pdf")},
        headers={"X-Client-Id": client_id},
    ).json()
    yield client_id, body["id"]
    session = SessionLocal()
    document = session.get(Document, uuid.UUID(body["id"]))
    if document is not None:
        session.delete(document)
        session.commit()
    session.close()


def as_(client_id):
    return {"X-Client-Id": client_id} if client_id else {}


def test_the_owner_sees_and_opens_their_lease(alice):
    owner, document_id = alice
    listed = client.get("/documents", headers=as_(owner)).json()
    assert [d["id"] for d in listed] == [document_id]
    assert client.get(f"/documents/{document_id}", headers=as_(owner)).status_code == 200
    assert client.get(f"/documents/{document_id}/analysis", headers=as_(owner)).status_code == 200


@pytest.mark.parametrize("stranger", ["bob", None])
def test_anyone_else_cannot_list_open_review_or_chat_about_it(alice, stranger):
    _, document_id = alice
    assert document_id not in [d["id"] for d in client.get("/documents", headers=as_(stranger)).json()]
    assert client.get(f"/documents/{document_id}", headers=as_(stranger)).status_code == 404
    assert client.get(f"/documents/{document_id}/analysis", headers=as_(stranger)).status_code == 404
    assert client.post(f"/documents/{document_id}/analysis", json={}, headers=as_(stranger)).status_code == 404
    assert client.post(f"/documents/{document_id}/chat", json={"question": "rent?"},
                       headers=as_(stranger)).status_code == 404
    assert client.delete(f"/documents/{document_id}", headers=as_(stranger)).status_code == 404


def test_without_a_client_id_nothing_is_listed():
    assert client.get("/documents").json() == []


def test_the_owner_can_delete_now(alice):
    owner, document_id = alice
    assert client.delete(f"/documents/{document_id}", headers=as_(owner)).status_code == 204
    assert client.get(f"/documents/{document_id}", headers=as_(owner)).status_code == 404


def test_rate_limiter_blocks_past_the_limit_and_recovers_after_the_window():
    limiter = RateLimiter(limit=2, window=60)
    assert limiter.allow("1.2.3.4", now=0) and limiter.allow("1.2.3.4", now=1)
    assert not limiter.allow("1.2.3.4", now=2)
    assert limiter.allow("5.6.7.8", now=2), "limits are per visitor"
    assert limiter.allow("1.2.3.4", now=61)


def test_a_limit_of_zero_is_off():
    limiter = RateLimiter(limit=0)
    assert all(limiter.allow("x") for _ in range(100))
