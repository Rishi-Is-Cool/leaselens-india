"""Phase 1 verification harness.

Runs extraction + segmentation over the test-lease corpus and prints the raw output
for manual checking against the source PDFs, followed by a measured segmentation
accuracy. Deliberately does not touch the database, so segmentation can be verified
independently of Postgres availability.

    python scripts/run_pipeline.py            # summary + accuracy
    python scripts/run_pipeline.py --raw      # also dump raw extracted text
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ingestion.extract import extract_pdf  # noqa: E402
from app.ingestion.segment import segment  # noqa: E402

TEST_LEASES = Path(__file__).resolve().parents[2] / "data" / "test-leases"

# Expected operative clause counts, established by reading each source PDF: the
# parties/recital paragraphs, each numbered or headed clause, and the closing
# attestation. Title lines and signature rules are not clauses.
#
# `synthetic_header` counts the "State: ... | Format: ..." line the fixture generator
# writes as line 2 of every file. It is not lease content and would not appear in a
# real document, so accuracy is reported both with and without it.
EXPECTED = {
    "01_maharashtra_leave_license_mumbai.pdf": {"clauses": 13, "synthetic_header": 1},
    "02_delhi_rent_agreement.pdf": {"clauses": 12, "synthetic_header": 1},
    "03_karnataka_rental_agreement_bangalore.pdf": {"clauses": 12, "synthetic_header": 1},
    "04_tamil_nadu_lease_agreement_chennai.pdf": {"clauses": 7, "synthetic_header": 1},
    "05_uttar_pradesh_lease_deed_lucknow.pdf": {"clauses": 12, "synthetic_header": 1},
}


def looks_mid_sentence(text: str) -> bool:
    """A clause that opens lower-case or never terminates was split mid-sentence."""
    return bool(text) and (text[0].islower() or not text.rstrip().endswith((".", ";", ":", "!", "?")))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", action="store_true", help="dump raw extracted text")
    args = parser.parse_args()

    total_expected = 0
    total_matched = 0
    fragments = 0

    for path in sorted(TEST_LEASES.glob("*.pdf")):
        document = extract_pdf(path.read_bytes())
        clauses = segment(document.paragraphs)
        expected = EXPECTED.get(path.name, {})
        expected_clauses = expected.get("clauses", 0)
        header_noise = expected.get("synthetic_header", 0)

        print("=" * 100)
        print(f"{path.name}")
        print(
            f"pages={document.page_count} method={document.method} "
            f"paragraphs={len(document.paragraphs)} clauses={len(clauses)} "
            f"expected={expected_clauses} (+{header_noise} synthetic header)"
        )
        print("=" * 100)

        if args.raw:
            print("--- RAW EXTRACTED TEXT " + "-" * 77)
            print(document.full_text)
            print("--- END RAW TEXT " + "-" * 83)

        for clause in clauses:
            # The synthetic header occupies order 0 and is excluded from clause metrics.
            is_header = clause.order < header_noise
            fragment = looks_mid_sentence(clause.text) and not is_header
            label = "  <-- SYNTHETIC HEADER" if is_header else ("  <-- FRAGMENT" if fragment else "")
            heading = clause.section_heading or "-"
            print(f"[{clause.order:2d}] {clause.clause_id} | {heading[:30]:32} | {clause.text[:70]}{label}")
            fragments += fragment
        print()

        produced_real = len(clauses) - header_noise
        # Penalise over- and under-splitting alike, rather than capping at the expected
        # count, which would hide a segmenter that shatters clauses into fragments.
        total_expected += expected_clauses
        total_matched += max(0, expected_clauses - abs(produced_real - expected_clauses))

    print("=" * 100)
    print("MEASURED SEGMENTATION ACCURACY")
    print("=" * 100)
    accuracy = (total_matched / total_expected * 100) if total_expected else 0.0
    print(f"expected clauses across corpus : {total_expected}")
    print(f"correctly segmented            : {total_matched}")
    print(f"mid-sentence fragments         : {fragments}")
    print(f"accuracy                       : {accuracy:.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
