"""Baseline #1: sentence embeddings + logistic regression, with temperature calibration.

Hyper-parameters are chosen by grouped cross-validation on the training portion only
(groups = pseudo-lease blocks), so the held-out test set never influences them. The
softmax temperature is fitted on out-of-fold predictions, which is what makes the
reported confidence comparable to how often the model is actually right.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
from scipy.optimize import minimize_scalar
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.model_selection import GroupKFold

from app.classifier.dataset import LABELS

ARTIFACT_PATH = Path(__file__).resolve().parent / "artifacts" / "risk_logreg.joblib"
C_GRID = (0.1, 0.3, 1.0, 3.0, 10.0, 30.0)
CLASS_WEIGHTS = (None, "balanced")


def _encode(labels: list[str]) -> np.ndarray:
    return np.array([LABELS.index(label) for label in labels])


def _ordered_proba(model: LogisticRegression, vectors: np.ndarray) -> np.ndarray:
    raw = model.predict_proba(vectors)
    ordered = np.zeros((len(vectors), len(LABELS)))
    for column, klass in enumerate(model.classes_):
        ordered[:, klass] = raw[:, column]
    return ordered


def _apply_temperature(probs: np.ndarray, temperature: float) -> np.ndarray:
    logits = np.log(np.clip(probs, 1e-9, 1.0)) / temperature
    logits -= logits.max(axis=1, keepdims=True)
    exp = np.exp(logits)
    return exp / exp.sum(axis=1, keepdims=True)


def _fit_temperature(probs: np.ndarray, y: np.ndarray) -> float:
    def nll(t: float) -> float:
        calibrated = _apply_temperature(probs, t)
        return float(-np.log(np.clip(calibrated[np.arange(len(y)), y], 1e-9, 1.0)).mean())

    return float(minimize_scalar(nll, bounds=(0.3, 5.0), method="bounded").x)


@dataclass
class TrainedClassifier:
    model: LogisticRegression
    temperature: float
    c: float
    class_weight: str | None
    cv_macro_f1: float

    def predict_proba(self, vectors: np.ndarray) -> np.ndarray:
        return _apply_temperature(_ordered_proba(self.model, vectors), self.temperature)

    def save(self, path: Path = ARTIFACT_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @staticmethod
    def load(path: Path = ARTIFACT_PATH) -> "TrainedClassifier":
        return joblib.load(path)


def fit(vectors: np.ndarray, labels: list[str], groups: list[int], *, folds: int = 5) -> TrainedClassifier:
    y = _encode(labels)
    groups_arr = np.asarray(groups)
    splitter = GroupKFold(n_splits=folds)

    best = None
    for class_weight in CLASS_WEIGHTS:
        for c in C_GRID:
            oof = np.zeros((len(y), len(LABELS)))
            for tr, va in splitter.split(vectors, y, groups_arr):
                m = LogisticRegression(C=c, class_weight=class_weight, max_iter=2000).fit(vectors[tr], y[tr])
                oof[va] = _ordered_proba(m, vectors[va])
            score = f1_score(y, oof.argmax(axis=1), average="macro")
            if best is None or score > best[0]:
                best = (score, c, class_weight, oof)

    score, c, class_weight, oof = best
    temperature = _fit_temperature(oof, y)
    model = LogisticRegression(C=c, class_weight=class_weight, max_iter=2000).fit(vectors, y)
    return TrainedClassifier(
        model=model, temperature=temperature, c=c, class_weight=class_weight, cv_macro_f1=float(score)
    )
