"""Phase 2 experiment runner: split, train, evaluate every approach on the same test set.

    python scripts/run_phase2.py                 # baselines + trained; LLM if LLM_API_KEY set
    python scripts/run_phase2.py --skip-llm      # never call the LLM
    python scripts/run_phase2.py --llm-limit 60  # LLM on the first 60 test clauses only

Writes data/classifier_eval.md and saves the shipped model artifact.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.classifier import llm, metrics, trained  # noqa: E402
from app.classifier.dataset import LABELS, class_balance, load_dataset  # noqa: E402
from app.classifier.embeddings import embed  # noqa: E402
from app.classifier.split import BLOCK_SIZE, DEDUP_THRESHOLD, check_leakage, make_split  # noqa: E402

EVAL_PATH = Path(__file__).resolve().parents[2] / "data" / "classifier_eval.md"
INDIAN_SET = Path(__file__).resolve().parents[2] / "data" / "indian_eval_set.csv"


def wilson(correct: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% interval for an accuracy; wide on small n, which is the point of showing it."""
    if n == 0:
        return 0.0, 0.0
    p = correct / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


def indian_domain_section(clf, shots_few, llm_ready: bool, us_reports) -> list[str]:
    """Score the same models on hand-labeled clauses from the official Indian forms."""
    if not INDIAN_SET.exists():
        return ["## Indian-domain check", "", "`data/indian_eval_set.csv` not found; run "
                "`python scripts/build_indian_eval_set.py`.", ""]
    rows = list(csv.DictReader(INDIAN_SET.open(encoding="utf-8")))
    reviewed = sum(1 for r in rows if r["reviewed_label"].strip())
    truth = [(r["reviewed_label"].strip() or r["proposed_label"]).upper() for r in rows]
    texts = [r["text"] for r in rows]

    # (name, predicted labels, probabilities, ground truth used for it, indices covered)
    results: list[tuple[str, list[str], np.ndarray, list[str]]] = []
    p_trained = clf.predict_proba(embed(texts, cache=False))
    results.append(("Trained classifier", [LABELS[k] for k in p_trained.argmax(1)], p_trained, truth))
    quota_notes = []
    if llm_ready:
        for name, shots in (("LLM zero-shot", []), ("LLM few-shot", shots_few)):
            print(f"Indian set: {name}", flush=True)
            probs, completed, quota_hit = run_llm(name, texts, shots)
            if completed == 0:
                quota_notes.append(f"{name} on the Indian set: 0 clauses classified (quota exhausted).")
                continue
            results.append((f"{name}{'' if completed == len(texts) else f' (partial, n={completed})'}",
                             [LABELS[k] for k in probs.argmax(1)], probs, truth[:completed]))
            if quota_hit:
                quota_notes.append(
                    f"{name} on the Indian set stopped at {completed}/{len(texts)}: daily quota reached."
                )

    majority = max(set(truth), key=truth.count)
    synthetic = [r for r in rows if r["source"].startswith("synthetic")]
    real = len(rows) - len(synthetic)
    red_caveat = (
        "**There are no RED clauses**: blank official templates are deliberately neutral, so this sample "
        "cannot test the classifier's RED detection at all."
        if truth.count("RED") == 0 else
        f"**{truth.count('RED')} RED clause(s)** are included: {real} real clauses from the blank official "
        f"forms contain none (they are deliberately neutral), so {len(synthetic)} were hand-authored "
        "specifically to test RED detection - see `reviewed_reason` in the CSV for each one's rationale."
    )
    lines = [
        f"## Indian-domain check ({len(rows)} hand-labeled clauses)",
        "",
        f"**Why:** the training data (US-style leases) is not Indian. This scores the same models on "
        f"{real} real clauses from the official Tamil Nadu, West Bengal and Maharashtra forms plus "
        f"{len(synthetic)} authored clauses (`data/indian_eval_set.csv`; the real ones are segmented by "
        "Person A's pipeline, with fill-in blanks shown as `[blank]`).",
        "",
        f"**Labels:** {reviewed} of {len(rows)} are owner-reviewed. "
        + ("" if reviewed == len(rows) else
           "The rest are **proposals written by Claude, not ground truth** - review the `reviewed_label` "
           "column, then re-run to refresh these numbers."),
        f"Label mix: {', '.join(f'{k} {truth.count(k)}' for k in LABELS)}. " + red_caveat,
        "",
    ]
    if quota_notes:
        lines += ["> " + "\n> ".join(quota_notes), ""]
    lines += [
        "| Approach | Indian sample accuracy (95% CI) | US test accuracy | Change |",
        "|---|---|---|---|",
    ]
    us = {r.name.split(" (")[0].split(" - ")[0]: r for r in us_reports}
    for name, pred, probs, name_truth in results:
        correct = sum(t == p for t, p in zip(name_truth, pred))
        lo, hi = wilson(correct, len(name_truth))
        # Strip a "(partial, n=..)" suffix before matching, so a partial Indian-set run
        # still finds its US counterpart by name instead of comparing against nothing.
        name_base = name.split(" (")[0]
        counterpart = next((r for k, r in us.items() if name_base.lower().split()[-1] in k.lower()
                            or (name_base.startswith("Trained") and k.startswith("Trained"))), None)
        us_acc = f"{counterpart.accuracy:.1%}" if counterpart else "-"
        delta = f"{(correct / len(name_truth) - counterpart.accuracy) * 100:+.1f} pts" if counterpart else "-"
        lines.append(
            f"| {name} | {correct / len(name_truth):.1%} ({lo:.0%}-{hi:.0%}), n={len(name_truth)} | {us_acc} | {delta} |"
        )
    correct_majority = sum(t == majority for t in truth)
    lines.append(f"| Majority baseline (always {majority}) | {correct_majority / len(truth):.1%} | 48.0% | - |")
    lines += ["", f"Read the interval, not the point estimate: with {len(rows)} clauses one clause is "
              f"{100 / len(rows):.1f} points and the interval is wide. This is a sanity check on domain "
              "transfer, not a benchmark.", ""]

    for name, pred, probs, name_truth in results:
        r = metrics.evaluate(f"{name} on Indian sample", name_truth, pred, probs)
        supported = [v["f1"] for v in r.per_class.values() if v["support"] > 0]
        lines += [metrics.to_markdown(r), "",
                  f"(Macro-F1 over the {len(supported)} classes present: {sum(supported) / len(supported):.3f}; "
                  "the table's macro-F1 counts absent RED as 0.)", ""]
    misses = []
    for name, pred, _, name_truth in results:
        for row, t, p in zip(rows, name_truth, pred):
            if t != p:
                misses.append(f"- {name}: {row['id']} true {t}, predicted {p} - {row['text'][:110]}...")
    if misses:
        lines += ["Misclassified Indian clauses:", "", *misses, ""]
    return lines


def pick_shots(split, per_class: int = 2, seed: int = 7) -> list[tuple[str, str]]:
    """Few-shot examples come from TRAIN only, so they cannot leak the test set."""
    rng = np.random.default_rng(seed)
    shots: list[tuple[str, str]] = []
    for label in LABELS:
        pool = [i for i in split.train if split.clauses[i].label == label]
        for i in rng.choice(pool, size=per_class, replace=False):
            shots.append((split.clauses[int(i)].text, label))
    order = rng.permutation(len(shots))
    return [shots[i] for i in order]


def run_llm(name: str, texts: list[str], shots) -> tuple[np.ndarray, int, bool]:
    """Classify `texts` in order; stop early (without raising) if the daily quota is hit.

    Returns (probabilities for the completed prefix, how many completed, whether the
    daily quota was the reason it stopped short). Every completed answer is already
    cached on disk, so a later re-run picks up exactly where this left off.
    """
    classifier = llm.LLMClassifier(shots=shots)
    rows = []
    quota_hit = False
    for n, text in enumerate(texts, start=1):
        try:
            probs = classifier.predict_proba_one(text)
        except llm.DailyQuotaExceededError as exc:
            print(f"  {name}: stopped at {len(rows)}/{len(texts)} - {exc}", flush=True)
            quota_hit = True
            break
        rows.append([probs[label] for label in LABELS])
        if n % 25 == 0:
            print(f"  {name}: {n}/{len(texts)}", flush=True)
    return np.array(rows), len(rows), quota_hit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-llm", action="store_true")
    parser.add_argument("--llm-limit", type=int, default=None)
    args = parser.parse_args()

    clauses = load_dataset()
    split = make_split(clauses, embed([c.text for c in clauses]))
    leak = check_leakage(split)
    if not leak.clean:
        raise SystemExit(f"Leakage check FAILED: {leak}")

    labels = [c.label for c in split.clauses]
    y_train = [labels[i] for i in split.train]
    y_test = [labels[i] for i in split.test]
    test_texts = [split.clauses[i].text for i in split.test]

    reports: list[metrics.Report] = []

    majority = max(set(y_train), key=y_train.count)
    reports.append(metrics.evaluate(f"Majority-class baseline (always {majority})", y_test, [majority] * len(y_test)))

    clf = trained.fit(split.vectors[split.train], y_train, [split.block_of[i] for i in split.train])
    p_trained = clf.predict_proba(split.vectors[split.test])
    reports.append(
        metrics.evaluate(
            "Trained classifier (MiniLM embeddings + logistic regression, calibrated)",
            y_test, [LABELS[k] for k in p_trained.argmax(1)], p_trained,
        )
    )

    llm_reports: dict[str, tuple[metrics.Report, np.ndarray, int]] = {}
    llm_note = ""
    if args.skip_llm or not llm.is_configured():
        llm_note = (
            "LLM baseline NOT RUN: no `LLM_API_KEY` in `.env`. Add a free-tier key "
            "(see `.env.example`) and re-run `python scripts/run_phase2.py`."
        )
    else:
        n = args.llm_limit or len(test_texts)
        notes = []
        for name, shots in (("zero-shot", []), ("few-shot (6 train examples)", pick_shots(split))):
            print(f"LLM {name} on {n} clauses...", flush=True)
            probs, completed, quota_hit = run_llm(name, test_texts[:n], shots)
            if completed == 0:
                notes.append(f"LLM {name}: 0 clauses classified (quota hit before this pass could run).")
                continue
            report = metrics.evaluate(
                f"LLM {name} - {llm.settings()['model']}" + ("" if completed == n else f" (partial, n={completed})"),
                y_test[:completed], [LABELS[k] for k in probs.argmax(1)], probs,
            )
            llm_reports[name] = (report, probs, completed)
            reports.append(report)
            if quota_hit:
                notes.append(
                    f"LLM {name} stopped early at {completed}/{n}: the provider's free-tier daily quota "
                    f"was reached. Cached answers are kept; re-run this script after the quota resets "
                    "(typically 24h) to complete the rest, or set LLM_MODEL to a model with separate quota."
                )
        if llm_reports:
            best_name = max(llm_reports, key=lambda k: llm_reports[k][0].macro_f1)
            report_best, p_llm, completed_best = llm_reports[best_name]
            ens = (p_trained[:completed_best] + p_llm) / 2
            reports.append(
                metrics.evaluate(
                    f"Ensemble (fixed 50/50 average of trained + LLM {best_name})"
                    + ("" if completed_best == n else f" (partial, n={completed_best})"),
                    y_test[:completed_best], [LABELS[k] for k in ens.argmax(1)], ens,
                )
            )
        if n < len(test_texts):
            notes.append(f"LLM rows cover only the first {n} of {len(test_texts)} test clauses (--llm-limit).")
        llm_note = "\n> \n> ".join(notes)

    # Ship model: same hyper-parameters, refit on ALL deduplicated data (train + test).
    shipped = trained.fit(split.vectors, labels, split.block_of)
    shipped.save()

    india = indian_domain_section(clf, pick_shots(split), llm.is_configured() and not args.skip_llm, reports)
    write_report(clauses, split, leak, clf, reports, llm_note, india)
    for r in reports:
        print(f"{r.accuracy:6.1%}  macroF1 {r.macro_f1:.3f}  {r.name}")
    print(f"\nWrote {EVAL_PATH}")


def write_report(clauses, split, leak, clf, reports, llm_note, india) -> None:
    balance = class_balance(clauses)
    test_labels = [split.clauses[i].label for i in split.test]
    train_labels = [split.clauses[i].label for i in split.train]

    def dist(values):
        return ", ".join(f"{k} {values.count(k)} ({values.count(k) / len(values):.0%})" for k in LABELS)

    lines = [
        "# Phase 2 - classifier evaluation",
        "",
        f"Generated {date.today().isoformat()} by `backend/scripts/run_phase2.py`. Every number below is "
        "computed on the **same held-out test set** unless a row says otherwise.",
        "",
        "## Method",
        "",
        f"- **Data:** {len(clauses)} labeled clauses (`data/ML_Final_Dataset_Cleaned.xlsx`). "
        f"Distribution: {', '.join(f'{k} {balance[k][0]} ({balance[k][1]:.1%})' for k in LABELS)}.",
        f"- **Deduplication:** clauses with embedding cosine >= {DEDUP_THRESHOLD} (all-MiniLM-L6-v2) are "
        f"collapsed to one. Removed {split.dropped_duplicates}, leaving {len(split.clauses)}. Duplicate clusters "
        "never disagreed on label. The twins are the same boilerplate across different leases.",
        f"- **Split:** the file has no lease ID (`clause_id` is a row number). Rows are in lease order, so "
        f"contiguous blocks of {BLOCK_SIZE} rows stand in for leases and whole blocks go to train or test "
        f"(seed {split.seed}, ~20% test, chosen so the class mix matches). "
        f"**This is a proxy:** a real lease can straddle a block edge, so leakage is reduced, not proven zero.",
        f"- **Train:** {len(split.train)} clauses ({dist(train_labels)}). **Test:** {len(split.test)} clauses "
        f"({dist(test_labels)}).",
        "",
        "## Leakage check",
        "",
        f"- Blocks appearing in both train and test: **{leak.shared_blocks}**",
        f"- Clause IDs appearing in both: **{leak.shared_clause_ids}**",
        f"- Highest cosine similarity between any test clause and any train clause: **{leak.max_cross_similarity:.3f}** "
        f"(below the {DEDUP_THRESHOLD} dedup threshold)",
        f"- Test clauses with a train neighbour >= 0.90: **{leak.test_with_close_train_neighbour} of {leak.test_size}** "
        "(paraphrases that survive dedup; a small optimistic bias, reported rather than hidden)",
        "",
        "## Model selection (training data only)",
        "",
        f"Grouped 5-fold cross-validation over the training blocks chose C={clf.c}, class_weight={clf.class_weight}, "
        f"macro-F1 {clf.cv_macro_f1:.3f}. Softmax temperature {clf.temperature:.2f} fitted on out-of-fold predictions. "
        "The test set played no part.",
        "",
        "## Results",
        "",
        "| Approach | n | Accuracy | Macro-F1 | ECE |",
        "|---|---|---|---|---|",
    ]
    for r in reports:
        ece = f"{r.ece:.3f}" if r.ece is not None else "-"
        lines.append(f"| {r.name} | {r.n} | {r.accuracy:.1%} | {r.macro_f1:.3f} | {ece} |")
    if llm_note:
        lines += ["", f"> {llm_note}"]
    lines += ["", "## Detail per approach", ""]
    for r in reports:
        lines += [metrics.to_markdown(r), ""]
    lines += india
    EVAL_PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
