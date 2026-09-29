"""Phase 2 Step 3: improve the `approach="trained"` fallback with reviewed synthetic
Indian clauses (owner-approved 2026-09-29; the LLM stays the default regardless).

Two stages, per the owner's explicit decision (option b):

1. HELD-OUT CHECK. Train on the original US train split (1,199 real clauses) plus only
   the 153 TRAIN-side synthetic rows. Evaluate on three untouched sets the model never
   saw: the 323-clause US test, the 31-clause reviewed Indian eval set, and - new - the
   42 held-out synthetic rows. The synthetic-test breakdown specifically separates
   "obvious" RED (alarm-word phrasing) from "subtle" RED (same severity, no alarm words),
   because the owner flagged a real risk: every alarm-word phrase in the dataset appears
   only in RED rows, so a classifier could look accurate by pattern-matching keywords
   instead of learning the underlying reasoning. Subtle-RED recall on a truly held-out
   template is the test that would catch that.
2. FINAL FIT (only if the check looks sound - not automatic). Refit on the original US
   train split plus ALL 195 synthetic rows (not just the 153), for what actually ships as
   the `approach="trained"` artifact. Its metrics on the still-valid US test (323) and
   Indian eval (31) are reported; the 42 synthetic-test numbers are NOT re-reported for
   this model, because those rows are now part of its training data - re-testing on them
   would be circular. The held-out check above is what stands as evidence of
   generalization to synthetic material.

    python scripts/retrain_trained_fallback.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scripts.generate_synthetic_indian_clauses as gen  # noqa: E402
from app.classifier import metrics, trained  # noqa: E402
from app.classifier.dataset import LABELS, load_dataset  # noqa: E402
from app.classifier.embeddings import embed  # noqa: E402
from app.classifier.split import check_leakage, make_split  # noqa: E402

DATA = Path(__file__).resolve().parents[2] / "data"
SYNTHETIC_SPLIT_CSV = DATA / "synthetic_indian_clauses_with_split.csv"
INDIAN_EVAL_CSV = DATA / "indian_eval_set.csv"
OUT_PATH = DATA / "retrain_fallback_report.md"
SYNTHETIC_GROUP_OFFSET = 1_000_000  # keeps synthetic template ids out of the real block-id range


def red_subtlety_lookup() -> dict[str, str]:
    """Maps a filled clause text back to 'obvious' / 'subtle' / 'na', from the
    generator's own template bodies - not stored in the reviewed CSV, so this reproduces
    it rather than risk touching the already-approved file."""
    lookup: dict[str, str] = {}
    for topic, variants in gen.TOPICS.items():
        for key, (text, _reason) in variants.items():
            tag = "obvious" if "obvious" in key else ("subtle" if "red" in key else "na")
            for state in gen.STATES:
                lookup[gen._fill(text, state)] = tag
    return lookup


def load_synthetic_split() -> tuple[list[dict], list[dict]]:
    rows = list(csv.DictReader(SYNTHETIC_SPLIT_CSV.open(encoding="utf-8")))
    train = [r for r in rows if r["split"] == "train"]
    test = [r for r in rows if r["split"] == "test"]
    return train, test


def load_indian_eval() -> tuple[list[str], list[str]]:
    rows = list(csv.DictReader(INDIAN_EVAL_CSV.open(encoding="utf-8")))
    texts = [r["text"] for r in rows]
    truth = [(r["reviewed_label"].strip() or r["proposed_label"]).upper() for r in rows]
    return texts, truth


def evaluate_all(name_prefix: str, clf: trained.TrainedClassifier, sets: list[tuple[str, list[str], list[str]]]) -> list[metrics.Report]:
    reports = []
    for name, texts, truth in sets:
        probs = clf.predict_proba(embed(texts, cache=False))
        pred = [LABELS[k] for k in probs.argmax(1)]
        reports.append(metrics.evaluate(f"{name_prefix}{name}", truth, pred, probs))
    return reports


def red_subtlety_breakdown(clf: trained.TrainedClassifier, texts: list[str], truth: list[str], subtlety_of: dict[str, str]) -> str:
    probs = clf.predict_proba(embed(texts, cache=False))
    pred = [LABELS[k] for k in probs.argmax(1)]
    lines = ["| RED subtype | n | correctly predicted RED | recall |", "|---|---|---|---|"]
    for subtype in ("obvious", "subtle"):
        idx = [i for i, t in enumerate(texts) if truth[i] == "RED" and subtlety_of.get(t) == subtype]
        if not idx:
            continue
        correct = sum(1 for i in idx if pred[i] == "RED")
        lines.append(f"| {subtype} | {len(idx)} | {correct} | {correct / len(idx):.1%} |")
        for i in idx:
            if pred[i] != "RED":
                lines.append(f"|   miss: predicted {pred[i]} | {texts[i][:100]}... | | |")
    return "\n".join(lines)


def main() -> None:
    clauses = load_dataset()
    real_split = make_split(clauses, embed([c.text for c in clauses]))
    leak = check_leakage(real_split)
    if not leak.clean:
        raise SystemExit(f"Real-data leakage check FAILED: {leak}")

    real_labels = [c.label for c in real_split.clauses]
    real_train_idx, real_test_idx = real_split.train, real_split.test
    real_train_vectors = real_split.vectors[real_train_idx]
    real_train_labels = [real_labels[i] for i in real_train_idx]
    real_train_groups = [real_split.block_of[i] for i in real_train_idx]

    us_test_texts = [real_split.clauses[i].text for i in real_test_idx]
    us_test_truth = [real_labels[i] for i in real_test_idx]

    indian_texts, indian_truth = load_indian_eval()
    subtlety_of = red_subtlety_lookup()
    synth_train, synth_test = load_synthetic_split()

    # Sanity: every synthetic row (train and test) must resolve to a known subtlety tag
    # (or "na" for non-RED), otherwise the breakdown below would silently under-count.
    unresolved = [r["clause_text"][:60] for r in synth_train + synth_test if r["clause_text"] not in subtlety_of]
    if unresolved:
        raise SystemExit(f"{len(unresolved)} synthetic clauses did not match the generator's own templates: {unresolved[:3]}")

    # ---------- Stage 1: held-out check (153 synthetic train rows only) ----------
    synth_train_texts = [r["clause_text"] for r in synth_train]
    synth_train_labels = [r["proposed_label"] for r in synth_train]
    synth_train_vectors = embed(synth_train_texts, cache=False)
    synth_train_groups = [SYNTHETIC_GROUP_OFFSET + int(r["template_id"]) for r in synth_train]

    check_vectors = np.vstack([real_train_vectors, synth_train_vectors])
    check_labels = real_train_labels + synth_train_labels
    check_groups = real_train_groups + synth_train_groups
    check_clf = trained.fit(check_vectors, check_labels, check_groups)

    synth_test_texts = [r["clause_text"] for r in synth_test]
    synth_test_truth = [r["proposed_label"] for r in synth_test]

    check_reports = evaluate_all(
        "[held-out check] ",
        check_clf,
        [
            ("US test (323, unchanged)", us_test_texts, us_test_truth),
            ("Indian eval (31, unchanged)", indian_texts, indian_truth),
            ("Synthetic held-out test (42, NEW)", synth_test_texts, synth_test_truth),
        ],
    )
    synth_breakdown = red_subtlety_breakdown(check_clf, synth_test_texts, synth_test_truth, subtlety_of)

    # Baseline for comparison: the currently-shipped trained model (real data only).
    baseline_clf = trained.fit(real_train_vectors, real_train_labels, real_train_groups)
    baseline_reports = evaluate_all(
        "[baseline, real-data-only] ",
        baseline_clf,
        [
            ("US test (323)", us_test_texts, us_test_truth),
            ("Indian eval (31)", indian_texts, indian_truth),
        ],
    )

    write_report(check_clf, check_reports, baseline_reports, synth_breakdown, None, None)
    print("\n".join(f"{r.accuracy:6.1%}  macroF1 {r.macro_f1:.3f}  {r.name}" for r in baseline_reports + check_reports))
    print(f"\nWrote {OUT_PATH}")
    print(
        "\nHeld-out check complete. This script does NOT auto-decide whether the check "
        "'passes' - read the Indian-eval and synthetic-test numbers (especially the "
        "obvious-vs-subtle RED breakdown) in the report and decide whether to proceed to "
        "the final full-data fit. Re-run with --final to do that once confirmed."
    )

    if "--final" in sys.argv:
        # ---------- Stage 2: final fit on ALL 195 synthetic + original US train ----------
        all_synth_texts = [r["clause_text"] for r in synth_train + synth_test]
        all_synth_labels = [r["proposed_label"] for r in synth_train + synth_test]
        all_synth_vectors = embed(all_synth_texts, cache=False)
        all_synth_groups = [SYNTHETIC_GROUP_OFFSET + int(r["template_id"]) for r in (synth_train + synth_test)]

        final_vectors = np.vstack([real_train_vectors, all_synth_vectors])
        final_labels = real_train_labels + all_synth_labels
        final_groups = real_train_groups + all_synth_groups
        final_clf = trained.fit(final_vectors, final_labels, final_groups)
        final_clf.save()  # overwrites app/classifier/artifacts/risk_logreg.joblib

        final_reports = evaluate_all(
            "[SHIPPED, refit on all 195] ",
            final_clf,
            [
                ("US test (323, unchanged)", us_test_texts, us_test_truth),
                ("Indian eval (31, unchanged)", indian_texts, indian_truth),
            ],
        )
        write_report(check_clf, check_reports, baseline_reports, synth_breakdown, final_clf, final_reports)
        print("\n".join(f"{r.accuracy:6.1%}  macroF1 {r.macro_f1:.3f}  {r.name}" for r in final_reports))
        print(f"\nShipped fallback model updated: {trained.ARTIFACT_PATH}")


def write_report(check_clf, check_reports, baseline_reports, synth_breakdown, final_clf, final_reports) -> None:
    lines = [
        "# Trained-classifier fallback improvement - held-out check",
        "",
        "Owner-approved 2026-09-29: all 195 synthetic Indian clauses reviewed, no mislabels; "
        "option (b) - train on the 153 train-side rows only first, hold out the 42 test-side "
        "rows as a third generalization check, watching obvious-vs-subtle RED recall "
        "specifically (every alarm-word phrase in the dataset is RED-only, so a classifier "
        "could look accurate by keyword-matching instead of reasoning).",
        "",
        "This affects only `classify_clause(text, approach=\"trained\")` - the fallback used "
        "when the LLM call fails. `classify_clause()`'s default stays LLM zero-shot regardless "
        "of this result.",
        "",
        "## Stage 1: held-out check (153 synthetic train rows, 42 held out)",
        "",
        f"Grouped CV hyper-parameters: C={check_clf.c}, class_weight={check_clf.class_weight}, "
        f"cv macro-F1 {check_clf.cv_macro_f1:.3f}.",
        "",
        "| Model | Test set | n | Accuracy | Macro-F1 |",
        "|---|---|---|---|---|",
    ]
    for r in baseline_reports:
        lines.append(f"| Baseline (real data only) | {r.name.replace('[baseline, real-data-only] ', '')} | {r.n} | {r.accuracy:.1%} | {r.macro_f1:.3f} |")
    for r in check_reports:
        lines.append(f"| +153 synthetic (held-out check) | {r.name.replace('[held-out check] ', '')} | {r.n} | {r.accuracy:.1%} | {r.macro_f1:.3f} |")
    lines += [
        "",
        "### RED detection on the 42 held-out synthetic clauses, by phrasing type",
        "",
        synth_breakdown,
        "",
        "### Detail",
        "",
    ]
    for r in baseline_reports + check_reports:
        lines += [metrics.to_markdown(r), ""]

    if final_clf is not None:
        lines += [
            "## Stage 2: final fit shipped (all 195 synthetic + original US train)",
            "",
            f"Grouped CV hyper-parameters: C={final_clf.c}, class_weight={final_clf.class_weight}, "
            f"cv macro-F1 {final_clf.cv_macro_f1:.3f}. This is the model saved to "
            f"`{trained.ARTIFACT_PATH.relative_to(Path(__file__).resolve().parents[2])}` and used by "
            "`approach=\"trained\"`.",
            "",
            "**The 42 synthetic held-out rows are part of this model's training data and are "
            "deliberately NOT re-reported here** - the Stage 1 numbers above are the valid "
            "evidence of generalization to synthetic material; re-testing this model on rows "
            "it was trained on would be circular.",
            "",
            "| Test set | n | Accuracy | Macro-F1 |",
            "|---|---|---|",
        ]
        for r in final_reports:
            lines.append(f"| {r.name.replace('[SHIPPED, refit on all 195] ', '')} | {r.n} | {r.accuracy:.1%} | {r.macro_f1:.3f} |")
        lines += ["", "### Detail", ""]
        for r in final_reports:
            lines += [metrics.to_markdown(r), ""]

    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
