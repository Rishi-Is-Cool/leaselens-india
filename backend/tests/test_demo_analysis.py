"""The saved-analysis endpoint must serve the best record it has for each document.

The full-corpus Phase 4 run was cut short by a daily token cap, so most of its clauses
carry an error rather than an explanation. These guard against that file ever shadowing
the verified-clean sample again.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)  # no `with`: these routes never touch the database

MAHARASHTRA = "01_maharashtra_leave_license_mumbai.pdf"


def test_clean_sample_wins_over_the_degraded_full_run():
    document = client.get(f"/analysis/documents/{MAHARASHTRA}").json()
    clauses = document["clauses"]
    assert len(clauses) == 13
    assert all(c["explanation"] for c in clauses), "a clause lost its explanation"
    assert not any(c["error"] for c in clauses)


def test_cross_clause_connections_are_served():
    document = client.get(f"/analysis/documents/{MAHARASHTRA}").json()
    assert len(document["cross_clause"]) >= 1


def test_summary_reports_explanation_coverage_truthfully():
    summaries = {d["filename"]: d for d in client.get("/analysis/documents").json()}
    assert summaries[MAHARASHTRA]["explained_count"] == summaries[MAHARASHTRA]["clause_count"]
    for summary in summaries.values():
        assert 0 <= summary["explained_count"] <= summary["clause_count"]


def test_every_saved_clause_still_has_a_risk_label():
    for summary in client.get("/analysis/documents").json():
        document = client.get(f"/analysis/documents/{summary['filename']}").json()
        for clause in document["clauses"]:
            assert clause["risk_label"] in {"GREEN", "YELLOW", "RED"}


def test_unknown_document_is_a_404_not_a_crash():
    assert client.get("/analysis/documents/nope.pdf").status_code == 404
