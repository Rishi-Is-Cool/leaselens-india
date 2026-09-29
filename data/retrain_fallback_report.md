# Trained-classifier fallback improvement - held-out check

Owner-approved 2026-09-29: all 195 synthetic Indian clauses reviewed, no mislabels; option (b) - train on the 153 train-side rows only first, hold out the 42 test-side rows as a third generalization check, watching obvious-vs-subtle RED recall specifically (every alarm-word phrase in the dataset is RED-only, so a classifier could look accurate by keyword-matching instead of reasoning).

This affects only `classify_clause(text, approach="trained")` - the fallback used when the LLM call fails. `classify_clause()`'s default stays LLM zero-shot regardless of this result.

## Stage 1: held-out check (153 synthetic train rows, 42 held out)

Grouped CV hyper-parameters: C=10.0, class_weight=balanced, cv macro-F1 0.606.

| Model | Test set | n | Accuracy | Macro-F1 |
|---|---|---|---|---|
| Baseline (real data only) | US test (323) | 323 | 65.9% | 0.642 |
| Baseline (real data only) | Indian eval (31) | 31 | 45.2% | 0.401 |
| +153 synthetic (held-out check) | US test (323, unchanged) | 323 | 65.0% | 0.642 |
| +153 synthetic (held-out check) | Indian eval (31, unchanged) | 31 | 58.1% | 0.576 |
| +153 synthetic (held-out check) | Synthetic held-out test (42, NEW) | 42 | 59.5% | 0.557 |

### RED detection on the 42 held-out synthetic clauses, by phrasing type

| RED subtype | n | correctly predicted RED | recall |
|---|---|---|---|
| obvious | 6 | 6 | 100.0% |
| subtle | 6 | 6 | 100.0% |

### Detail

**[baseline, real-data-only] US test (323)** (n=323)

- Accuracy: **65.9%**   Macro-F1: **0.642**
- Confidence: mean 0.64, ECE 0.053 (lower is better calibrated)
- When confidence >= 0.80 (14% of clauses): accuracy 89.1%

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| GREEN | 0.791 | 0.658 | 0.718 | 155 |
| YELLOW | 0.600 | 0.676 | 0.636 | 111 |
| RED | 0.522 | 0.632 | 0.571 | 57 |

Confusion matrix (rows = true, columns = predicted):

| true / pred | GREEN | YELLOW | RED |
|---|---|---|---|
| GREEN | 102 | 37 | 16 |
| YELLOW | 19 | 75 | 17 |
| RED | 8 | 13 | 36 |

**[baseline, real-data-only] Indian eval (31)** (n=31)

- Accuracy: **45.2%**   Macro-F1: **0.401**
- Confidence: mean 0.60, ECE 0.187 (lower is better calibrated)
- When confidence >= 0.80 (13% of clauses): accuracy 75.0%

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| GREEN | 0.550 | 0.611 | 0.579 | 18 |
| YELLOW | 0.143 | 0.111 | 0.125 | 9 |
| RED | 0.500 | 0.500 | 0.500 | 4 |

Confusion matrix (rows = true, columns = predicted):

| true / pred | GREEN | YELLOW | RED |
|---|---|---|---|
| GREEN | 11 | 6 | 1 |
| YELLOW | 7 | 1 | 1 |
| RED | 2 | 0 | 2 |

**[held-out check] US test (323, unchanged)** (n=323)

- Accuracy: **65.0%**   Macro-F1: **0.642**
- Confidence: mean 0.61, ECE 0.040 (lower is better calibrated)
- When confidence >= 0.80 (9% of clauses): accuracy 96.7%

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| GREEN | 0.752 | 0.626 | 0.683 | 155 |
| YELLOW | 0.597 | 0.667 | 0.630 | 111 |
| RED | 0.557 | 0.684 | 0.614 | 57 |

Confusion matrix (rows = true, columns = predicted):

| true / pred | GREEN | YELLOW | RED |
|---|---|---|---|
| GREEN | 97 | 42 | 16 |
| YELLOW | 22 | 74 | 15 |
| RED | 10 | 8 | 39 |

**[held-out check] Indian eval (31, unchanged)** (n=31)

- Accuracy: **58.1%**   Macro-F1: **0.576**
- Confidence: mean 0.56, ECE 0.127 (lower is better calibrated)

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| GREEN | 0.733 | 0.611 | 0.667 | 18 |
| YELLOW | 0.333 | 0.333 | 0.333 | 9 |
| RED | 0.571 | 1.000 | 0.727 | 4 |

Confusion matrix (rows = true, columns = predicted):

| true / pred | GREEN | YELLOW | RED |
|---|---|---|---|
| GREEN | 11 | 6 | 1 |
| YELLOW | 4 | 3 | 2 |
| RED | 0 | 0 | 4 |

**[held-out check] Synthetic held-out test (42, NEW)** (n=42)

- Accuracy: **59.5%**   Macro-F1: **0.557**
- Confidence: mean 0.54, ECE 0.145 (lower is better calibrated)
- When confidence >= 0.80 (7% of clauses): accuracy 100.0%

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| GREEN | 0.625 | 0.667 | 0.645 | 15 |
| YELLOW | 0.600 | 0.200 | 0.300 | 15 |
| RED | 0.571 | 1.000 | 0.727 | 12 |

Confusion matrix (rows = true, columns = predicted):

| true / pred | GREEN | YELLOW | RED |
|---|---|---|---|
| GREEN | 10 | 2 | 3 |
| YELLOW | 6 | 3 | 6 |
| RED | 0 | 0 | 12 |

## Stage 2: final fit shipped (all 195 synthetic + original US train)

Grouped CV hyper-parameters: C=10.0, class_weight=balanced, cv macro-F1 0.595. This is the model saved to `backend\app\classifier\artifacts\risk_logreg.joblib` and used by `approach="trained"`.

**The 42 synthetic held-out rows are part of this model's training data and are deliberately NOT re-reported here** - the Stage 1 numbers above are the valid evidence of generalization to synthetic material; re-testing this model on rows it was trained on would be circular.

| Test set | n | Accuracy | Macro-F1 |
|---|---|---|
| US test (323, unchanged) | 323 | 64.7% | 0.640 |
| Indian eval (31, unchanged) | 31 | 54.8% | 0.537 |

### Detail

**[SHIPPED, refit on all 195] US test (323, unchanged)** (n=323)

- Accuracy: **64.7%**   Macro-F1: **0.640**
- Confidence: mean 0.61, ECE 0.050 (lower is better calibrated)
- When confidence >= 0.80 (10% of clauses): accuracy 93.5%

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| GREEN | 0.746 | 0.626 | 0.681 | 155 |
| YELLOW | 0.593 | 0.658 | 0.624 | 111 |
| RED | 0.557 | 0.684 | 0.614 | 57 |

Confusion matrix (rows = true, columns = predicted):

| true / pred | GREEN | YELLOW | RED |
|---|---|---|---|
| GREEN | 97 | 42 | 16 |
| YELLOW | 23 | 73 | 15 |
| RED | 10 | 8 | 39 |

**[SHIPPED, refit on all 195] Indian eval (31, unchanged)** (n=31)

- Accuracy: **54.8%**   Macro-F1: **0.537**
- Confidence: mean 0.57, ECE 0.117 (lower is better calibrated)

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| GREEN | 0.688 | 0.611 | 0.647 | 18 |
| YELLOW | 0.250 | 0.222 | 0.235 | 9 |
| RED | 0.571 | 1.000 | 0.727 | 4 |

Confusion matrix (rows = true, columns = predicted):

| true / pred | GREEN | YELLOW | RED |
|---|---|---|---|
| GREEN | 11 | 6 | 1 |
| YELLOW | 5 | 2 | 2 |
| RED | 0 | 0 | 4 |
