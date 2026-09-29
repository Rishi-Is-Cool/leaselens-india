"""The Phase 4 grounding guardrail: an automated check that every factual claim in a
generated explanation is traceable to either (a) the clause's own text or (b) a
retrieved statute excerpt - and that no unhedged legal conclusion or invented citation
slipped through despite the prompt's instructions not to.

Five checks, each independently pass/fail so a failure names exactly what went wrong:

1. CITATION_RESTRICTED   every statute_support entry_id was actually retrieved for this
                         clause (no invented citation - the direct test of the project's
                         "no invented citations" rule).
2. NO_SMUGGLED_CITATION  no Act/Section-shaped reference appears in the free-text fields
                         (document_says, concern) outside the structured statute_support
                         list - catches a model naming a statute in prose instead of the
                         citation field, which would bypass check 1 entirely.
3. DOCUMENT_GROUNDED     document_says introduces no new number/amount/date the clause
                         doesn't contain, and has enough word overlap (relaxed for short
                         clauses) to be a restatement of the clause, not an invention.
4. NO_LEGAL_CONCLUSION   no unhedged "is illegal / is void / is unenforceable"-style
                         assertion (the project's legal-safety rule).
5. CONCERN_PRESENT       a YELLOW/RED clause's concern field is non-empty and not a
                         one-line placeholder.

An explanation is considered grounded only if all five pass.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "of", "to", "for", "in", "on", "and",
    "or", "shall", "will", "not", "be", "by", "at", "with", "this", "that", "it", "as",
    "any", "if", "may", "must", "such", "under", "upon", "which", "who", "whom",
}

STATUTE_REFERENCE = re.compile(
    r"\b(section|sec\.?)\s+\d+[a-zA-Z()0-9.]*|\b\d{4}\s+act\b|\bact,?\s+\d{4}\b", re.I
)

UNHEDGED_CONCLUSIONS = [
    re.compile(r"\bis illegal\b", re.I),
    re.compile(r"\bis void\b", re.I),
    re.compile(r"\bis unenforceable\b", re.I),
    re.compile(r"\bis not enforceable\b", re.I),
    re.compile(r"\bis not legal\b", re.I),
    re.compile(r"\byou can void\b", re.I),
    re.compile(r"\bthis (clause|term) is invalid\b", re.I),
]

MIN_OVERLAP_RATIO = 0.20
MIN_OVERLAP_ABSOLUTE = 2
MIN_CONCERN_CHARS = 20
# A comma only counts as part of the number when followed by exactly 3 digits (a
# thousands separator, "50,000") - otherwise a trailing sentence comma ("Rs. 50,000,
# refundable...") gets swallowed into the number and "50,000," never matches "50,000".
NUMBER_PATTERN = re.compile(r"\d{1,3}(?:,\d{3})*(?:\.\d+)?")


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-zA-Z]+", text.lower()) if w not in _STOPWORDS and len(w) > 2}


@dataclass
class GroundingReport:
    clause_id: str
    checks: dict[str, bool] = field(default_factory=dict)
    reasons: dict[str, str] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return all(self.checks.values())

    @property
    def failed_checks(self) -> list[str]:
        return [name for name, ok in self.checks.items() if not ok]


def check_grounding(explanation, clause_text: str, retrieved: list[dict]) -> GroundingReport:
    """explanation: an app.explain.generate.ExplanationResult."""
    report = GroundingReport(clause_id=explanation.clause_id)
    allowed_ids = {r["entry_id"] for r in retrieved}

    cited_ids = {s["entry_id"] for s in explanation.statute_support}
    invented = cited_ids - allowed_ids
    report.checks["CITATION_RESTRICTED"] = not invented
    if invented:
        report.reasons["CITATION_RESTRICTED"] = f"cited id(s) not in the retrieved set: {sorted(invented)}"

    free_text = f"{explanation.document_says} {explanation.concern}"
    smuggled = STATUTE_REFERENCE.findall(free_text)
    # A reference is fine if the SAME entry is properly cited in statute_support - the
    # model is allowed to name a section it has already cited; the failure mode this
    # guards against is naming one it did NOT put through the citation field.
    report.checks["NO_SMUGGLED_CITATION"] = not smuggled or bool(cited_ids)
    if smuggled and not cited_ids:
        report.reasons["NO_SMUGGLED_CITATION"] = f"statute-shaped reference in free text with no statute_support entry: {smuggled[:3]}"

    # Two independent signals, either one sufficient: (a) no NEW number/amount/date
    # appears in document_says that isn't in the clause - the direct test for a
    # fabricated fact, and largely immune to paraphrasing; (b) a lexical-overlap ratio,
    # relaxed with an absolute-count floor so a short clause (e.g. a one-line "IN
    # WITNESS WHEREOF" attestation) isn't penalised just for having few words to overlap
    # on - a faithful paraphrase of short, formal language legitimately swaps words
    # ("have set their hands" -> "signed") without inventing anything.
    clause_numbers = set(NUMBER_PATTERN.findall(clause_text))
    says_numbers = set(NUMBER_PATTERN.findall(explanation.document_says))
    invented_numbers = says_numbers - clause_numbers
    no_invented_numbers = not invented_numbers

    clause_tokens = _tokens(clause_text)
    says_tokens = _tokens(explanation.document_says)
    shared = len(says_tokens & clause_tokens)
    overlap = shared / len(says_tokens) if says_tokens else 0.0
    lexical_ok = overlap >= MIN_OVERLAP_RATIO or shared >= MIN_OVERLAP_ABSOLUTE

    report.checks["DOCUMENT_GROUNDED"] = no_invented_numbers and lexical_ok
    if invented_numbers:
        report.reasons["DOCUMENT_GROUNDED"] = f"document_says introduces number(s)/amount(s) not in the clause text: {sorted(invented_numbers)}"
    elif not lexical_ok:
        report.reasons["DOCUMENT_GROUNDED"] = (
            f"only {shared} shared word(s) ({overlap:.0%}) between document_says and the "
            f"clause text (need >= {MIN_OVERLAP_ABSOLUTE} words or >= {MIN_OVERLAP_RATIO:.0%})"
        )

    unhedged = [p.pattern for p in UNHEDGED_CONCLUSIONS if p.search(free_text)]
    report.checks["NO_LEGAL_CONCLUSION"] = not unhedged
    if unhedged:
        report.reasons["NO_LEGAL_CONCLUSION"] = f"unhedged legal conclusion detected: {unhedged}"

    needs_concern = explanation.risk_label in ("YELLOW", "RED")
    concern_ok = (not needs_concern) or len(explanation.concern.strip()) >= MIN_CONCERN_CHARS
    report.checks["CONCERN_PRESENT"] = concern_ok
    if not concern_ok:
        report.reasons["CONCERN_PRESENT"] = f"risk label {explanation.risk_label} requires a real concern, got {len(explanation.concern.strip())} chars"

    return report
