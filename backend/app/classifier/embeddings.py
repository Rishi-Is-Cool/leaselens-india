"""Sentence embeddings with an on-disk cache keyed by the exact texts embedded."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
CACHE_DIR = Path(__file__).resolve().parents[3] / "data"

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed(texts: list[str], *, cache: bool = True) -> np.ndarray:
    """L2-normalised embeddings, so a dot product is the cosine similarity."""
    if not texts:
        return np.zeros((0, 384), dtype=np.float32)
    digest = hashlib.sha1("\n".join(texts).encode("utf-8")).hexdigest()[:16]
    path = CACHE_DIR / f".embeddings_{digest}.npy"
    if cache and path.exists():
        return np.load(path)
    vectors = _get_model().encode(
        texts, normalize_embeddings=True, batch_size=64, show_progress_bar=False
    )
    vectors = np.asarray(vectors, dtype=np.float32)
    if cache and len(texts) > 1:
        np.save(path, vectors)
    return vectors
