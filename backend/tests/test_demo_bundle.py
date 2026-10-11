"""The hosted demo replays a bundled JSON file, so it must stay in step with the saved
analysis and must never carry anything that should not be public."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "frontend" / "public" / "demo-analysis.json"

sys.path.insert(0, str(ROOT / "backend" / "scripts"))
from build_demo_analysis import build  # noqa: E402


def test_bundle_matches_what_the_generator_would_write():
    """Fails if the saved analysis changed but the bundle was not regenerated."""
    assert json.loads(BUNDLE.read_text(encoding="utf-8")) == build(), (
        "frontend/public/demo-analysis.json is stale: run "
        "python scripts/build_demo_analysis.py"
    )


def test_bundle_leaks_nothing_private():
    text = BUNDLE.read_text(encoding="utf-8")
    for needle in ("org_0", "qwen", "gpt-oss", "Rate limit", "raw_reply", "supabase", "sb_secret", "postgresql"):
        assert needle not in text, f"bundle contains {needle!r}"


def test_bundle_has_every_document_with_labels_and_the_clean_sample_explained():
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    assert len(bundle) == 9
    maharashtra = bundle["01_maharashtra_leave_license_mumbai.pdf"]
    assert maharashtra["explained_count"] == maharashtra["clause_count"] == 13
    assert maharashtra["connection_count"] >= 1
    for document in bundle.values():
        assert all(c["risk_label"] in {"GREEN", "YELLOW", "RED"} for c in document["clauses"])


def test_every_sample_ships_its_pdf_and_a_highlight_for_every_clause():
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    for filename, document in bundle.items():
        assert document["pdf"] == f"/samples/{filename}"
        assert (ROOT / "frontend" / "public" / "samples" / filename).exists()
        assert set(document["highlights"]) == {c["clause_id"] for c in document["clauses"]}


def test_production_env_points_at_an_https_api_and_holds_no_secrets():
    lines = [
        line.strip()
        for line in (ROOT / "frontend" / ".env.production").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    settings = dict(line.split("=", 1) for line in lines)
    assert settings["VITE_API_BASE_URL"].startswith("https://")
    assert set(settings) <= {"VITE_API_BASE_URL", "VITE_STATIC_DEMO"}
    for secret in ("KEY", "PASSWORD", "TOKEN", "postgresql"):
        assert all(secret not in line for line in lines)
