from app.classifier.dataset import LABELS, class_balance, load_dataset


def test_dataset_loads_and_validates():
    clauses = load_dataset()
    assert len(clauses) == 1682
    assert {c.label for c in clauses} == set(LABELS)
    assert len({c.clause_id for c in clauses}) == len(clauses)


def test_class_balance_matches_the_audit():
    balance = class_balance(load_dataset())
    assert [balance[label][0] for label in LABELS] == [811, 584, 287]
