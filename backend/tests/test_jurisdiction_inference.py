"""Offline tests for the best-effort jurisdiction inference helper. Deliberately does
NOT test against the Phase 1 fixtures' synthetic "State: X | City: Y" debug line - real
leases never contain that, so a test built around it would validate the wrong thing."""

from dataclasses import dataclass

from app.explain.jurisdiction import infer_jurisdiction, infer_jurisdiction_for_document


@dataclass
class FakeClause:
    text: str


def test_infers_maharashtra_from_a_real_looking_execution_line():
    text = "This Leave and License Agreement is made and executed at Mumbai on this 3rd day of March, 2026."
    hint = infer_jurisdiction(text)
    assert hint.jurisdiction == "Maharashtra"
    assert not hint.confirmed
    assert "mumbai" in hint.evidence


def test_infers_delhi_from_an_address():
    text = "The Landlord resides at 14, Green Park, New Delhi - 110016."
    hint = infer_jurisdiction(text)
    assert hint.jurisdiction == "Delhi"


def test_ambiguous_when_both_signals_present():
    text = "Previously residing at Mumbai, the Landlord has since relocated to New Delhi."
    hint = infer_jurisdiction(text)
    assert hint.jurisdiction is None
    assert hint.ambiguous


def test_names_an_unsupported_jurisdiction_rather_than_silently_returning_nothing():
    text = "This Rental Agreement is executed at Bengaluru, Karnataka."
    hint = infer_jurisdiction(text)
    assert hint.jurisdiction is None
    assert hint.unsupported_hint == "Karnataka"


def test_no_signal_returns_none_with_no_unsupported_hint():
    text = "The parties agree to the terms and conditions set out below."
    hint = infer_jurisdiction(text)
    assert hint.jurisdiction is None
    assert hint.unsupported_hint is None
    assert hint.evidence == []


def test_never_confirmed_by_this_function_alone():
    """Confirmation is a separate, not-yet-built step (Phase 5/6); this function must
    never claim to have gotten user confirmation."""
    hint = infer_jurisdiction("Executed at Mumbai.")
    assert hint.confirmed is False


def test_document_level_uses_first_clause_with_a_signal():
    clauses = [
        FakeClause("The parties agree as follows."),
        FakeClause("This Agreement is made and executed at Mumbai."),
        FakeClause("The Tenant shall pay rent monthly."),
    ]
    hint = infer_jurisdiction_for_document(clauses)
    assert hint.jurisdiction == "Maharashtra"


def test_document_level_no_signal_anywhere_returns_none():
    clauses = [FakeClause("The parties agree."), FakeClause("Rent is payable monthly.")]
    hint = infer_jurisdiction_for_document(clauses)
    assert hint.jurisdiction is None
    assert hint.unsupported_hint is None
