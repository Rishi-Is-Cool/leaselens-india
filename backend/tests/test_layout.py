"""Locating clauses on the original page, for highlighting them in the document viewer."""

import io
import shutil
from pathlib import Path

import pytest

from app.ingestion.extract import extract
from app.ingestion.layout import Word, locate_clauses
from app.ingestion.segment import segment_document

LEASES = Path(__file__).resolve().parents[2] / "data" / "test-leases"


def line(page, top, text, x=0.1):
    """Words of one line, laid out left to right."""
    words, left = [], x
    for token in text.split():
        right = left + 0.01 * len(token)
        words.append(Word(page, left, top, right, top + 0.01, token))
        left = right + 0.005
    return words


def test_each_clause_maps_to_its_own_lines_in_order():
    words = (
        line(1, 0.10, "1. The tenant shall pay rent of Rs. 20,000")
        + line(1, 0.12, "on the 5th of each month.")
        + line(1, 0.20, "2. The deposit is refundable within 30 days.")
        + line(2, 0.05, "3. Either party may end this with one month's notice.")
    )
    located = locate_clauses(words, [
        ("c001", "The tenant shall pay rent of Rs. 20,000 on the 5th of each month."),
        ("c002", "The deposit is refundable within 30 days."),
        ("c003", "Either party may end this with one month's notice."),
    ])
    assert [b[2] for b in located["c001"]] == [0.10, 0.12], "one box per line"
    assert located["c002"][0][0] == 1 and located["c003"][0][0] == 2
    assert all(0 <= v <= 1 for boxes in located.values() for b in boxes for v in b[1:])


def test_repeated_wording_is_matched_after_the_previous_clause():
    words = line(1, 0.1, "Rent is due monthly.") + line(1, 0.2, "Rent is due monthly in advance.")
    located = locate_clauses(words, [("c001", "Rent is due monthly."), ("c002", "Rent is due monthly in advance.")])
    assert located["c001"][0][2] == 0.1 and located["c002"][0][2] == 0.2


def test_ocr_noise_still_locates_and_missing_text_is_omitted_not_guessed():
    words = line(1, 0.1, "The Licensee sha11 pay the 1icence fee monthly to the Licensor.")
    located = locate_clauses(words, [
        ("c001", "The Licensee shall pay the licence fee monthly to the Licensor."),
        ("c002", "Arbitration shall be held in Mumbai under the 1996 Act."),
    ])
    assert "c001" in located
    assert "c002" not in located


@pytest.mark.parametrize("path", sorted(LEASES.glob("*.pdf")), ids=lambda p: p.stem)
def test_every_clause_of_every_sample_lease_is_located(path):
    document = extract(path.read_bytes(), "application/pdf")
    clauses = segment_document(document.paragraphs).clauses
    located = locate_clauses(document.words, [(c.clause_id, c.text) for c in clauses])
    assert set(located) == {c.clause_id for c in clauses}
    pages = {b[0] for boxes in located.values() for b in boxes}
    assert pages <= set(range(1, document.page_count + 1))


@pytest.mark.skipif(shutil.which("tesseract") is None and not Path("C:/Program Files/Tesseract-OCR/tesseract.exe").exists(),
                    reason="Tesseract not installed")
def test_a_photographed_page_is_located_from_ocr_word_boxes():
    import pdfplumber

    with pdfplumber.open(LEASES / "03_karnataka_rental_agreement_bangalore.pdf") as pdf:
        image = pdf.pages[0].to_image(resolution=200).original
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    document = extract(buffer.getvalue(), "image/png")
    clauses = segment_document(document.paragraphs).clauses
    located = locate_clauses(document.words, [(c.clause_id, c.text) for c in clauses])
    assert len(located) >= 0.9 * len(clauses)
