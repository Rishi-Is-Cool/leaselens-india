"""Loader for the labeled clause dataset, with validation.

The file carries no lease identifier: `clause_id` is a global row number (1..N), not a
document key. Anything that needs document grouping must derive it separately.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import openpyxl

DATASET_PATH = Path(__file__).resolve().parents[3] / "data" / "ML_Final_Dataset_Cleaned.xlsx"
LABELS = ("GREEN", "YELLOW", "RED")
REQUIRED_COLUMNS = ("clause_id", "clause_text", "risk_label")


@dataclass(frozen=True)
class LabeledClause:
    clause_id: int
    text: str
    label: str


def load_dataset(path: Path = DATASET_PATH) -> list[LabeledClause]:
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    rows = workbook.active.iter_rows(values_only=True)
    header = [str(c).strip() if c is not None else "" for c in next(rows)]
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        raise ValueError(f"Dataset is missing columns: {missing}")
    index = {name: header.index(name) for name in REQUIRED_COLUMNS}

    clauses: list[LabeledClause] = []
    for line, row in enumerate(rows, start=2):
        if row is None or all(c is None for c in row):
            continue
        text = str(row[index["clause_text"]] or "").strip()
        label = str(row[index["risk_label"]] or "").strip().upper()
        if not text:
            raise ValueError(f"Row {line}: empty clause_text")
        if label not in LABELS:
            raise ValueError(f"Row {line}: unknown risk_label {label!r}")
        clauses.append(LabeledClause(int(row[index["clause_id"]]), text, label))

    if len({c.clause_id for c in clauses}) != len(clauses):
        raise ValueError("clause_id values are not unique")
    return clauses


def class_balance(clauses: list[LabeledClause]) -> dict[str, tuple[int, float]]:
    counts = Counter(c.label for c in clauses)
    return {label: (counts[label], counts[label] / len(clauses)) for label in LABELS}
