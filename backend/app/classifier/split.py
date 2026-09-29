"""Near-duplicate removal and a leakage-checked train/test split.

The dataset has no lease identifier (`clause_id` is a global row number), so two
safeguards are combined:

1. Near-duplicates (cosine >= DEDUP_THRESHOLD) are collapsed to one clause. The audit found
   these are the same boilerplate copied across *different* leases, so a row-block split
   alone would not have kept them apart.
2. Rows are in lease order, so contiguous blocks of BLOCK_SIZE rows stand in for leases,
   and whole blocks are assigned to train or test. This is a proxy: a real lease can
   straddle a block boundary, so leakage there is reduced, not eliminated.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components

from app.classifier.dataset import LABELS, LabeledClause

DEDUP_THRESHOLD = 0.95
BLOCK_SIZE = 30
TEST_FRACTION = 0.20


@dataclass
class Split:
    train: list[int]  # indices into the deduplicated list
    test: list[int]
    clauses: list[LabeledClause]  # deduplicated
    vectors: np.ndarray  # embeddings aligned with `clauses`
    block_of: list[int]  # pseudo-lease block per deduplicated clause
    seed: int
    dropped_duplicates: int


def deduplicate(
    clauses: list[LabeledClause], vectors: np.ndarray, threshold: float = DEDUP_THRESHOLD
) -> tuple[list[LabeledClause], np.ndarray]:
    similar = csr_matrix(vectors @ vectors.T >= threshold)
    count, component = connected_components(similar, directed=False)
    keep = [int(np.where(component == k)[0][0]) for k in range(count)]
    keep.sort()
    return [clauses[i] for i in keep], vectors[keep]


def make_split(
    clauses: list[LabeledClause],
    vectors: np.ndarray,
    *,
    seed: int = 0,
    block_size: int = BLOCK_SIZE,
    test_fraction: float = TEST_FRACTION,
    tries: int = 400,
) -> Split:
    unique, unique_vectors = deduplicate(clauses, vectors)
    # Blocks follow the ORIGINAL row order, so blocks are cut before dedup renumbering.
    block_of = [(c.clause_id - 1) // block_size for c in unique]
    blocks = sorted(set(block_of))
    labels = np.array([c.label for c in unique])
    overall = np.array([(labels == label).mean() for label in LABELS])
    target_test = test_fraction * len(unique)

    rng = np.random.default_rng(seed)
    best, best_score = None, np.inf
    for _ in range(tries):
        order = rng.permutation(blocks)
        test_blocks: set[int] = set()
        size = 0
        for block in order:
            if size >= target_test:
                break
            test_blocks.add(int(block))
            size += sum(1 for b in block_of if b == block)
        mask = np.array([b in test_blocks for b in block_of])
        share = np.array([(labels[mask] == label).mean() for label in LABELS])
        score = np.abs(share - overall).sum() + abs(mask.sum() - target_test) / len(unique)
        if score < best_score:
            best, best_score = mask, score

    test = [int(i) for i in np.where(best)[0]]
    train = [int(i) for i in np.where(~best)[0]]
    return Split(
        train=train,
        test=test,
        clauses=unique,
        vectors=unique_vectors,
        block_of=block_of,
        seed=seed,
        dropped_duplicates=len(clauses) - len(unique),
    )


@dataclass
class LeakageReport:
    shared_blocks: int
    shared_clause_ids: int
    max_cross_similarity: float
    test_with_close_train_neighbour: int  # cosine >= 0.90
    test_size: int
    train_size: int

    @property
    def clean(self) -> bool:
        return (
            self.shared_blocks == 0
            and self.shared_clause_ids == 0
            and self.max_cross_similarity < DEDUP_THRESHOLD
        )


def check_leakage(split: Split) -> LeakageReport:
    train_blocks = {split.block_of[i] for i in split.train}
    test_blocks = {split.block_of[i] for i in split.test}
    train_ids = {split.clauses[i].clause_id for i in split.train}
    test_ids = {split.clauses[i].clause_id for i in split.test}
    cross = split.vectors[split.test] @ split.vectors[split.train].T
    closest = cross.max(axis=1)
    return LeakageReport(
        shared_blocks=len(train_blocks & test_blocks),
        shared_clause_ids=len(train_ids & test_ids),
        max_cross_similarity=float(closest.max()),
        test_with_close_train_neighbour=int((closest >= 0.90).sum()),
        test_size=len(split.test),
        train_size=len(split.train),
    )
