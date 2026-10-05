"""Read-only Phase 4 demo results for the frontend showcase.

The saved sample is deliberately replayable: serving it never calls an LLM or any
external service, so a presentation cannot fail due to quotas or network access.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/analysis", tags=["analysis"])

RAW_PATH = Path(__file__).resolve().parents[3] / "data" / "phase4_raw_results.json"
SAMPLE_PATH = Path(__file__).resolve().parents[3] / "data" / "phase4_demo_safe_sample.json"


def _sample() -> dict[str, dict]:
    path = RAW_PATH if RAW_PATH.exists() else SAMPLE_PATH
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/documents")
def list_analysed_documents() -> list[dict]:
    return [
        {
            "filename": filename,
            "jurisdiction": document.get("jurisdiction"),
            "clause_count": len(document.get("clauses", [])),
            "connection_count": len(document.get("cross_clause", [])),
        }
        for filename, document in _sample().items()
    ]


@router.get("/documents/{filename}")
def get_analysis_document(filename: str) -> dict:
    document = _sample().get(filename)
    if document is None:
        raise HTTPException(status_code=404, detail="No saved analysis was found for this filename.")
    return {"filename": filename, **document}
