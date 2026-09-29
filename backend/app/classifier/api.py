"""The single entry point the rest of LeaseLens uses: `classify_clause(text)`.

Nothing downstream needs to know which model is underneath. The approach is chosen by
DEFAULT_APPROACH, set from the measured comparison in data/classifier_eval.md: LLM
zero-shot beats the trained classifier by 10.6 points accuracy on the US test set and,
unlike the trained classifier, holds up on the small Indian sample too. If the LLM call
fails for any reason (no API key, a rate limit, a network error), `classify_clause`
falls back to the trained classifier rather than raising - see `data/classifier_eval.md`
"Decision" for why that fallback matters: this project's own evaluation run hit a
free-tier provider's daily quota mid-run.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np

from app.classifier.dataset import LABELS

DEFAULT_APPROACH = "llm"  # "trained" | "llm" | "ensemble"

logger = logging.getLogger(__name__)

_trained = None
_llm = None


@dataclass(frozen=True)
class ClassificationResult:
    label: str  # "GREEN" | "YELLOW" | "RED"
    confidence: float  # probability of `label`, 0-1
    probabilities: dict[str, float] = field(default_factory=dict)
    approach: str = DEFAULT_APPROACH


def _trained_probs(text: str) -> np.ndarray:
    global _trained
    from app.classifier.embeddings import embed
    from app.classifier.trained import ARTIFACT_PATH, TrainedClassifier

    if _trained is None:
        if not ARTIFACT_PATH.exists():
            raise FileNotFoundError(
                f"Trained model not found at {ARTIFACT_PATH}. Run: python scripts/run_phase2.py"
            )
        _trained = TrainedClassifier.load()
    return _trained.predict_proba(embed([text], cache=False))[0]


def _llm_probs(text: str) -> np.ndarray:
    global _llm
    from app.classifier.llm import LLMClassifier

    if _llm is None:
        _llm = LLMClassifier()
    probs = _llm.predict_proba_one(text)
    return np.array([probs[label] for label in LABELS])


def classify_clause(text: str, *, approach: str | None = None) -> ClassificationResult:
    """Classify one clause's risk to a tenant. Accepts a clause object's `text` directly."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("classify_clause needs a non-empty clause text.")
    approach = approach or DEFAULT_APPROACH

    used = approach
    if approach == "trained":
        probs = _trained_probs(text)
    elif approach == "llm":
        try:
            probs = _llm_probs(text)
        except Exception as exc:  # noqa: BLE001 - any LLM failure falls back, deliberately broad
            logger.warning("classify_clause: LLM approach failed (%s), falling back to trained.", exc)
            probs = _trained_probs(text)
            used = "trained (llm fallback)"
    elif approach == "ensemble":
        probs = (_trained_probs(text) + _llm_probs(text)) / 2
    else:
        raise ValueError(f"Unknown approach {approach!r}")

    best = int(np.argmax(probs))
    return ClassificationResult(
        label=LABELS[best],
        confidence=float(probs[best]),
        probabilities={label: float(p) for label, p in zip(LABELS, probs)},
        approach=used,
    )
