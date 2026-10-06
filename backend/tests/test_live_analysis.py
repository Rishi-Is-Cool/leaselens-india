"""Live analysis of an uploaded lease: state inference, the background job, persistence,
and that provider errors never reach the browser.

CI has no LLM key, so these exercise the offline path the app falls back to: risk levels
from the trained classifier and statutes from deterministic retrieval.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.analysis.service import public_error
from app.db import SessionLocal, create_tables
from app.main import app
from app.models import Analysis, Document

pytestmark = pytest.mark.skipif(SessionLocal is None, reason="DATABASE_URL not configured")

LEASES = Path(__file__).resolve().parents[2] / "data" / "test-leases"
client = TestClient(app)  # no `with`: skips the startup model warm-up thread


@pytest.fixture(scope="module", autouse=True)
def _tables():
    create_tables()


@pytest.fixture
def uploaded():
    created = []

    def upload(name: str) -> dict:
        body = client.post(
            "/documents", files={"file": (name, (LEASES / name).read_bytes(), "application/pdf")}
        ).json()
        created.append(body["id"])
        return body

    yield upload
    session = SessionLocal()
    try:
        for document_id in created:
            document = session.get(Document, document_id)
            if document is not None:
                session.delete(document)
        session.commit()
    finally:
        session.close()


def test_before_a_run_the_state_is_inferred_but_nothing_has_started(uploaded):
    document = uploaded("01_maharashtra_leave_license_mumbai.pdf")
    state = client.get(f"/documents/{document['id']}/analysis").json()
    assert state["status"] == "not_started"
    assert state["result"] is None
    assert state["jurisdiction_hint"]["jurisdiction"] == "Maharashtra"
    assert "mumbai" in state["jurisdiction_hint"]["evidence"]
    assert set(state["supported_jurisdictions"]) == {"Maharashtra", "Delhi"}


def test_a_run_labels_every_clause_and_matches_the_confirmed_states_law(uploaded):
    document = uploaded("01_maharashtra_leave_license_mumbai.pdf")
    started = client.post(f"/documents/{document['id']}/analysis", json={"jurisdiction": "Maharashtra"})
    assert started.status_code == 202

    state = client.get(f"/documents/{document['id']}/analysis").json()
    assert state["status"] == "done"
    assert state["progress"] == {"done": 13, "total": 13}
    clauses = state["result"]["clauses"]
    assert len(clauses) == 13
    assert all(c["risk_label"] in {"GREEN", "YELLOW", "RED"} for c in clauses)
    statutes = [s for c in clauses for s in c["retrieved_statutes"]]
    assert statutes, "a Maharashtra lease should match at least one statute"
    assert all(s["jurisdiction"] in {"Maharashtra", "Central"} for s in statutes)
    assert all(s["source_url"].startswith("http") for s in statutes)


def test_without_a_provider_explanations_are_skipped_not_failed(uploaded, monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    document = uploaded("02_delhi_rent_agreement.pdf")
    client.post(f"/documents/{document['id']}/analysis", json={"jurisdiction": "Delhi"})
    state = client.get(f"/documents/{document['id']}/analysis").json()
    assert state["explanations_available"] is False
    assert all(c["explanation"] is None and c["error"] is None for c in state["result"]["clauses"])
    assert state["result"]["cross_clause"] == []


def test_another_state_runs_without_any_statute_retrieval(uploaded):
    document = uploaded("03_karnataka_rental_agreement_bangalore.pdf")
    hint = client.get(f"/documents/{document['id']}/analysis").json()["jurisdiction_hint"]
    assert hint["jurisdiction"] is None and hint["unsupported_state"] == "Karnataka"

    client.post(f"/documents/{document['id']}/analysis", json={"jurisdiction": None})
    state = client.get(f"/documents/{document['id']}/analysis").json()
    assert state["status"] == "done"
    assert all(c["retrieved_statutes"] == [] for c in state["result"]["clauses"])


def test_unsupported_jurisdiction_is_rejected(uploaded):
    document = uploaded("02_delhi_rent_agreement.pdf")
    response = client.post(f"/documents/{document['id']}/analysis", json={"jurisdiction": "Atlantis"})
    assert response.status_code == 422


def test_a_second_start_while_running_is_refused(uploaded):
    document = uploaded("02_delhi_rent_agreement.pdf")
    session = SessionLocal()
    try:
        session.add(Analysis(document_id=document["id"], status="running", progress_total=12))
        session.commit()
    finally:
        session.close()
    response = client.post(f"/documents/{document['id']}/analysis", json={"jurisdiction": "Delhi"})
    assert response.status_code == 409


def test_unknown_document_is_a_404():
    response = client.get("/documents/00000000-0000-0000-0000-000000000000/analysis")
    assert response.status_code == 404


def test_the_analysis_is_deleted_with_its_document(uploaded):
    document = uploaded("02_delhi_rent_agreement.pdf")
    client.post(f"/documents/{document['id']}/analysis", json={"jurisdiction": "Delhi"})
    session = SessionLocal()
    try:
        session.delete(session.get(Document, document["id"]))
        session.commit()
        assert session.get(Analysis, document["id"]) is None
    finally:
        session.close()


@pytest.mark.parametrize(
    "raw",
    [
        "explanation generation failed: qwen/qwen3.8-27b hit its free-tier daily limit: "
        '{"error":{"message":"Rate limit reached in organization `org_01exampleexampleexample00`"}}',
        "explanation generation failed: HTTP 429 Too Many Requests",
        "explanation generation failed: connection reset",
        "classification failed: model missing",
    ],
)
def test_provider_errors_never_reach_the_browser(raw):
    public = public_error(raw)
    assert public
    for leak in ("org_", "qwen", "Rate limit", "429", "HTTP", "model missing"):
        assert leak not in public
