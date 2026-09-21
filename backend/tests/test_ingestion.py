from pathlib import Path

import pytest

from app.ingestion.extract import extract_pdf
from app.ingestion.segment import segment

TEST_LEASES = Path(__file__).resolve().parents[2] / "data" / "test-leases"

# Operative clause counts per source document. The title block (instrument title plus the
# fixture generator's "State: ... | City: ..." line) is not lease content and is excluded
# by the segmenter, so these are exact.
EXPECTED_CLAUSES = {
    "01_maharashtra_leave_license_mumbai.pdf": 13,
    "02_delhi_rent_agreement.pdf": 12,
    "03_karnataka_rental_agreement_bangalore.pdf": 12,
    "04_tamil_nadu_lease_agreement_chennai.pdf": 7,
    "05_uttar_pradesh_lease_deed_lucknow.pdf": 12,
    "06_west_bengal_tenancy_agreement_kolkata.pdf": 10,
    "07_punjab_rent_deed_chandigarh.pdf": 8,
    "08_rajasthan_leave_license_jaipur.pdf": 10,
    "09_gujarat_rent_agreement.pdf": 8,
}

ACCURACY_TARGET = 90.0


def clauses_for(name: str):
    document = extract_pdf((TEST_LEASES / name).read_bytes())
    return document, segment(document.paragraphs)


@pytest.mark.parametrize("name", sorted(EXPECTED_CLAUSES))
def test_clause_count_matches_source_document(name):
    _, clauses = clauses_for(name)
    assert len(clauses) == EXPECTED_CLAUSES[name]


@pytest.mark.parametrize("name", sorted(EXPECTED_CLAUSES))
def test_no_clause_is_split_mid_sentence(name):
    """The handoff's hard rule: a clause must never begin or end mid-sentence."""
    _, clauses = clauses_for(name)
    for clause in clauses:
        assert not clause.text[0].islower(), f"{name} {clause.clause_id} starts mid-sentence"
        # A clause ending in a list item is complete; bullets carry no full stop.
        if "•" in clause.text:
            continue
        assert clause.text.rstrip().endswith(
            (".", ";", ":", "!", "?")
        ), f"{name} {clause.clause_id} ends mid-sentence"


def test_corpus_accuracy_meets_target():
    expected = sum(EXPECTED_CLAUSES.values())
    matched = 0
    for name, count in EXPECTED_CLAUSES.items():
        _, clauses = clauses_for(name)
        produced = len(clauses)
        matched += max(0, count - abs(produced - count))
    assert matched / expected * 100 >= ACCURACY_TARGET


def test_clause_objects_match_the_published_contract():
    """Phase 2 and Phase 4 build against this shape; it must not drift silently."""
    _, clauses = clauses_for("02_delhi_rent_agreement.pdf")
    assert set(clauses[0].as_dict()) == {"clause_id", "section_heading", "text", "order"}
    assert [c.order for c in clauses] == list(range(len(clauses)))
    assert len({c.clause_id for c in clauses}) == len(clauses)


def test_unnumbered_prose_document_is_split_by_paragraph():
    """Tamil Nadu has no numbering or headings; it must not come back as one clause."""
    _, clauses = clauses_for("04_tamil_nadu_lease_agreement_chennai.pdf")
    assert len(clauses) > 5


def test_run_in_headings_are_recognised():
    """Delhi labels clauses as "Rent:" / "Security Deposit:" with no numbering."""
    _, clauses = clauses_for("02_delhi_rent_agreement.pdf")
    headings = {c.section_heading for c in clauses}
    assert {"Rent", "Security Deposit", "Notice Period"} <= headings


def test_article_sections_scope_their_sub_clauses():
    """UP nests 2.1/2.2/2.3 beneath "ARTICLE 2 - TERM AND RENT"."""
    _, clauses = clauses_for("05_uttar_pradesh_lease_deed_lucknow.pdf")
    term_and_rent = [c for c in clauses if c.section_heading == "TERM AND RENT"]
    assert len(term_and_rent) == 3


def test_all_pages_extract_without_ocr():
    """The corpus is born-digital; a text page must never be routed to OCR."""
    for name in EXPECTED_CLAUSES:
        document, _ = clauses_for(name)
        assert document.method == "text"
        assert document.ocr_page_numbers == []


def test_signature_lines_are_not_emitted_as_clauses():
    for name in EXPECTED_CLAUSES:
        _, clauses = clauses_for(name)
        for clause in clauses:
            assert "____" not in clause.text


def test_all_caps_run_in_heading_is_extracted():
    """Bug: "USE OF PREMISES The Tenant shall..." left the heading inside text."""
    _, clauses = clauses_for("09_gujarat_rent_agreement.pdf")
    use = next(c for c in clauses if c.section_heading == "USE OF PREMISES")
    assert use.text.startswith("The Tenant shall use the premises")


def test_spelled_out_clause_numbering_is_recognised():
    """Bug: "Clause 3. Maintenance." was unmatched; only bare "3." was handled."""
    _, clauses = clauses_for("09_gujarat_rent_agreement.pdf")
    headings = {c.section_heading for c in clauses}
    assert {"Premises", "Term and Rent", "Maintenance", "Inspection and Jurisdiction"} <= headings
    for clause in clauses:
        assert not clause.text.startswith("Clause ")


def test_title_block_is_not_emitted_as_a_clause():
    """Bug: the "State: ... | City: ..." masthead line became a clause object."""
    for name in EXPECTED_CLAUSES:
        _, clauses = clauses_for(name)
        for clause in clauses:
            assert not clause.text.startswith("State:")
            assert clause.section_heading != "State"


def test_title_block_split_keeps_the_agreement_body():
    from app.ingestion.segment import split_title_block

    title, body = split_title_block(
        [
            "RENT AGREEMENT",
            "State: Gujarat | City: Ahmedabad",
            "This Rent Agreement is made at Ahmedabad on this 5th day of June, 2026.",
            "Clause 1. Premises. The Owner lets out Flat No. 502.",
        ]
    )
    assert title == ["RENT AGREEMENT", "State: Gujarat | City: Ahmedabad"]
    assert len(body) == 2
    assert body[0].startswith("This Rent Agreement")


def test_sentence_opening_is_not_mistaken_for_a_heading():
    """"2. The Tenant shall pay ... Rs. 28,000" ends a full stop after "Rs"."""
    _, clauses = clauses_for("03_karnataka_rental_agreement_bangalore.pdf")
    rent = next(c for c in clauses if "28,000" in c.text)
    assert rent.section_heading == "TERMS AND CONDITIONS"
    assert rent.text.startswith("2. The Tenant shall pay")


@pytest.mark.parametrize("name", sorted(EXPECTED_CLAUSES))
def test_signature_lines_are_preserved_not_discarded(name):
    """Signing lines are not clauses, but they must not vanish from the output."""
    from app.ingestion.segment import segment_document

    document = extract_pdf((TEST_LEASES / name).read_bytes())
    parsed = segment_document(document.paragraphs)
    assert parsed.signature_block, f"{name} lost its signature block"
    assert any("_" in line for line in parsed.signature_block)


# Superseded by test_no_source_text_is_silently_dropped, which measures coverage
# across every corpus and accounts for section headings.


def test_numbered_caps_headings_are_extracted():
    """Bug: "1. PREMISES AND TERM The Landlord..." has no full stop closing the heading."""
    _, clauses = clauses_for("07_punjab_rent_deed_chandigarh.pdf")
    headings = {c.section_heading for c in clauses}
    assert {
        "PREMISES AND TERM",
        "RENT AND DEPOSIT",
        "SCHEDULE OF FIXTURES INCLUDED",
        "GENERAL CONDITIONS",
        "TERMINATION",
        "JURISDICTION",
    } <= headings


def test_bullet_list_stays_one_clause():
    """Bug: four fixture bullets became four clauses, detached from their heading."""
    _, clauses = clauses_for("07_punjab_rent_deed_chandigarh.pdf")
    fixtures = [c for c in clauses if c.section_heading == "SCHEDULE OF FIXTURES INCLUDED"]
    assert len(fixtures) == 1
    assert fixtures[0].text.count("\u2022") == 4
    assert "air-conditioner" in fixtures[0].text and "wardrobe" in fixtures[0].text


def test_cid_font_artifacts_are_normalised():
    """pdfminer emits "(cid:127)" for a glyph it cannot map; PyMuPDF resolves it."""
    for name in EXPECTED_CLAUSES:
        document, clauses = clauses_for(name)
        assert "(cid:" not in document.full_text, f"{name} leaks a cid artifact"
        for clause in clauses:
            assert "(cid:" not in clause.text


def test_roman_numeral_clauses_segment():
    """West Bengal numbers its clauses I, II, III rather than 1, 2, 3."""
    _, clauses = clauses_for("06_west_bengal_tenancy_agreement_kolkata.pdf")
    assert len(clauses) == 10
    assert any(c.text.startswith("I. The tenancy") for c in clauses)


# --- content completeness ------------------------------------------------------------
# Clause-count accuracy cannot see text that is dropped rather than mis-split, which is
# how the filled-form content loss went unnoticed. These measure coverage directly.

ALL_CORPORA = (
    sorted((Path(__file__).resolve().parents[2] / "data" / "test-leases").glob("*.pdf"))
    + sorted((Path(__file__).resolve().parents[2] / "official_format").glob("*.pdf"))
    + sorted((Path(__file__).resolve().parents[2] / "test").glob("*.pdf"))
)
MIN_COVERAGE = 95.0


@pytest.mark.parametrize("path", ALL_CORPORA, ids=lambda p: p.name)
def test_no_source_text_is_silently_dropped(path):
    from app.ingestion.coverage import measure
    from app.ingestion.segment import segment_document

    document = extract_pdf(path.read_bytes(), allow_ocr=False)
    parsed = segment_document(document.paragraphs)
    coverage = measure(document.paragraphs, parsed)
    assert not coverage.unexplained, f"{path.name} dropped {coverage.unexplained}"
    assert coverage.percent >= MIN_COVERAGE, f"{path.name} coverage {coverage.percent:.1f}%"


def test_filled_form_keeps_every_reported_element():
    """The four pieces reported missing from the filled Tamil Nadu deed."""
    from app.ingestion.segment import segment_document

    path = Path(__file__).resolve().parents[2] / "test" / "tamil_nadu_FILLED_lease_deed.pdf"
    document = extract_pdf(path.read_bytes())
    parsed = segment_document(document.paragraphs)
    everything = " ".join(
        parsed.title_block
        + parsed.section_headings
        + [f"{c.section_heading or ''} {c.text}" for c in parsed.clauses]
        + parsed.signature_block
    )
    assert "THIS AGREEMENT OF LEASE is entered into" in everything
    assert "WHEREAS" in everything
    assert "DEMISED PREMISES" in everything
    assert any("LESSOR:" in s for s in parsed.signature_block)
    assert any("LESSEE:" in s for s in parsed.signature_block)


def test_deed_connectors_are_detected_consistently():
    """BETWEEN and AND play the same structural role and must be treated alike."""
    from app.ingestion.segment import segment_document

    path = Path(__file__).resolve().parents[2] / "test" / "tamil_nadu_FILLED_lease_deed.pdf"
    parsed = segment_document(extract_pdf(path.read_bytes()).paragraphs)
    headings = [c.section_heading for c in parsed.clauses]
    assert "BETWEEN" in headings and "AND" in headings


def test_section_heading_does_not_carry_into_the_closing_clause():
    """The attestation must not inherit the schedule heading above it."""
    from app.ingestion.segment import segment_document

    path = Path(__file__).resolve().parents[2] / "test" / "tamil_nadu_FILLED_lease_deed.pdf"
    parsed = segment_document(extract_pdf(path.read_bytes()).paragraphs)
    closing = next(c for c in parsed.clauses if c.text.startswith("IN WITNESSES WHEREOF"))
    assert closing.section_heading is None


def test_witness_slots_stay_distinct():
    from app.ingestion.segment import segment_document

    path = Path(__file__).resolve().parents[2] / "test" / "tamil_nadu_FILLED_lease_deed.pdf"
    parsed = segment_document(extract_pdf(path.read_bytes()).paragraphs)
    numbered = [s for s in parsed.signature_block if s[0].isdigit()]
    assert len(numbered) == 2
