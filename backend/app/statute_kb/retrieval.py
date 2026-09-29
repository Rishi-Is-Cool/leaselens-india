"""Phase 3 statute knowledge base: jurisdiction-safe, topic-scoped retrieval.

Written by Person C (Phase 3), integrated 2026-09-29. Fixed before integration: 7
"Central" jurisdiction entries used a DL_ (Delhi) ID prefix, renamed to CENTRAL_
throughout the KB, index, and audit_sources/ (see data/statute_kb/audit_sources/ and
PROGRESS.md "Phase 3" for the full fix writeup, including one additional citation
accuracy issue found and corrected during that fix).

This is a DETERMINISTIC keyword/topic retrieval implementation, not a production
semantic-search or embedding-based system. Its purpose is to prove out:

  - jurisdiction isolation (a Maharashtra query never returns a Delhi entry, and
    vice versa)
  - topic filtering
  - an explicit, documented policy for when Central-law entries may be surfaced
  - citation traceability (a displayed citation must come from an entry that was
    actually retrieved for the specific query, not merely exist somewhere in the
    master KB)
  - excerpt traceability (displayed statutory text must exactly match the
    retrieved entry's excerpt_text, word for word)
  - source URL traceability

A production system can later replace the keyword-overlap scoring in
`_relevance_score` with a real embedding-similarity model without changing the
jurisdiction-isolation or traceability logic, which are the parts this step
exists to validate. Phase 4's grounding guardrail (app/explain/grounding.py) uses
the three validate_*_traceability functions directly.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

KB_DIR = Path(__file__).resolve().parents[3] / "data" / "statute_kb"
DEFAULT_KB_PATH = KB_DIR / "leaselens_statute_kb.json"
DEFAULT_INDEX_PATH = KB_DIR / "leaselens_statute_index.json"

VALID_JURISDICTIONS = {"Maharashtra", "Delhi"}
CENTRAL_JURISDICTION = "Central"

_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "of", "to", "for", "in", "on",
    "and", "or", "there", "any", "does", "do", "what", "who", "how", "i", "my",
    "this", "that", "it", "be", "can", "may", "has", "have", "with", "at",
}


def _tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-zA-Z]+", text.lower()) if t not in _STOPWORDS]


def load_kb(kb_path: Path = DEFAULT_KB_PATH) -> dict:
    with open(kb_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_index(index_path: Path = DEFAULT_INDEX_PATH) -> dict:
    with open(index_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _entries_by_id(kb: dict) -> dict[str, dict]:
    return {e["id"]: e for e in kb["entries"]}


def _relevance_score(query: str, entry: dict) -> int:
    """Deterministic keyword-overlap score. NOT a semantic embedding similarity —
    this is intentionally simple so retrieval behavior is fully inspectable and
    reproducible without external models or network access. Counts how many
    non-stopword query tokens appear anywhere in the entry's citation, excerpt_text,
    notes, applicability, or example clauses."""
    query_tokens = set(_tokenize(query))
    haystack_parts = [
        entry.get("citation", ""),
        entry.get("excerpt_text", ""),
        entry.get("notes", ""),
        entry.get("applicability", ""),
        " ".join(entry.get("applies_to_clause_examples", []) or []),
    ]
    haystack_tokens = set(_tokenize(" ".join(haystack_parts)))
    return len(query_tokens & haystack_tokens)


class CentralLawPolicyError(ValueError):
    pass


def central_law_policy(jurisdiction: str) -> dict:
    """Explicit, documented Central-law policy.

    For BOTH pilot jurisdictions (Maharashtra and Delhi):
      - The jurisdiction's own state-specific entries are always eligible.
      - Central entries are eligible ONLY when the caller explicitly opts in
        (include_central=True on retrieve_statute) AND the Central entry's
        topic_tags match the requested topic per the master index. Central
        entries are never included by default/automatically.
      - The other pilot jurisdiction's entries are NEVER eligible, under any
        circumstance, regardless of the include_central flag.

    Central applicability is established purely from KB metadata that already
    exists (the index's own Central/<topic> bucket membership) — if a Central
    entry is not listed under the requested topic in the index, it is excluded
    rather than guessed at.
    """
    if jurisdiction not in VALID_JURISDICTIONS:
        raise CentralLawPolicyError(
            f"Unsupported jurisdiction '{jurisdiction}'. Must be one of {VALID_JURISDICTIONS}."
        )
    return {
        "own_jurisdiction_entries": "always eligible",
        "other_pilot_jurisdiction_entries": "never eligible, under any circumstance",
        "central_entries": "eligible only if include_central=True AND entry is listed "
                            "under this exact topic in the index's Central bucket",
    }


def retrieve_statute(
    jurisdiction: str, topic: str, query: str, kb: dict, index: dict, include_central: bool = False
) -> list[dict]:
    """Reference retrieval pipeline:

        jurisdiction  -->  jurisdiction filter (via index)
                       -->  topic filter (via index)
                       -->  keyword-overlap relevance scoring within that
                            already-filtered candidate set
                       -->  ranked results

    Jurisdiction and topic filtering happen BEFORE any relevance scoring — the
    candidate set is built from the index first, and scoring only ever ranks
    within that pre-filtered set. It never runs a global search and then removes
    wrong-jurisdiction results afterward.

    Returns a list of dicts, each with: entry_id, citation, excerpt_text,
    source_url, jurisdiction, topic_tags, relevance_score, last_verified_date,
    ordered by relevance_score descending, ties broken by entry_id for
    determinism. last_verified_date is copied directly from the matched KB
    entry's own last_verified_date field — never hard-coded or derived any
    other way.

    Raises CentralLawPolicyError for an unsupported jurisdiction.
    """
    if jurisdiction not in VALID_JURISDICTIONS:
        raise CentralLawPolicyError(
            f"Unsupported jurisdiction '{jurisdiction}'. Must be one of {VALID_JURISDICTIONS}."
        )

    by_id = _entries_by_id(kb)

    candidate_ids = list(index.get(jurisdiction, {}).get(topic, []))
    if include_central:
        candidate_ids.extend(index.get(CENTRAL_JURISDICTION, {}).get(topic, []))

    # Defensive: guarantee no entry from the OTHER pilot jurisdiction can ever
    # enter the candidate set, even if the index were malformed.
    other_jurisdiction = "Delhi" if jurisdiction == "Maharashtra" else "Maharashtra"
    safe_candidate_ids = [
        cid for cid in candidate_ids
        if cid in by_id and by_id[cid]["jurisdiction"] != other_jurisdiction
    ]

    scored = []
    for cid in safe_candidate_ids:
        entry = by_id[cid]
        scored.append((_relevance_score(query, entry), cid, entry))
    scored.sort(key=lambda t: (-t[0], t[1]))

    return [
        {
            "entry_id": entry["id"],
            "citation": entry["citation"],
            "excerpt_text": entry["excerpt_text"],
            "source_url": entry["source_url"],
            "jurisdiction": entry["jurisdiction"],
            "topic_tags": entry["topic_tags"],
            "relevance_score": score,
            "last_verified_date": entry["last_verified_date"],
        }
        for score, cid, entry in scored
    ]


def validate_citation_traceability(retrieved_entries: list[dict], displayed_citation: str) -> bool:
    """True iff displayed_citation exactly matches the 'citation' field of at least
    one entry in retrieved_entries (the entries actually returned for THIS query) —
    not merely somewhere in the whole master KB."""
    return any(e["citation"] == displayed_citation for e in retrieved_entries)


def validate_excerpt_traceability(retrieved_entry: dict, displayed_excerpt: str) -> bool:
    """True iff displayed_excerpt is an exact, unmodified match of
    retrieved_entry['excerpt_text']. Any change — including a single word — fails."""
    return displayed_excerpt == retrieved_entry["excerpt_text"]


def validate_source_url_traceability(retrieved_entry: dict, displayed_source_url: str) -> bool:
    """True iff displayed_source_url is an exact match of retrieved_entry['source_url']."""
    return displayed_source_url == retrieved_entry["source_url"]
