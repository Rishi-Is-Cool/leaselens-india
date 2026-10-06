"""Phase 4: cross-clause connection detection.

Two stages, as the handoff specifies: a cheap embedding-similarity shortlist first
(candidates only, never a claim of relatedness by itself), then an LLM pass that
actually decides whether two clauses are meaningfully connected and, if so, explains
the connection grounded in both clauses' own text - e.g. a termination-notice clause and
a separate early-termination-payment clause.

Embedding similarity alone is not the mechanism: two clauses can be topically similar
without being the kind of connection a tenant needs to know about (two unrelated GREEN
clauses about "notice" in different senses), and two clauses can be meaningfully linked
without high lexical/semantic similarity (a rent-escalation clause and a security-deposit
clause that references "current rent"). The LLM pass is what actually confirms/explains
it; the embedding shortlist only keeps the number of LLM calls proportional to document
size instead of the full O(n^2) clause-pair count.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

import numpy as np

from app.classifier.embeddings import embed
from app.llm_client import LLMClient

SHORTLIST_MIN_SIMILARITY = 0.25
SHORTLIST_TOP_K = 2

SYSTEM_PROMPT = """You look at two clauses from the SAME lease and decide whether they
are meaningfully connected in a way a tenant should know about - for example, a
termination-notice clause and a separate clause about a payment due on early
termination, or a security-deposit clause and a separate clause about what can be
deducted from it.

Being about a loosely similar topic is NOT enough - only say related=true if
understanding one clause genuinely changes how a tenant should read the other (a
hidden interaction, a condition in one that affects the other, a combined effect that
isn't obvious from either clause alone).

Never state a legal conclusion ("this combination is illegal/unenforceable") - describe
the practical interaction in hedged, plain language, quoting or closely paraphrasing
both clauses.

Reply with ONLY a JSON object, no other text:
{"related": true|false, "relationship_type": "...", "explanation": "..."}
If related is false, relationship_type and explanation may be empty strings.
"""


@dataclass
class CrossClauseResult:
    clause_id_a: str
    clause_id_b: str
    related: bool
    relationship_type: str = ""
    explanation: str = ""


def shortlist_candidate_pairs(
    clauses: list, top_k: int = SHORTLIST_TOP_K, min_similarity: float = SHORTLIST_MIN_SIMILARITY
) -> list[tuple[int, int, float]]:
    """clauses: objects with a `.text` attribute, in document order. Returns (i, j,
    similarity) with i < j, each clause contributing at most `top_k` candidate partners,
    deduplicated."""
    if len(clauses) < 2:
        return []
    # Never cached: these are an uploaded lease's clauses, and a cache file on disk would
    # outlive the upload's retention window. Recomputing for one lease takes milliseconds.
    vectors = embed([c.text for c in clauses], cache=False)
    sim = vectors @ vectors.T
    np.fill_diagonal(sim, -1)

    pairs: set[tuple[int, int]] = set()
    for i in range(len(clauses)):
        top = np.argsort(-sim[i])[:top_k]
        for j in top:
            j = int(j)
            if sim[i, j] >= min_similarity and i != j:
                pairs.add((min(i, j), max(i, j)))

    return sorted((i, j, float(sim[i, j])) for i, j in pairs)


def parse_reply(content: str) -> dict:
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        raise ValueError(f"no JSON in reply: {content[:150]!r}")
    data = json.loads(match.group(0))
    if "related" not in data:
        raise ValueError("reply missing 'related'")
    return data


def confirm_connection(
    clause_id_a: str, text_a: str, clause_id_b: str, text_b: str, *, client: LLMClient | None = None
) -> CrossClauseResult:
    client = client or LLMClient(max_tokens=900)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Clause A ({clause_id_a}): {text_a}\n\nClause B ({clause_id_b}): {text_b}"},
    ]
    content = client.chat(messages)
    try:
        data = parse_reply(content)
    except (ValueError, json.JSONDecodeError):
        content = client.chat(messages)
        data = parse_reply(content)
    return CrossClauseResult(
        clause_id_a=clause_id_a,
        clause_id_b=clause_id_b,
        related=bool(data.get("related")),
        relationship_type=str(data.get("relationship_type", "")).strip(),
        explanation=str(data.get("explanation", "")).strip(),
    )
