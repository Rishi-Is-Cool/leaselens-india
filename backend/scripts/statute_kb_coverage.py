"""Phase 3 statute-coverage measurement (Person C, integrated 2026-09-29).

Runs retrieve_statute() against a manually-written representative sample of 10
Maharashtra clauses and 10 Delhi clauses, honestly caveated as a small illustrative
sample rather than the real Phase 1 pipeline's actual clause output.

    python scripts/statute_kb_coverage.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.statute_kb.retrieval import load_index, load_kb, retrieve_statute  # noqa: E402

OUT_PATH = Path(__file__).resolve().parents[2] / "data" / "statute_kb" / "coverage_results.json"

kb = load_kb()
index = load_index()

MAHARASHTRA_CLAUSES = [
    {"clause_id": "MH-C01", "jurisdiction": "Maharashtra", "topic": "security_deposit",
     "text": "The tenant shall pay a security deposit equal to ten months' rent at the commencement of this agreement, which is non-refundable under any circumstances."},
    {"clause_id": "MH-C02", "jurisdiction": "Maharashtra", "topic": "security_deposit",
     "text": "The security deposit shall be adjusted against the last two months of rent and any unpaid utility bills at the end of the tenancy."},
    {"clause_id": "MH-C03", "jurisdiction": "Maharashtra", "topic": "notice",
     "text": "Either party may terminate this leave and license agreement by giving 15 days' written notice to the other party."},
    {"clause_id": "MH-C04", "jurisdiction": "Maharashtra", "topic": "notice",
     "text": "The landlord may terminate this agreement immediately without any notice period if the licensee is found to be in default."},
    {"clause_id": "MH-C05", "jurisdiction": "Maharashtra", "topic": "eviction",
     "text": "The landlord may re-enter and take possession of the premises immediately upon any breach by the tenant, without recourse to any court or authority."},
    {"clause_id": "MH-C06", "jurisdiction": "Maharashtra", "topic": "eviction",
     "text": "This agreement is a licence for residence and shall automatically terminate on expiry of the licence period stated above, at which point the licensee must vacate."},
    {"clause_id": "MH-C07", "jurisdiction": "Maharashtra", "topic": "maintenance",
     "text": "The tenant shall be solely responsible for all repairs to the premises, including structural repairs, throughout the tenancy, and the landlord shall bear no repair obligations whatsoever."},
    {"clause_id": "MH-C08", "jurisdiction": "Maharashtra", "topic": "maintenance",
     "text": "The landlord shall carry out structural repairs, and any such repair costing above a certain threshold may result in a permitted rent increase."},
    {"clause_id": "MH-C09", "jurisdiction": "Maharashtra", "topic": "registration",
     "text": "This leave and license agreement shall be registered as required under applicable law, and the licensee shall bear the registration cost."},
    {"clause_id": "MH-C10", "jurisdiction": "Maharashtra", "topic": "rent_escalation",
     "text": "The licence fee shall increase by four percent annually, compounded, at the landlord's discretion."},
]

DELHI_CLAUSES = [
    {"clause_id": "DL-C01", "jurisdiction": "Delhi", "topic": "security_deposit",
     "text": "The tenant shall deposit an amount equal to twelve months' rent as an interest-free, refundable security deposit."},
    {"clause_id": "DL-C02", "jurisdiction": "Delhi", "topic": "security_deposit",
     "text": "The landlord may claim a premium of Rs. 5,00,000 in addition to rent as a condition for granting this tenancy."},
    {"clause_id": "DL-C03", "jurisdiction": "Delhi", "topic": "notice",
     "text": "This tenancy may be terminated by either party giving one month's written notice."},
    {"clause_id": "DL-C04", "jurisdiction": "Delhi", "topic": "notice",
     "text": "The landlord reserves the right to terminate this tenancy at will without notice, for any reason."},
    {"clause_id": "DL-C05", "jurisdiction": "Delhi", "topic": "eviction",
     "text": "The landlord may recover possession of the premises if the tenant fails to pay rent within two months of a written demand for arrears."},
    {"clause_id": "DL-C06", "jurisdiction": "Delhi", "topic": "eviction",
     "text": "The landlord may recover possession at any time without any grounds or Controller's order, simply upon giving notice to the tenant."},
    {"clause_id": "DL-C07", "jurisdiction": "Delhi", "topic": "maintenance",
     "text": "The landlord shall keep the premises in good and tenantable repair at all times, and the tenant may deduct repair costs from rent if the landlord fails to act after notice."},
    {"clause_id": "DL-C08", "jurisdiction": "Delhi", "topic": "maintenance",
     "text": "The tenant shall be responsible for all repairs to the premises, including major structural repairs, without exception."},
    {"clause_id": "DL-C09", "jurisdiction": "Delhi", "topic": "rent_escalation",
     "text": "Rent shall be increased by 15% every eleven months at the sole discretion of the landlord, without any statutory basis cited."},
    {"clause_id": "DL-C10", "jurisdiction": "Delhi", "topic": "registration",
     "text": "This rent agreement shall not be registered with any authority, and the parties waive any right to registration."},
]


def run_coverage(clauses: list[dict], include_central: bool) -> list[dict]:
    rows = []
    for c in clauses:
        results = retrieve_statute(c["jurisdiction"], c["topic"], c["text"], kb, index, include_central=include_central)
        rows.append({
            "clause_id": c["clause_id"],
            "topic": c["topic"],
            "text": c["text"],
            "matched": len(results) > 0,
            "retrieved_ids": [r["entry_id"] for r in results],
            "retrieved_jurisdictions": sorted({r["jurisdiction"] for r in results}),
        })
    return rows


def main() -> None:
    for label, include_central in [("include_central=False (default)", False), ("include_central=True", True)]:
        print(f"\n=== {label} ===")
        for jur_name, clauses in [("Maharashtra", MAHARASHTRA_CLAUSES), ("Delhi", DELHI_CLAUSES)]:
            rows = run_coverage(clauses, include_central)
            matched = sum(1 for r in rows if r["matched"])
            print(f"\n{jur_name}: {matched}/{len(rows)} matched = {100 * matched / len(rows):.1f}%")
            for r in rows:
                status = "MATCH" if r["matched"] else "NO MATCH"
                print(f"  {r['clause_id']:8s} [{r['topic']:16s}] {status:9s} -> {r['retrieved_ids']}")
            other = "Delhi" if jur_name == "Maharashtra" else "Maharashtra"
            leaks = [r for r in rows if other in r["retrieved_jurisdictions"]]
            print(f"  !!! LEAKAGE: {[r['clause_id'] for r in leaks]}" if leaks else f"  Jurisdiction isolation OK: no {jur_name} clause returned a {other} entry")

    output = {
        label_key: {"Maharashtra": run_coverage(MAHARASHTRA_CLAUSES, ic), "Delhi": run_coverage(DELHI_CLAUSES, ic)}
        for label_key, ic in [("no_central", False), ("with_central", True)]
    }
    OUT_PATH.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"\nFull results written to {OUT_PATH}")


if __name__ == "__main__":
    main()
