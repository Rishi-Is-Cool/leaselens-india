"""Demo-safe replay of a saved Phase 4 run: displays everything from a saved raw-results
JSON file - makes ZERO network calls, so it cannot fail live in front of an audience
regardless of quota state. Confirms the saved output is genuinely replayable, per the
owner's demo-safety question.

Defaults to data/phase4_demo_safe_sample.json - a known-clean, single-document (13
clauses, 0 errors, 2 cross-clause connections) dataset kept specifically for this purpose,
since data/phase4_raw_results.json gets overwritten by every run and is not guaranteed
clean at any given moment (see PROGRESS.md "Phase 4 - demo safety").

    python scripts/demo_replay_phase4.py                     # list documents in the demo-safe sample
    python scripts/demo_replay_phase4.py 01_maharashtra_leave_license_mumbai.pdf
    python scripts/demo_replay_phase4.py --file phase4_raw_results.json           # a different saved file
    python scripts/demo_replay_phase4.py --file phase4_raw_results.json 02_delhi_rent_agreement.pdf
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DEFAULT_RAW_PATH = DATA_DIR / "phase4_demo_safe_sample.json"


def main() -> None:
    args = sys.argv[1:]
    raw_path = DEFAULT_RAW_PATH
    if args and args[0] == "--file":
        raw_path = DATA_DIR / args[1]
        args = args[2:]

    payload = json.loads(raw_path.read_text(encoding="utf-8"))

    if not args:
        print(f"No network calls made - this only reads {raw_path.name}.\n")
        print("Available documents:")
        for name, doc in payload.items():
            n = len(doc["clauses"])
            errors = sum(1 for c in doc["clauses"] if c["error"])
            print(f"  {name}  ({n} clauses, jurisdiction={doc['jurisdiction']}, {errors} error(s), "
                  f"{len(doc['cross_clause'])} cross-clause connection(s))")
        print("\nRun again with a document name to display it in full.")
        return

    name = args[0]
    if name not in payload:
        raise SystemExit(f"'{name}' not found. Run with no arguments to list available documents.")
    doc = payload[name]

    print(f"=== {name} ===  jurisdiction: {doc['jurisdiction'] or '(unsupported / no signal)'}\n")
    for c in doc["clauses"]:
        print(f"[{c['clause_id']}] risk: {c['risk_label']} (confidence {c['risk_confidence']:.2f})")
        print(f"  Clause: {c['text'][:200]}{'...' if len(c['text']) > 200 else ''}")
        if c["error"]:
            print(f"  ERROR: {c['error']}")
        elif c["explanation"]:
            e = c["explanation"]
            print(f"  Document says: {e['document_says']}")
            if e["concern"]:
                print(f"  Concern: {e['concern']}")
            if e["statute_support"]:
                for s in e["statute_support"]:
                    print(f"  Statute: {s['entry_id']} - {s['how_it_applies']}")
        print()

    if doc["cross_clause"]:
        print(f"--- Cross-clause connections ({len(doc['cross_clause'])}) ---\n")
        for cc in doc["cross_clause"]:
            print(f"{cc['clause_id_a']} <-> {cc['clause_id_b']}  ({cc['relationship_type']})")
            print(f"  {cc['explanation']}\n")


if __name__ == "__main__":
    main()
