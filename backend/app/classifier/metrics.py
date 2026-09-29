"""Evaluation helpers: accuracy, per-class F1, confusion matrix, calibration."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.classifier.dataset import LABELS


@dataclass
class Report:
    name: str
    n: int
    accuracy: float
    macro_f1: float
    per_class: dict[str, dict[str, float]]  # precision / recall / f1 / support
    confusion: np.ndarray  # rows = true, cols = predicted, order = LABELS
    ece: float | None = None
    mean_confidence: float | None = None
    accuracy_when_confident: float | None = None  # confidence >= 0.8
    coverage_when_confident: float | None = None


def expected_calibration_error(confidence: np.ndarray, correct: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        in_bin = (confidence > lo) & (confidence <= hi)
        if in_bin.any():
            ece += in_bin.mean() * abs(correct[in_bin].mean() - confidence[in_bin].mean())
    return float(ece)


def evaluate(name: str, y_true: list[str], y_pred: list[str], probs: np.ndarray | None = None) -> Report:
    index = {label: i for i, label in enumerate(LABELS)}
    n = len(y_true)
    confusion = np.zeros((3, 3), dtype=int)
    for t, p in zip(y_true, y_pred):
        confusion[index[t], index[p]] += 1

    per_class: dict[str, dict[str, float]] = {}
    for label, i in index.items():
        tp = confusion[i, i]
        precision = tp / confusion[:, i].sum() if confusion[:, i].sum() else 0.0
        recall = tp / confusion[i].sum() if confusion[i].sum() else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "support": int(confusion[i].sum()),
        }

    report = Report(
        name=name,
        n=n,
        accuracy=float(np.trace(confusion) / n),
        macro_f1=float(np.mean([v["f1"] for v in per_class.values()])),
        per_class=per_class,
        confusion=confusion,
    )
    if probs is not None:
        confidence = probs.max(axis=1)
        correct = np.array([t == p for t, p in zip(y_true, y_pred)], dtype=float)
        report.ece = expected_calibration_error(confidence, correct)
        report.mean_confidence = float(confidence.mean())
        sure = confidence >= 0.8
        report.coverage_when_confident = float(sure.mean())
        report.accuracy_when_confident = float(correct[sure].mean()) if sure.any() else None
    return report


def to_markdown(report: Report) -> str:
    lines = [f"**{report.name}** (n={report.n})", ""]
    lines.append(f"- Accuracy: **{report.accuracy:.1%}**   Macro-F1: **{report.macro_f1:.3f}**")
    if report.ece is not None:
        lines.append(
            f"- Confidence: mean {report.mean_confidence:.2f}, ECE {report.ece:.3f} "
            "(lower is better calibrated)"
        )
        if report.accuracy_when_confident is not None:
            lines.append(
                f"- When confidence >= 0.80 ({report.coverage_when_confident:.0%} of clauses): "
                f"accuracy {report.accuracy_when_confident:.1%}"
            )
    lines += ["", "| Class | Precision | Recall | F1 | Support |", "|---|---|---|---|---|"]
    for label in LABELS:
        m = report.per_class[label]
        lines.append(
            f"| {label} | {m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} | {m['support']} |"
        )
    lines += [
        "",
        "Confusion matrix (rows = true, columns = predicted):",
        "",
        "| true / pred | " + " | ".join(LABELS) + " |",
        "|---|---|---|---|",
    ]
    for label, row in zip(LABELS, report.confusion):
        lines.append(f"| {label} | " + " | ".join(str(int(v)) for v in row) + " |")
    return "\n".join(lines)
