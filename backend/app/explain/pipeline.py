"""Phase 4 end-to-end pipeline: clauses in, grounded explanations + cross-clause
connections out.

Jurisdiction is a caller-supplied input, not inferred here. Phase 3's own task list
mentions jurisdiction selection/inference, but neither Person C's delivered retrieval
code nor Phase 1's ingestion carries a jurisdiction field - there is nothing in this
codebase yet that infers it from a document. Building that UI/inference flow is Phase
5/6/7 territory (document-aware chat, frontend); Phase 4's stated inputs are "the clause
text, its risk label, any matched statute excerpts from Phase 3", which presumes
jurisdiction-based retrieval already happened upstream of this phase. So: pass
jurisdiction in, or pass None to skip statute retrieval entirely (every explanation
still generates, just with no statute_support - itself the correct, honest behavior for
a jurisdiction Phase 3 doesn't cover).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.classifier.api import classify_clause
from app.explain.cross_clause import CrossClauseResult, confirm_connection, shortlist_candidate_pairs
from app.explain.generate import ExplanationResult, generate_explanation
from app.explain.grounding import GroundingReport, check_grounding
from app.explain.topics import tag_topic
from app.llm_client import LLMClient
from app.statute_kb.retrieval import VALID_JURISDICTIONS, load_index, load_kb, retrieve_statute

_kb = None
_index = None


def _kb_and_index():
    global _kb, _index
    if _kb is None:
        _kb = load_kb()
        _index = load_index()
    return _kb, _index


@dataclass
class ClauseExplanation:
    clause_id: str
    text: str
    risk_label: str
    risk_confidence: float
    topic: str | None
    retrieved_statutes: list[dict]
    explanation: ExplanationResult | None
    grounding: GroundingReport | None
    error: str | None = None


@dataclass
class DocumentExplanations:
    jurisdiction: str | None
    clauses: list[ClauseExplanation] = field(default_factory=list)
    cross_clause: list[CrossClauseResult] = field(default_factory=list)


def _retrieve_for_clause(text: str, section_heading: str | None, jurisdiction: str | None) -> tuple[str | None, list[dict]]:
    topic = tag_topic(text, section_heading)
    if not jurisdiction or jurisdiction not in VALID_JURISDICTIONS or topic is None:
        return topic, []
    kb, index = _kb_and_index()
    return topic, retrieve_statute(jurisdiction, topic, text, kb, index, include_central=True)


def explain_document(
    clauses: list,
    jurisdiction: str | None,
    *,
    classify_approach: str | None = None,
    explain_client: LLMClient | None = None,
    cross_clause_client: LLMClient | None = None,
    run_cross_clause: bool = True,
) -> DocumentExplanations:
    """clauses: objects with `.clause_id`, `.text`, and optionally `.section_heading`
    (matching app.ingestion.segment.Clause)."""
    result = DocumentExplanations(jurisdiction=jurisdiction)

    for clause in clauses:
        heading = getattr(clause, "section_heading", None)
        topic, retrieved = _retrieve_for_clause(clause.text, heading, jurisdiction)
        try:
            classification = classify_clause(clause.text, approach=classify_approach)
        except Exception as exc:  # noqa: BLE001 - a classification failure shouldn't kill the whole document
            result.clauses.append(ClauseExplanation(
                clause_id=clause.clause_id, text=clause.text, risk_label="", risk_confidence=0.0,
                topic=topic, retrieved_statutes=retrieved, explanation=None, grounding=None,
                error=f"classification failed: {exc}",
            ))
            continue

        try:
            explanation = generate_explanation(
                clause.clause_id, clause.text, classification.label, retrieved, client=explain_client
            )
            grounding = check_grounding(explanation, clause.text, retrieved)
            error = None
        except Exception as exc:  # noqa: BLE001 - one clause's failure must not stop the batch
            explanation, grounding, error = None, None, f"explanation generation failed: {exc}"

        result.clauses.append(ClauseExplanation(
            clause_id=clause.clause_id,
            text=clause.text,
            risk_label=classification.label,
            risk_confidence=classification.confidence,
            topic=topic,
            retrieved_statutes=retrieved,
            explanation=explanation,
            grounding=grounding,
            error=error,
        ))

    if run_cross_clause and len(clauses) >= 2:
        by_index = list(clauses)
        for i, j, _sim in shortlist_candidate_pairs(by_index):
            try:
                connection = confirm_connection(
                    by_index[i].clause_id, by_index[i].text,
                    by_index[j].clause_id, by_index[j].text,
                    client=cross_clause_client,
                )
                if connection.related:
                    result.cross_clause.append(connection)
            except Exception:  # noqa: BLE001 - a failed pair check must not stop the batch
                continue

    return result
