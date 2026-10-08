"""The ONNX backend used on the hosted API must produce the embeddings the risk classifier
was trained on (sentence-transformers), or its predictions silently drift."""

import importlib.util

import numpy as np
import pytest

from app.classifier import embeddings

pytestmark = pytest.mark.skipif(
    not (importlib.util.find_spec("onnxruntime") and importlib.util.find_spec("sentence_transformers")),
    reason="needs both embedding backends installed",
)

TEXTS = [
    "The Licensee shall pay a monthly licence fee of Rs. 25,000 on or before the 5th of each month.",
    "The Licensor may terminate this agreement at any time without notice and re-enter the premises.",
    "The security deposit shall be refunded without interest within 15 days of vacating.",
    "Short.",
    "word " * 400,  # longer than the 256-token limit: both must truncate the same way
]


def test_onnx_matches_sentence_transformers():
    from sentence_transformers import SentenceTransformer

    torch_vectors = SentenceTransformer(embeddings.MODEL_NAME).encode(TEXTS, normalize_embeddings=True)
    onnx_vectors = embeddings.OnnxMiniLM().encode(TEXTS)
    cosine = (torch_vectors * onnx_vectors).sum(axis=1)
    assert cosine.min() > 0.9999, cosine
    assert np.allclose(np.linalg.norm(onnx_vectors, axis=1), 1, atol=1e-5)
