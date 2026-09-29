"""Phase 4 DoD verification: run the explanation + cross-clause pipeline on the Phase 1
test document set, measure the grounding-check pass rate, and collect cross-clause
connections for manual review.

Jurisdiction is obtained from app.explain.jurisdiction's best-effort inference (scanning
each document's own clause text - never the title block, which carries a synthetic
"State: X | City: Y" debug line these test fixtures happen to include but no real lease
would) - not read from a hardcoded per-file answer key. KNOWN_JURISDICTION below is used
only to score that inference's accuracy on this corpus, never to decide what the pipeline
actually runs on. Only Maharashtra and Delhi are covered by the Phase 3 KB; documents
outside those two correctly retrieve no statutes and are a live test of "say so
explicitly" rather than fabricate.

**This inference is a hint, not a selection mechanism.** Nothing in this codebase lets a
user confirm or correct it - that UI/API step is Phase 5/6 territory. See PROGRESS.md
"Phase 4 - jurisdiction" for exactly what does and doesn't exist here.

    python scripts/run_phase4.py                  # full corpus
    python scripts/run_phase4.py --limit 2         # first 2 documents only (smoke test)
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.explain.grounding import check_grounding  # noqa: E402
from app.explain.jurisdiction import infer_jurisdiction_for_document  # noqa: E402
from app.explain.pipeline import explain_document  # noqa: E402
from app.ingestion.extract import extract_pdf  # noqa: E402
from app.ingestion.segment import segment_document  # noqa: E402

TEST_LEASES = Path(__file__).resolve().parents[2] / "data" / "test-leases"
OUT_PATH = Path(__file__).resolve().parents[2] / "data" / "phase4_report.md"
RAW_PATH = Path(__file__).resolve().parents[2] / "data" / "phase4_raw_results.json"

# Ground truth for SCORING the inference only - never fed to the pipeline itself. Only
# Maharashtra and Delhi are in the Phase 3 KB; the rest are included specifically to
# exercise the "no coverage, say so, don't fabricate" path across most of the corpus.
KNOWN_JURISDICTION = {
    "01_maharashtra_leave_license_mumbai.pdf": "Maharashtra",
    "02_delhi_rent_agreement.pdf": "Delhi",
    "03_karnataka_rental_agreement_bangalore.pdf": None,
    "04_tamil_nadu_lease_agreement_chennai.pdf": None,
    "05_uttar_pradesh_lease_deed_lucknow.pdf": None,
    "06_west_bengal_tenancy_agreement_kolkata.pdf": None,
    "07_punjab_rent_deed_chandigarh.pdf": None,
    "08_rajasthan_leave_license_jaipur.pdf": None,
    "09_gujarat_rent_agreement.pdf": None,
}


def _dump_raw(all_results: dict) -> None:
    """Persist clause text + risk label + retrieved statutes + generated explanation for
    every clause, so the grounding check (or any other analysis) can be re-run later
    without spending fresh LLM calls - exactly what's needed if the guardrail's own
    logic changes, as it did during this run (see PROGRESS.md).

    Backs up any existing RAW_PATH/OUT_PATH first - a demo-safety incident on 2026-09-30
    saw a good, complete 92/92 dataset overwritten by a run that then hit a quota wall,
    losing the only clean cached copy. Never again silently."""
    for path in (RAW_PATH, OUT_PATH):
        if path.exists():
            backup = path.with_suffix(f".backup-{__import__('datetime').datetime.now():%Y%m%dT%H%M%S}{path.suffix}")
            path.rename(backup)
            print(f"Backed up existing {path.name} -> {backup.name}", flush=True)

    payload = {}
    for name, r in all_results.items():
        payload[name] = {
            "jurisdiction": r.jurisdiction,
            "clauses": [
                {
                    "clause_id": c.clause_id,
                    "text": c.text,
                    "risk_label": c.risk_label,
                    "risk_confidence": c.risk_confidence,
                    "topic": c.topic,
                    "retrieved_statutes": c.retrieved_statutes,
                    "explanation": asdict(c.explanation) if c.explanation else None,
                    "error": c.error,
                }
                for c in r.clauses
            ],
            "cross_clause": [asdict(cc) for cc in r.cross_clause],
        }
    RAW_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _recheck_from_raw() -> None:
    """Reload phase4_raw_results.json and re-run ONLY the grounding check (no LLM calls)
    - for when app.explain.grounding's logic changes and the report needs refreshing
    without re-spending quota. Regenerates the markdown report; does not touch cross-clause
    results, which don't depend on the grounding guardrail."""
    from app.explain.generate import ExplanationResult

    payload = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    all_results = {}
    inference_scorecard = []
    for name, doc in payload.items():
        clauses = []
        for c in doc["clauses"]:
            explanation = ExplanationResult(**c["explanation"]) if c["explanation"] else None
            grounding = check_grounding(explanation, c["text"], c["retrieved_statutes"]) if explanation else None
            clauses.append(_RawClauseExplanation(
                clause_id=c["clause_id"], text=c["text"], risk_label=c["risk_label"],
                risk_confidence=c["risk_confidence"], topic=c["topic"],
                retrieved_statutes=c["retrieved_statutes"], explanation=explanation,
                grounding=grounding, error=c["error"],
            ))
        cross_clause = [_RawCrossClause(**cc) for cc in doc["cross_clause"]]
        all_results[name] = _RawDocumentExplanations(jurisdiction=doc["jurisdiction"], clauses=clauses, cross_clause=cross_clause)
        if name in KNOWN_JURISDICTION:
            # doc["jurisdiction"] is exactly what infer_jurisdiction_for_document produced
            # during the original run (main() passes its .jurisdiction straight into
            # explain_document) - re-read it rather than recompute, since the recheck
            # path's job is to redo grounding, not re-derive an already-known inference.
            known = KNOWN_JURISDICTION[name]
            inference_scorecard.append({
                "document": name, "known": known, "inferred": doc["jurisdiction"],
                "correct": doc["jurisdiction"] == known,
            })
    write_report(all_results, inference_scorecard)
    print(f"Re-checked grounding from {RAW_PATH} (no LLM calls). Wrote {OUT_PATH}")


from dataclasses import dataclass, field  # noqa: E402


@dataclass
class _RawClauseExplanation:
    clause_id: str
    text: str
    risk_label: str
    risk_confidence: float
    topic: str | None
    retrieved_statutes: list
    explanation: object
    grounding: object
    error: str | None = None


@dataclass
class _RawCrossClause:
    clause_id_a: str
    clause_id_b: str
    related: bool
    relationship_type: str = ""
    explanation: str = ""


@dataclass
class _RawDocumentExplanations:
    jurisdiction: str | None
    clauses: list = field(default_factory=list)
    cross_clause: list = field(default_factory=list)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="only process the first N documents")
    parser.add_argument("--recheck-only", action="store_true", help="re-run grounding from saved raw results, no LLM calls")
    args = parser.parse_args()

    if args.recheck_only:
        _recheck_from_raw()
        return

    documents = sorted(KNOWN_JURISDICTION)[: args.limit] if args.limit else sorted(KNOWN_JURISDICTION)

    all_results = {}
    inference_scorecard = []
    for name in documents:
        path = TEST_LEASES / name
        extracted = extract_pdf(path.read_bytes(), allow_ocr=False)
        parsed = segment_document(extracted.paragraphs)

        hint = infer_jurisdiction_for_document(parsed.clauses)
        known = KNOWN_JURISDICTION[name]
        correct = hint.jurisdiction == known
        inference_scorecard.append({
            "document": name, "known": known, "inferred": hint.jurisdiction,
            "unsupported_hint": hint.unsupported_hint, "ambiguous": hint.ambiguous,
            "evidence": hint.evidence, "correct": correct,
        })
        print(
            f"{name}: {len(parsed.clauses)} clauses | jurisdiction inferred={hint.jurisdiction} "
            f"(known={known}, {'OK' if correct else 'MISMATCH'}, evidence={hint.evidence})",
            flush=True,
        )
        result = explain_document(parsed.clauses, hint.jurisdiction)
        all_results[name] = result
        n_ok = sum(1 for c in result.clauses if c.grounding and c.grounding.passed)
        n_err = sum(1 for c in result.clauses if c.error)
        print(f"  grounded: {n_ok}/{len(result.clauses)}  errors: {n_err}  cross-clause found: {len(result.cross_clause)}", flush=True)

    _dump_raw(all_results)
    write_report(all_results, inference_scorecard)
    print(f"\nWrote {OUT_PATH}\nWrote {RAW_PATH}")


def write_report(all_results: dict, inference_scorecard: list[dict] | None = None) -> None:
    total = sum(len(r.clauses) for r in all_results.values())
    errored = sum(1 for r in all_results.values() for c in r.clauses if c.error)
    checked = total - errored
    grounded = sum(1 for r in all_results.values() for c in r.clauses if c.grounding and c.grounding.passed)
    pass_rate = grounded / checked if checked else 0.0

    lines = [
        "# Phase 4 - explanation layer, cross-clause detection, grounding guardrail",
        "",
        f"Run on {len(all_results)} Phase 1 test documents ({total} clauses total). "
        f"Reproduce with `python scripts/run_phase4.py` from `backend/`.",
        "",
    ]

    if inference_scorecard:
        n_correct = sum(1 for s in inference_scorecard if s["correct"])
        lines += [
            "## Jurisdiction inference (a hint, not a selection mechanism - see PROGRESS.md)",
            "",
            f"Scanned each document's own clause text (never the title block) for city/state "
            f"signals; scored against the known state each fixture represents. "
            f"**{n_correct}/{len(inference_scorecard)} correct.**",
            "",
            "| Document | Known | Inferred | Unsupported hint | Ambiguous | Correct |",
            "|---|---|---|---|---|---|",
        ]
        for s in inference_scorecard:
            lines.append(
                f"| {s['document']} | {s['known'] or '-'} | {s['inferred'] or '-'} | "
                f"{s.get('unsupported_hint') or '-'} | {s.get('ambiguous', False)} | "
                f"{'yes' if s['correct'] else 'NO'} |"
            )
        lines += ["", "No user confirmation step exists yet for this hint - that is Phase 5/6 work.", ""]

    lines += [
        "## Grounding guardrail pass rate",
        "",
        f"**{pass_rate:.1%}** ({grounded}/{checked} clauses that reached grounding check; "
        f"{errored} clause(s) failed before reaching it - counted separately below, not folded "
        "into the pass rate, since a pipeline error is a different failure mode than an "
        "ungrounded explanation).",
        "",
        "| Document | Jurisdiction | Clauses | Grounded | Errors | Cross-clause found |",
        "|---|---|---|---|---|---|",
    ]
    for name, r in all_results.items():
        n = len(r.clauses)
        ok = sum(1 for c in r.clauses if c.grounding and c.grounding.passed)
        err = sum(1 for c in r.clauses if c.error)
        lines.append(f"| {name} | {r.jurisdiction or '(unsupported)'} | {n} | {ok}/{n - err} | {err} | {len(r.cross_clause)} |")

    lines += ["", "## Grounding failures, with reasons", ""]
    any_failure = False
    for name, r in all_results.items():
        for c in r.clauses:
            if c.grounding and not c.grounding.passed:
                any_failure = True
                lines.append(f"- **{name} / {c.clause_id}** ({c.risk_label}): {c.grounding.reasons}")
            elif c.error:
                any_failure = True
                lines.append(f"- **{name} / {c.clause_id}**: PIPELINE ERROR - {c.error}")
    if not any_failure:
        lines.append("(none)")

    lines += ["", "## Cross-clause connections found", ""]
    any_connection = False
    for name, r in all_results.items():
        for conn in r.cross_clause:
            any_connection = True
            lines += [
                f"**{name}**: `{conn.clause_id_a}` <-> `{conn.clause_id_b}` ({conn.relationship_type})",
                "",
                conn.explanation,
                "",
            ]
    if not any_connection:
        lines.append("(none found)")

    lines += ["", "## Sample explanations (for manual review)", ""]
    shown = 0
    for name, r in all_results.items():
        for c in r.clauses:
            if c.explanation is None or shown >= 12:
                continue
            shown += 1
            lines += [
                f"**{name} / {c.clause_id}** — risk: {c.risk_label} (confidence {c.risk_confidence:.2f}), "
                f"topic: {c.topic or 'none'}, retrieved: {[s['entry_id'] for s in c.retrieved_statutes] or 'none'}, "
                f"grounded: {c.grounding.passed if c.grounding else 'n/a'}",
                "",
                f"> Clause: {c.text[:300]}",
                "",
                f"- **Document says:** {c.explanation.document_says}",
                f"- **Concern:** {c.explanation.concern or '(none - GREEN)'}",
                f"- **Statute support:** {c.explanation.statute_support or 'none'}",
                "",
            ]

    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
