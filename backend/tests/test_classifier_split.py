import numpy as np

from app.classifier.dataset import load_dataset
from app.classifier.embeddings import embed
from app.classifier.split import DEDUP_THRESHOLD, check_leakage, make_split


def _split():
    clauses = load_dataset()
    return make_split(clauses, embed([c.text for c in clauses]))


def test_split_has_no_shared_block_or_clause():
    report = check_leakage(_split())
    assert report.shared_blocks == 0
    assert report.shared_clause_ids == 0


def test_no_near_duplicate_crosses_the_split():
    report = check_leakage(_split())
    assert report.max_cross_similarity < DEDUP_THRESHOLD
    assert report.clean


def test_train_and_test_partition_the_deduplicated_set():
    split = _split()
    assert set(split.train).isdisjoint(split.test)
    assert len(split.train) + len(split.test) == len(split.clauses)
    assert 0.15 <= len(split.test) / len(split.clauses) <= 0.28


def test_every_class_present_in_test():
    split = _split()
    assert {split.clauses[i].label for i in split.test} == {"GREEN", "YELLOW", "RED"}
    assert np.all(np.isfinite(split.vectors))
