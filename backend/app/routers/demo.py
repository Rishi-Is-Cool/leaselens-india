"""Read-only Phase 4 demo results for the frontend showcase.

The saved sample is deliberately replayable: serving it never calls an LLM or any
external service, so a presentation cannot fail due to quotas or network access.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.analysis.service import public_error

router = APIRouter(prefix="/analysis", tags=["analysis"])

RAW_PATH = Path(__file__).resolve().parents[3] / "data" / "phase4_raw_results.json"
SAMPLE_PATH = Path(__file__).resolve().parents[3] / "data" / "phase4_demo_safe_sample.json"


def _load(path: Path) -> dict[str, dict]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _sample() -> dict[str, dict]:
    """Best saved record per document.

    The full-corpus run was cut short by a daily token cap, so most of its clauses carry
    an error instead of an explanation. The verified-clean sample is therefore laid over
    it per document, rather than the whole file being preferred or ignored: a document in
    both takes the clean record, and the rest keep whatever the full run did produce.
    """
    return {**_load(RAW_PATH), **_load(SAMPLE_PATH)}


def _explained(document: dict) -> int:
    return sum(1 for clause in document.get("clauses", []) if clause.get("explanation"))


@router.get("/documents")
def list_analysed_documents() -> list[dict]:
    return [
        {
            "filename": filename,
            "jurisdiction": document.get("jurisdiction"),
            "clause_count": len(document.get("clauses", [])),
            "explained_count": _explained(document),
            "connection_count": len(document.get("cross_clause", [])),
        }
        for filename, document in _sample().items()
    ]


@router.get("/documents/{filename}")
def get_analysis_document(filename: str) -> dict:
    document = _sample().get(filename)
    if document is None:
        raise HTTPException(status_code=404, detail="No saved analysis was found for this filename.")
    # Saved runs hold raw provider errors (rate-limit text, account ids); serve a category.
    clauses = [{**clause, "error": public_error(clause.get("error"))} for clause in document.get("clauses", [])]
    return {"filename": filename, **document, "clauses": clauses}
