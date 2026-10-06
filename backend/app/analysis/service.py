"""Live risk, statute and explanation review of an uploaded document.

Runs the Phase 2-4 pipeline as a background job and stores the outcome on an `Analysis`
row the UI polls. It degrades rather than fails without an LLM provider: risk levels then
come from the offline trained classifier, statutes are still matched (retrieval needs no
LLM), and only the plain-language explanations and cross-clause links are skipped.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import asdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.explain.jurisdiction import infer_jurisdiction_for_document
from app.explain.pipeline import explain_document
from app.llm_client import is_configured as llm_configured
from app.models import Analysis, Clause, Document
from app.statute_kb.retrieval import VALID_JURISDICTIONS

logger = logging.getLogger(__name__)

SUPPORTED_JURISDICTIONS = sorted(VALID_JURISDICTIONS)

# A job that stopped reporting progress this long ago died with its server.
STALE_AFTER = timedelta(minutes=15)

STATUTE_FIELDS = ("entry_id", "citation", "excerpt_text", "source_url", "last_verified_date", "jurisdiction")


class AnalysisAlreadyRunning(RuntimeError):
    pass


def jurisdiction_hint(document: Document) -> dict:
    hint = infer_jurisdiction_for_document(document.clauses)
    return {
        "jurisdiction": hint.jurisdiction,
        "evidence": hint.evidence,
        "unsupported_state": hint.unsupported_hint,
        "ambiguous": hint.ambiguous,
    }


def _public_error(raw: str | None) -> str | None:
    """Provider errors carry rate-limit text and the account's organisation id, so the
    browser only ever gets a category, never the raw message."""
    if not raw:
        return None
    lowered = raw.lower()
    if lowered.startswith("classification failed"):
        return "The risk level could not be determined for this clause."
    if any(marker in lowered for marker in ("daily limit", "rate limit", "quota", "429")):
        return "The AI provider's daily limit was reached, so no explanation was generated."
    return "An explanation could not be generated for this clause."


def _serialise(result, headings: dict[str, str | None]) -> dict:
    clauses = []
    for clause in result.clauses:
        explanation = asdict(clause.explanation) if clause.explanation else None
        if explanation:
            explanation.pop("raw_reply", None)
        clauses.append(
            {
                "clause_id": clause.clause_id,
                "section_heading": headings.get(clause.clause_id),
                "text": clause.text,
                "risk_label": clause.risk_label,
                "risk_confidence": clause.risk_confidence,
                "topic": clause.topic,
                "retrieved_statutes": [
                    {key: statute.get(key) for key in STATUTE_FIELDS} for statute in clause.retrieved_statutes
                ],
                "explanation": explanation,
                "error": _public_error(clause.error),
            }
        )
    return {
        "clauses": clauses,
        "cross_clause": [
            {
                key: value
                for key, value in asdict(connection).items()
                if key in ("clause_id_a", "clause_id_b", "relationship_type", "explanation")
            }
            for connection in result.cross_clause
        ],
    }


def is_stale(analysis: Analysis) -> bool:
    if analysis.status != "running" or analysis.updated_at is None:
        return False
    return datetime.now(timezone.utc) - analysis.updated_at > STALE_AFTER


def start(session: Session, document: Document, jurisdiction: str | None) -> Analysis:
    if jurisdiction is not None and jurisdiction not in VALID_JURISDICTIONS:
        raise ValueError(f"Unsupported jurisdiction {jurisdiction!r}.")

    analysis = session.get(Analysis, document.id)
    if analysis is not None and analysis.status == "running" and not is_stale(analysis):
        raise AnalysisAlreadyRunning("An analysis of this document is already running.")
    if analysis is None:
        analysis = Analysis(document_id=document.id)
        session.add(analysis)

    analysis.status = "running"
    analysis.jurisdiction = jurisdiction
    analysis.explanations_available = llm_configured()
    analysis.progress_done = 0
    analysis.progress_total = len(document.clauses)
    analysis.result = None
    analysis.error = None
    session.commit()
    session.refresh(analysis)
    return analysis


def run(document_id: uuid.UUID) -> None:
    """Background job body. Uses its own session: the request's has closed by now."""
    if SessionLocal is None:
        return
    session = SessionLocal()
    try:
        analysis = session.get(Analysis, document_id)
        if analysis is None:
            return
        clauses = list(
            session.scalars(
                select(Clause).where(Clause.document_id == document_id).order_by(Clause.order_index)
            )
        )
        explain = analysis.explanations_available

        def report(done: int, total: int) -> None:
            analysis.progress_done, analysis.progress_total = done, total
            session.commit()

        result = explain_document(
            clauses,
            analysis.jurisdiction,
            # Without a provider the LLM approach would fail and fall back on every clause
            # anyway; asking for the trained model directly skips that per-clause churn.
            classify_approach=None if explain else "trained",
            explain=explain,
            run_cross_clause=explain,
            on_progress=report,
        )
        analysis.result = _serialise(result, {c.clause_id: c.section_heading for c in clauses})
        analysis.status = "done"
        analysis.progress_done = analysis.progress_total = len(clauses)
        session.commit()
    except Exception:  # noqa: BLE001 - record the failure rather than leave the row "running"
        logger.exception("analysis of document %s failed", document_id)
        session.rollback()
        analysis = session.get(Analysis, document_id)
        if analysis is not None:
            analysis.status = "failed"
            analysis.error = "The analysis stopped unexpectedly. Try running it again."
            session.commit()
    finally:
        session.close()


def describe(document: Document, analysis: Analysis | None) -> dict:
    """The single shape the UI reads, whether or not an analysis has started."""
    base = {
        "document_id": str(document.id),
        "filename": document.filename,
        "supported_jurisdictions": SUPPORTED_JURISDICTIONS,
        "jurisdiction_hint": jurisdiction_hint(document),
        "llm_configured": llm_configured(),
    }
    if analysis is None:
        return {**base, "status": "not_started", "jurisdiction": None, "explanations_available": False,
                "progress": {"done": 0, "total": len(document.clauses)}, "result": None, "error": None}

    status, error = analysis.status, analysis.error
    if is_stale(analysis):
        status, error = "failed", "The analysis was interrupted, probably by a server restart. Run it again."
    return {
        **base,
        "status": status,
        "jurisdiction": analysis.jurisdiction,
        "explanations_available": analysis.explanations_available,
        "progress": {"done": analysis.progress_done, "total": analysis.progress_total},
        "result": analysis.result if status == "done" else None,
        "error": error,
    }
