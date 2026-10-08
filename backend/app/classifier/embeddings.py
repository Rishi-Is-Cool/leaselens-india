"""Sentence embeddings with an on-disk cache keyed by the exact texts embedded.

Two interchangeable backends compute the same all-MiniLM-L6-v2 embedding:

- sentence-transformers (PyTorch): the default, used to train the risk classifier.
- ONNX Runtime: the same model's official ONNX export with the same mean pooling and
  normalisation, at a fraction of PyTorch's memory, so the API fits a 512 MB free-tier
  host. Selected with EMBEDDINGS_BACKEND=onnx, or automatically when PyTorch/
  sentence-transformers is not installed. tests/test_embeddings_backend.py checks the two
  agree.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path

import numpy as np

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MAX_TOKENS = 256  # the model's max_seq_length in sentence-transformers
CACHE_DIR = Path(__file__).resolve().parents[3] / "data"

_model = None


def backend() -> str:
    chosen = os.environ.get("EMBEDDINGS_BACKEND", "").strip().lower()
    if chosen in ("onnx", "torch"):
        return chosen
    return "torch" if importlib.util.find_spec("sentence_transformers") else "onnx"


class OnnxMiniLM:
    def __init__(self):
        import onnxruntime
        from huggingface_hub import hf_hub_download
        from tokenizers import Tokenizer

        self.tokenizer = Tokenizer.from_file(hf_hub_download(MODEL_NAME, "tokenizer.json"))
        self.tokenizer.enable_truncation(max_length=MAX_TOKENS)
        self.tokenizer.enable_padding(pad_id=0, pad_token="[PAD]")
        options = onnxruntime.SessionOptions()
        options.intra_op_num_threads = int(os.environ.get("EMBEDDINGS_THREADS", "1"))
        self.session = onnxruntime.InferenceSession(
            hf_hub_download(MODEL_NAME, "onnx/model.onnx"), options, providers=["CPUExecutionProvider"]
        )
        self.inputs = {i.name for i in self.session.get_inputs()}

    def encode(self, texts: list[str], batch_size: int = 32, **_ignored) -> np.ndarray:
        out = []
        for start in range(0, len(texts), batch_size):
            encodings = self.tokenizer.encode_batch(texts[start : start + batch_size])
            ids = np.array([e.ids for e in encodings], dtype=np.int64)
            mask = np.array([e.attention_mask for e in encodings], dtype=np.int64)
            feed = {"input_ids": ids, "attention_mask": mask}
            if "token_type_ids" in self.inputs:
                feed["token_type_ids"] = np.zeros_like(ids)
            hidden = self.session.run(None, feed)[0]
            weights = mask[..., None].astype(np.float32)
            pooled = (hidden * weights).sum(axis=1) / np.clip(weights.sum(axis=1), 1e-9, None)
            out.append(pooled / np.clip(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-12, None))
        return np.concatenate(out).astype(np.float32)


def _get_model():
    global _model
    if _model is None:
        if backend() == "onnx":
            _model = OnnxMiniLM()
        else:
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
