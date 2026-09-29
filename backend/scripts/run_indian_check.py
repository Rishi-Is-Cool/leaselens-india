"""Run just the Indian-domain check and splice it into data/classifier_eval.md.

Re-running the full `run_phase2.py` would redo the entire 323-clause US benchmark and
burn through that model's daily quota again just to refresh 27 rows. This script instead
loads the already-shipped trained classifier and, optionally, a different LLM_MODEL (its
own separate free-tier quota) so the small Indian check can finish without touching the
US results.

    LLM_MODEL=openai/gpt-oss-120b python scripts/run_indian_check.py
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.classifier import trained  # noqa: E402
from app.classifier.dataset import load_dataset  # noqa: E402
from app.classifier.embeddings import embed  # noqa: E402
from app.classifier.split import make_split  # noqa: E402
from scripts.run_phase2 import EVAL_PATH, indian_domain_section, pick_shots  # noqa: E402

import app.classifier.llm as llm  # noqa: E402


@dataclass
class _UsResult:
    """Just enough of a Report for indian_domain_section's 'US test accuracy' column."""

    name: str
    accuracy: float


def _parse_us_results(report_text: str) -> list[_UsResult]:
    """Read the already-written '## Results' table so re-running this script never
    needs to recompute or hardcode the US benchmark numbers it compares against."""
    match = re.search(r"## Results\n\n\|.*?\|\n\|[-| ]+\|\n(.*?)\n\n", report_text, re.DOTALL)
    if not match:
        return []
    results = []
    for line in match.group(1).splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and cells[2].endswith("%"):
            results.append(_UsResult(name=cells[0], accuracy=float(cells[2].rstrip("%")) / 100))
    return results


def main() -> None:
    clauses = load_dataset()
    split = make_split(clauses, embed([c.text for c in clauses]))
    # The TRAIN-ONLY model, not the shipped artifact (fit on train+test combined) -
    # otherwise "US test accuracy" and "Indian sample accuracy" would silently be two
    # different models, making the comparison meaningless.
    labels = [c.label for c in split.clauses]
    y_train = [labels[i] for i in split.train]
    clf = trained.fit(split.vectors[split.train], y_train, [split.block_of[i] for i in split.train])
    shots = pick_shots(split)

    text = EVAL_PATH.read_text(encoding="utf-8")
    us_reports = _parse_us_results(text)
    print(f"Using LLM_MODEL={llm.settings()['model']} for the Indian-domain check.")
    india = indian_domain_section(clf, shots, llm.is_configured(), us_reports=us_reports)

    marker = "## Indian-domain check"
    head = text[: text.index(marker)] if marker in text else text.rstrip() + "\n\n"
    EVAL_PATH.write_text(head + "\n".join(india), encoding="utf-8")
    print(f"Updated {EVAL_PATH}")


if __name__ == "__main__":
    main()
