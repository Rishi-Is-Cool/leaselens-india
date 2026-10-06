"""Bundle the saved Phase 4 analysis into the frontend for the hosted, backend-free demo.

The public site runs from saved results rather than a live API, so it cannot sleep, run out
of LLM quota, or expose anyone's uploads. This writes exactly what the /analysis endpoint
would serve (best record per document), minus fields the UI never reads.

    python scripts/build_demo_analysis.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.routers.demo import _explained, _sample  # noqa: E402

OUTPUT = Path(__file__).resolve().parents[2] / "frontend" / "public" / "demo-analysis.json"

# Failed explanations carry the provider's error text, which includes its rate-limit
# message and the account's organisation id. None of that belongs in a public file.
UNAVAILABLE = "Explanation unavailable for this saved run."


def _clause(clause: dict) -> dict:
    explanation = clause.get("explanation")
    if explanation:
        explanation = {
            "clause_id": explanation.get("clause_id", clause["clause_id"]),
            "risk_label": explanation.get("risk_label", clause["risk_label"]),
            "document_says": explanation.get("document_says"),
            "concern": explanation.get("concern"),
            "statute_support": explanation.get("statute_support", []),
            "disclaimer": explanation.get("disclaimer"),
        }
    return {
        "clause_id": clause["clause_id"],
        "text": clause["text"],
        "risk_label": clause["risk_label"],
        "risk_confidence": clause.get("risk_confidence", 0.0),
        "topic": clause.get("topic"),
        "retrieved_statutes": [
            {
                key: statute.get(key)
                for key in ("entry_id", "citation", "excerpt_text", "source_url", "last_verified_date")
            }
            for statute in clause.get("retrieved_statutes", [])
        ],
        "explanation": explanation,
        "error": UNAVAILABLE if clause.get("error") else None,
    }


def build() -> dict:
    documents = {}
    for filename, document in sorted(_sample().items()):
        documents[filename] = {
            "jurisdiction": document.get("jurisdiction"),
            "clause_count": len(document.get("clauses", [])),
            "explained_count": _explained(document),
            "connection_count": len(document.get("cross_clause", [])),
            "clauses": [_clause(c) for c in document.get("clauses", [])],
            "cross_clause": [
                {
                    key: connection.get(key)
                    for key in ("clause_id_a", "clause_id_b", "relationship_type", "explanation")
                }
                for connection in document.get("cross_clause", [])
            ],
        }
    return documents


def main() -> int:
    documents = build()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(documents, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT} ({OUTPUT.stat().st_size / 1024:.0f} KB, {len(documents)} documents)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
