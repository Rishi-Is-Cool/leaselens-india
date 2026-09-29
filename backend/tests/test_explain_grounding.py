"""Offline, deterministic tests for the Phase 4 grounding guardrail. No LLM calls -
constructs ExplanationResult objects directly to test each of the 5 checks in isolation.
"""

from app.explain.generate import ExplanationResult
from app.explain.grounding import check_grounding
from app.explain.topics import tag_topic

CLAUSE = (
    "The Tenant shall pay a security deposit of Rs. 50,000 to the Landlord, which shall "
    "be interest-free and refundable within fifteen days of vacating the premises."
)
RETRIEVED = [
    {"entry_id": "MH_SEC_001", "citation": "Section 10, Maharashtra Rent Control Act, 1999",
     "excerpt_text": "A landlord shall not claim a deposit exceeding a reasonable amount..."},
]


def _good_explanation(**overrides):
    defaults = dict(
        clause_id="c001",
        risk_label="YELLOW",
        document_says="The tenant pays a security deposit of Rs. 50,000, refundable within fifteen days of vacating.",
        concern="Fifteen days is a common but not statutorily mandated turnaround; confirm what happens if it runs long.",
        statute_support=[{"entry_id": "MH_SEC_001", "how_it_applies": "Caps deposit amounts in Maharashtra."}],
    )
    defaults.update(overrides)
    return ExplanationResult(**defaults)


def test_well_formed_explanation_passes_all_checks():
    report = check_grounding(_good_explanation(), CLAUSE, RETRIEVED)
    assert report.passed, report.reasons


def test_invented_citation_fails_citation_restricted():
    bad = _good_explanation(statute_support=[{"entry_id": "MH_SEC_999", "how_it_applies": "made up"}])
    report = check_grounding(bad, CLAUSE, RETRIEVED)
    assert not report.checks["CITATION_RESTRICTED"]
    assert not report.passed


def test_smuggled_citation_in_prose_fails_when_nothing_cited():
    bad = _good_explanation(
        statute_support=[],
        concern="This is governed by Section 108 of the Transfer of Property Act, 1882.",
    )
    report = check_grounding(bad, CLAUSE, RETRIEVED)
    assert not report.checks["NO_SMUGGLED_CITATION"]


def test_ungrounded_document_says_fails():
    bad = _good_explanation(
        document_says="The landlord may enter the property at any time without notice for inspection purposes."
    )
    report = check_grounding(bad, CLAUSE, RETRIEVED)
    assert not report.checks["DOCUMENT_GROUNDED"]


def test_unhedged_legal_conclusion_fails():
    bad = _good_explanation(concern="This clause is illegal and cannot be enforced against the tenant.")
    report = check_grounding(bad, CLAUSE, RETRIEVED)
    assert not report.checks["NO_LEGAL_CONCLUSION"]


def test_yellow_clause_needs_a_real_concern():
    bad = _good_explanation(concern="Worth checking.")
    report = check_grounding(bad, CLAUSE, RETRIEVED)
    assert not report.checks["CONCERN_PRESENT"]


def test_green_clause_does_not_require_a_concern():
    green = _good_explanation(risk_label="GREEN", concern="")
    report = check_grounding(green, CLAUSE, RETRIEVED)
    assert report.checks["CONCERN_PRESENT"]


def test_empty_retrieved_set_means_no_citation_is_ever_allowed():
    ok = _good_explanation(statute_support=[])
    report = check_grounding(ok, CLAUSE, retrieved=[])
    assert report.checks["CITATION_RESTRICTED"]

    bad = _good_explanation(statute_support=[{"entry_id": "MH_SEC_001", "how_it_applies": "x"}])
    report2 = check_grounding(bad, CLAUSE, retrieved=[])
    assert not report2.checks["CITATION_RESTRICTED"]


def test_short_boilerplate_clause_with_faithful_paraphrase_passes():
    """Regression: a short, formal clause paraphrased faithfully (different words, same
    meaning, no new facts) must not fail just for having few words to overlap on."""
    clause = "IN WITNESS WHEREOF the parties hereto have set their respective hands on the day, month and year first above written."
    explanation = _good_explanation(
        risk_label="GREEN",
        document_says="This is a standard execution clause stating that the parties have signed the document on the date specified at the beginning of the agreement.",
        concern="",
        statute_support=[],
    )
    report = check_grounding(explanation, clause, retrieved=[])
    assert report.checks["DOCUMENT_GROUNDED"], report.reasons


def test_invented_amount_fails_even_with_high_word_overlap():
    """Regression: a fabricated number must fail even if most other words overlap."""
    explanation = _good_explanation(
        document_says="The tenant pays a security deposit of Rs. 99,000 to the Landlord, refundable within fifteen days of vacating the premises."
    )
    report = check_grounding(explanation, CLAUSE, RETRIEVED)
    assert not report.checks["DOCUMENT_GROUNDED"]
    assert "99,000" in report.reasons["DOCUMENT_GROUNDED"]


def test_number_with_trailing_sentence_comma_is_not_a_false_mismatch():
    """Regression: 'Rs. 50,000,' (trailing punctuation) must match clause text's
    'Rs. 50,000' - the comma-as-punctuation must not be treated as part of the number."""
    explanation = _good_explanation(
        document_says="The tenant pays a security deposit of Rs. 50,000, which is refundable within fifteen days."
    )
    report = check_grounding(explanation, CLAUSE, RETRIEVED)
    assert report.checks["DOCUMENT_GROUNDED"], report.reasons


def test_topic_tagger_maps_known_keywords():
    assert tag_topic("The Tenant shall pay a security deposit of Rs. 50,000.") == "security_deposit"
    assert tag_topic("Either party may terminate this Agreement by giving notice.") == "eviction"
    assert tag_topic("The Landlord shall carry out all structural repairs.") == "maintenance"
    assert tag_topic("Rent shall increase by 5% annually.") == "rent_escalation"
    assert tag_topic("This Agreement shall be registered under applicable law.") == "registration"
    assert tag_topic("The parties agree to the following recitals.") is None
