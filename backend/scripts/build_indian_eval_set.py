"""Build data/indian_eval_set.csv: real clauses from the official Indian lease forms.

Clause text is taken from Person A's segmenter, not retyped. The labels are PROPOSALS
written by Claude for the project owner to review - they are not ground truth until the
`reviewed_label` column is filled in (the evaluation uses reviewed_label when present).

    python scripts/build_indian_eval_set.py

WARNING: this OVERWRITES data/indian_eval_set.csv from scratch, including any
`reviewed_label` / `reviewed_reason` the owner has already filled in, and any hand-added
rows (e.g. synthetic RED examples - the blank official templates this script draws from
contain none). It refuses to run if the existing file has any reviewed row or extra
rows beyond SELECTION, unless --force is passed.
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ingestion.extract import extract_pdf  # noqa: E402
from app.ingestion.segment import segment_document  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "indian_eval_set.csv"

# (form, clause_number, proposed label, why). Chosen from the agreement text of each form;
# blank-only or heading-only fragments and the Maharashtra data-entry table are excluded.
SELECTION = [
    ("tamil_nadu_official_lease_deed", "2", "GREEN", "rent payable monthly on a fixed day", "rent of Rs"),
    ("tamil_nadu_official_lease_deed", "4", "GREEN", "term with renewal by mutual consent"),
    ("tamil_nadu_official_lease_deed", "5", "YELLOW", "rent escalation, conditional on no breach"),
    ("tamil_nadu_official_lease_deed", "6", "YELLOW", "tenant carries upkeep; landlord inspection right"),
    ("tamil_nadu_official_lease_deed", "7", "GREEN", "permitted use; no sublet without consent"),
    ("tamil_nadu_official_lease_deed", "8", "GREEN", "tenant pays metered electricity"),
    ("tamil_nadu_official_lease_deed", "9", "GREEN", "no structural change without consent; appliances allowed"),
    ("tamil_nadu_official_lease_deed", "10", "GREEN", "hand back possession; notice to vacate early"),
    ("tamil_nadu_official_lease_deed", "11", "YELLOW", "lease revocable for breach after notice"),
    ("west_bengal_official_deed_of_lease", "5", "YELLOW", "interest-free deposit refunded only on vacating"),
    ("west_bengal_official_deed_of_lease", "6", "GREEN", "rent monthly in advance"),
    ("west_bengal_official_deed_of_lease", "7", "GREEN", "tenant pays electricity and municipal taxes"),
    ("west_bengal_official_deed_of_lease", "8", "GREEN", "restore fittings, fair wear and tear excepted"),
    ("west_bengal_official_deed_of_lease", "9", "YELLOW", "no sublet or parting with possession under any circumstances"),
    ("west_bengal_official_deed_of_lease", "11", "YELLOW", "no alteration under any circumstances"),
    ("west_bengal_official_deed_of_lease", "12", "GREEN", "minor repairs tenant, major repairs landlord"),
    ("west_bengal_official_deed_of_lease", "13", "GREEN", "landlord entry for inspection at reasonable time"),
    ("west_bengal_official_deed_of_lease", "14", "GREEN", "mutual notice to vacate"),
    ("west_bengal_official_deed_of_lease", "16", "YELLOW", "per-day damages for overstaying"),
    ("maharashtra_official_leave_license", "1", "YELLOW", "revocable licence, expressly no tenancy rights"),
    ("maharashtra_official_leave_license", "2.1", "GREEN", "licence fee payable in first five days"),
    ("maharashtra_official_leave_license", "2.2", "YELLOW", "interest-free refundable deposit"),
    ("maharashtra_official_leave_license", "4.2", "YELLOW", "licensee bears maintenance charges"),
    ("maharashtra_official_leave_license", "6", "GREEN", "no alteration without written consent"),
    ("maharashtra_official_leave_license", "7", "YELLOW", "no tenancy right, no transfer, sublet or mortgage"),
    ("maharashtra_official_leave_license", "8", "GREEN", "licensor access on reasonable notice"),
    ("maharashtra_official_leave_license", "12", "GREEN", "registration and stamp duty borne by licensor"),
]

BLANK = re.compile(r"(?:_{2,}|\.{4,}|…+|-{3,}\s*\(\d+[A-Z]?\)\s*-*|-{3,})")


def clean(text: str) -> str:
    """Collapse fill-in blanks to a single marker so length and wording stay natural."""
    text = re.sub(r"^\s*(?:\d+(?:\.\d+)*[.)])\s*", "", text)
    text = BLANK.sub("[blank]", text)
    text = re.sub(r"(\[blank\]\s*)+", "[blank] ", text)
    return re.sub(r"\s+", " ", text).strip()


def _refuse_if_reviewed_work_would_be_lost(force: bool) -> None:
    if force or not OUT.exists():
        return
    existing = list(csv.DictReader(OUT.open(encoding="utf-8")))
    reviewed = [r for r in existing if r.get("reviewed_label", "").strip()]
    extra = len(existing) - len(SELECTION)
    if reviewed or extra > 0:
        raise SystemExit(
            f"{OUT} already has {len(reviewed)} reviewed row(s) and {max(extra, 0)} row(s) "
            "beyond this script's own SELECTION (e.g. hand-added RED examples). Re-running "
            "would overwrite that work. Pass --force to proceed anyway."
        )


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="overwrite even if reviewed work exists")
    args = parser.parse_args()
    _refuse_if_reviewed_work_would_be_lost(args.force)

    parsed = {}
    for name in {form for form, *_ in SELECTION}:
        pdf = ROOT / "official_format" / f"{name}.pdf"
        parsed[name] = segment_document(extract_pdf(pdf.read_bytes(), allow_ocr=False).paragraphs).clauses

    rows = []
    for form, number, label, why, *hint in SELECTION:
        matches = [
            c for c in parsed[form]
            if c.clause_number == number
            and re.match(rf"^{re.escape(number)}[.)]?\s*\S", c.text)
            and (not hint or hint[0] in c.text)
        ]
        if not matches:
            raise SystemExit(f"clause {number} not found in {form}")
        rows.append(
            {
                "id": f"IN-{len(rows) + 1:02d}",
                "source": form,
                "clause_number": number,
                "text": clean(matches[0].text),
                "proposed_label": label,
                "proposed_reason": why,
                "reviewed_label": "",
            }
        )

    with OUT.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} clauses to {OUT}")


if __name__ == "__main__":
    main()
