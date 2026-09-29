import pytest

import app.classifier.api as api
from app.classifier.api import classify_clause
from app.classifier.dataset import LABELS
from app.classifier.llm import parse_answer
from app.classifier.metrics import evaluate

# approach="trained" everywhere here: it's offline and deterministic. The default
# ("llm") calls a real network API and is exercised separately, with the network mocked.


def test_classify_clause_returns_label_confidence_and_probabilities():
    result = classify_clause("The Tenant waives any right to sue for wrongful eviction.", approach="trained")
    assert result.label in LABELS
    assert 0.0 <= result.confidence <= 1.0
    assert set(result.probabilities) == set(LABELS)
    assert abs(sum(result.probabilities.values()) - 1.0) < 1e-6
    assert result.confidence == pytest.approx(result.probabilities[result.label])
    assert result.approach == "trained"


def test_classify_clause_rejects_empty_text():
    with pytest.raises(ValueError):
        classify_clause("   ", approach="trained")


def test_classify_clause_falls_back_to_trained_when_llm_fails(monkeypatch):
    """A rate limit or outage must degrade gracefully, not break every classification."""

    def boom(_text):
        raise RuntimeError("simulated: free-tier daily quota exceeded")

    monkeypatch.setattr(api, "_llm_probs", boom)
    result = classify_clause("Tenant shall pay a late fee of 10 percent.", approach="llm")
    assert result.label in LABELS
    assert result.approach == "trained (llm fallback)"


def test_llm_reply_is_parsed_and_normalised():
    probs = parse_answer('Sure: {"label": "RED", "probabilities": {"GREEN": 0.1, "YELLOW": 0.2, "RED": 0.7}}')
    assert max(probs, key=probs.get) == "RED"
    assert sum(probs.values()) == pytest.approx(1.0)


def test_llm_reply_without_json_is_rejected():
    with pytest.raises(ValueError):
        parse_answer("I think this is risky.")


def test_metrics_confusion_and_f1():
    report = evaluate("x", ["GREEN", "GREEN", "RED", "YELLOW"], ["GREEN", "RED", "RED", "YELLOW"])
    assert report.accuracy == 0.75
    assert report.confusion[0].tolist() == [1, 0, 1]
    assert report.per_class["RED"]["recall"] == 1.0


def test_indian_eval_set_is_well_formed():
    import csv
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "data" / "indian_eval_set.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    # 27 real clauses from the official forms plus a handful of hand-authored RED
    # examples (the blank templates themselves have none).
    assert 20 <= len(rows) <= 35
    assert {r["proposed_label"] for r in rows} <= set(LABELS)
    assert all(len(r["text"]) > 30 for r in rows)
    assert "RED" in {r["reviewed_label"] or r["proposed_label"] for r in rows}
    assert all((r["reviewed_label"] or r["proposed_label"]) in LABELS for r in rows)
