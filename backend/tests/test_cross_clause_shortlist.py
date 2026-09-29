"""Offline test for the embedding-based shortlist step (no LLM calls - only the local
MiniLM embedding model, same as Phase 2 uses)."""

from dataclasses import dataclass

from app.explain.cross_clause import shortlist_candidate_pairs


@dataclass
class FakeClause:
    clause_id: str
    text: str


def test_shortlist_pairs_two_similar_clauses_and_skips_self_pairs():
    clauses = [
        FakeClause("a", "The Tenant shall pay a security deposit of Rs. 50,000 to the Landlord."),
        FakeClause("b", "The security deposit of Rs. 50,000 shall be refunded within fifteen days of vacating."),
        FakeClause("c", "The parties agree that Indian courts alone shall have jurisdiction over disputes."),
    ]
    pairs = shortlist_candidate_pairs(clauses, top_k=2, min_similarity=0.1)
    assert all(i != j for i, j, _ in pairs)
    assert all(i < j for i, j, _ in pairs)
    ids = {(clauses[i].clause_id, clauses[j].clause_id) for i, j, _ in pairs}
    assert ("a", "b") in ids


def test_shortlist_empty_for_fewer_than_two_clauses():
    assert shortlist_candidate_pairs([]) == []
    assert shortlist_candidate_pairs([FakeClause("a", "text")]) == []
