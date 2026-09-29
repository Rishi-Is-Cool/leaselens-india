"""Phase 2 audit: class balance, near-duplicates (embedding cosine), and embedding cache.

    python scripts/audit_dataset.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.classifier.dataset import LABELS, class_balance, load_dataset  # noqa: E402

CACHE = Path(__file__).resolve().parents[2] / "data" / ".embeddings_minilm.npy"
MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def embed(texts: list[str]) -> np.ndarray:
    if CACHE.exists():
        cached = np.load(CACHE)
        if len(cached) == len(texts):
            return cached
    from sentence_transformers import SentenceTransformer

    vectors = SentenceTransformer(MODEL).encode(
        texts, normalize_embeddings=True, batch_size=64, show_progress_bar=False
    )
    np.save(CACHE, vectors)
    return vectors


def main() -> None:
    clauses = load_dataset()
    print(f"clauses: {len(clauses)}")
    for label, (n, share) in class_balance(clauses).items():
        print(f"  {label:<7}{n:>5}  {share:6.1%}")
    print(f"  majority-class accuracy: {max(n for n, _ in class_balance(clauses).values()) / len(clauses):.1%}")

    vectors = embed([c.text for c in clauses])
    sim = vectors @ vectors.T
    np.fill_diagonal(sim, -1)
    best = sim.max(axis=1)
    partner = sim.argmax(axis=1)
    labels = np.array([c.label for c in clauses])
    print("\nnear-duplicate audit (cosine, all-MiniLM-L6-v2):")
    for threshold in (0.98, 0.95, 0.90, 0.85):
        flagged = best >= threshold
        disagree = (labels[flagged] != labels[partner[flagged]]).mean() if flagged.any() else 0
        print(f"  >= {threshold}: {int(flagged.sum()):>4} clauses have a partner; partner label differs in {disagree:.1%}")

    upper = np.triu(sim >= 0.95, k=1)
    pairs = np.argwhere(upper)
    gap = np.abs(pairs[:, 0] - pairs[:, 1]) if len(pairs) else np.array([])
    if len(pairs):
        print(f"\npairs >= 0.95: {len(pairs)}; median row distance {int(np.median(gap))}; "
              f"{int((gap <= 50).sum())} within 50 rows of each other")
        for a, b in pairs[np.argsort(-sim[pairs[:, 0], pairs[:, 1]])][:6]:
            print(f"  {sim[a, b]:.3f} [{clauses[a].clause_id}:{labels[a]}] {clauses[a].text[:70]!r}")
            print(f"        [{clauses[b].clause_id}:{labels[b]}] {clauses[b].text[:70]!r}")


if __name__ == "__main__":
    main()
