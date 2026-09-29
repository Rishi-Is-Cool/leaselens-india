"""Cluster and leak-free split for data/synthetic_indian_clauses.csv.

Audit finding: the 195 synthetic clauses are generated from 47 underlying templates
(state/party-name substitutions only - see generate_synthetic_indian_clauses.py), each
cloned 2-5x across states. A naive random or document-level split does not prevent
leakage here, because a template's state-variants are near-duplicates of each other and
could land on both sides of train/test, inflating test accuracy without testing real
generalization.

Method (two independent clustering passes, cross-checked):
  1. Rule-based: normalize party terms / property references / amounts to placeholders,
     then exact-match on the normalized text.
  2. Embedding-based: cosine similarity >= 0.95 on all-MiniLM-L6-v2, union-find clustering.
  3. Split at the CLUSTER level (rule-based; see note below), stratified by label, 75/25.
  4. Verify: no cluster appears on both sides.

Note on the cross-check result: on this dataset the two methods disagree substantially
(47 rule-based clusters vs. 141 embedding clusters). Inspection confirms the rule-based
clusters are correct and the embedding threshold is the one that's too strict here: MiniLM
treats the actor-noun swap itself (e.g. "Licensee" vs "Tenant" vs "Lessee") as enough of a
semantic difference to often push cosine similarity below 0.95, even though the surrounding
clause is otherwise identical, same label, same structure. Every rule-based cluster was
checked and found to contain a single label and a single topic (no false merges), and
cluster sizes exactly match the generator's own template structure (8 x 2, 8 x 3, 31 x 5 =
47), which independently confirms the rule-based grouping is right for this dataset. The
split below uses the rule-based clusters.

    python scripts/dedup_and_split_synthetic.py
"""

from __future__ import annotations

import csv
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

DATA = Path(__file__).resolve().parents[2] / "data"
SRC = DATA / "synthetic_indian_clauses.csv"
OUT_CSV = DATA / "synthetic_indian_clauses_with_split.csv"
OUT_REPORT = DATA / "synthetic_dedup_split_report.json"

SIM_THRESHOLD = 0.95
TEST_FRACTION = 0.25
SEED = 42


def normalize(text: str) -> str:
    t = text.lower()
    t = re.sub(r"\b(licensee|tenant|lessee)\b", "PARTY_A", t)
    t = re.sub(r"\b(licensor|landlord|lessor|owner)\b", "PARTY_B", t)
    t = re.sub(
        r"\b(licensed premises|premises|demised premises|rented premises|said property)\b",
        "PROPERTY",
        t,
    )
    t = re.sub(r"rs\.?\s?[\d,]+", "AMOUNT", t)
    return re.sub(r"\s+", " ", t).strip()


def rule_based_clusters(texts: list[str]) -> list[int]:
    key_to_id: dict[str, int] = {}
    ids = []
    for text in texts:
        key = normalize(text)
        ids.append(key_to_id.setdefault(key, len(key_to_id)))
    return ids


def embedding_clusters(texts: list[str], threshold: float = SIM_THRESHOLD) -> list[int]:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("all-MiniLM-L6-v2")
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    sim = np.asarray(vectors) @ np.asarray(vectors).T

    n = len(texts)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(n):
        for j in range(i + 1, n):
            if sim[i, j] >= threshold:
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[ri] = rj

    root_to_id: dict[int, int] = {}
    ids = []
    for i in range(n):
        root = find(i)
        ids.append(root_to_id.setdefault(root, len(root_to_id)))
    return ids


def split_by_cluster(rows: list[dict], cluster_of: list[int], seed: int = SEED) -> None:
    """Assigns row["split"] in place: whole clusters go to train or test together."""
    cluster_label: dict[int, str] = {}
    members: dict[int, list[int]] = defaultdict(list)
    for i, (row, cid) in enumerate(zip(rows, cluster_of)):
        members[cid].append(i)
    for cid, idxs in members.items():
        cluster_label[cid] = Counter(rows[i]["proposed_label"] for i in idxs).most_common(1)[0][0]

    by_label: dict[str, list[int]] = defaultdict(list)
    for cid, label in cluster_label.items():
        by_label[label].append(cid)

    rng = random.Random(seed)
    test_clusters: set[int] = set()
    for label, cids in by_label.items():
        cids = sorted(cids)
        rng.shuffle(cids)
        n_test = max(1, round(len(cids) * TEST_FRACTION))
        test_clusters.update(cids[:n_test])

    for row, cid in zip(rows, cluster_of):
        row["split"] = "test" if cid in test_clusters else "train"


def main() -> None:
    rows = list(csv.DictReader(SRC.open(encoding="utf-8")))
    texts = [r["clause_text"] for r in rows]

    rule_ids = rule_based_clusters(texts)
    emb_ids = embedding_clusters(texts)

    for row, rid, eid in zip(rows, rule_ids, emb_ids):
        row["template_id"] = rid
        row["embedding_cluster_id"] = eid

    # Cross-check: for each rule-based cluster, how many distinct embedding clusters does
    # it span? Also verify no rule-based cluster mixes labels or topics (a false merge).
    rule_to_emb = defaultdict(set)
    rule_to_labels = defaultdict(set)
    rule_to_topics = defaultdict(set)
    for row, rid in zip(rows, rule_ids):
        rule_to_emb[rid].add(row["embedding_cluster_id"])
        rule_to_labels[rid].add(row["proposed_label"])
        rule_to_topics[rid].add(row["topic"])
    mismatches = sum(1 for v in rule_to_emb.values() if len(v) > 1)
    false_merges = sum(1 for cid in rule_to_labels if len(rule_to_labels[cid]) > 1 or len(rule_to_topics[cid]) > 1)

    split_by_cluster(rows, rule_ids)

    train_rows = [r for r in rows if r["split"] == "train"]
    test_rows = [r for r in rows if r["split"] == "test"]
    train_templates = {r["template_id"] for r in train_rows}
    test_templates = {r["template_id"] for r in test_rows}

    report = {
        "total_rows": len(rows),
        "n_templates_rule_based": len(set(rule_ids)),
        "n_templates_embedding": len(set(emb_ids)),
        "rule_vs_embedding_mismatches": mismatches,
        "rule_based_false_merges_labels_or_topics": false_merges,
        "train_rows": len(train_rows),
        "test_rows": len(test_rows),
        "train_templates": len(train_templates),
        "test_templates": len(test_templates),
        "leaked_templates_across_split": len(train_templates & test_templates),
        "train_label_dist": dict(Counter(r["proposed_label"] for r in train_rows)),
        "test_label_dist": dict(Counter(r["proposed_label"] for r in test_rows)),
    }

    fieldnames = list(rows[0].keys())
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    OUT_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    print(f"\nWrote {OUT_CSV}\nWrote {OUT_REPORT}")


if __name__ == "__main__":
    main()
