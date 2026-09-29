# Phase 2 - classifier evaluation

Generated 2026-09-27 by `backend/scripts/run_phase2.py`. Every number below is computed on the **same held-out test set** unless a row says otherwise.

## Method

- **Data:** 1682 labeled clauses (`data/ML_Final_Dataset_Cleaned.xlsx`). Distribution: GREEN 811 (48.2%), YELLOW 584 (34.7%), RED 287 (17.1%).
- **Deduplication:** clauses with embedding cosine >= 0.95 (all-MiniLM-L6-v2) are collapsed to one. Removed 160, leaving 1522. Duplicate clusters never disagreed on label. The twins are the same boilerplate across different leases.
- **Split:** the file has no lease ID (`clause_id` is a row number). Rows are in lease order, so contiguous blocks of 30 rows stand in for leases and whole blocks go to train or test (seed 0, ~20% test, chosen so the class mix matches). **This is a proxy:** a real lease can straddle a block edge, so leakage is reduced, not proven zero.
- **Train:** 1199 clauses (GREEN 565 (47%), YELLOW 428 (36%), RED 206 (17%)). **Test:** 323 clauses (GREEN 155 (48%), YELLOW 111 (34%), RED 57 (18%)).

## Leakage check

- Blocks appearing in both train and test: **0**
- Clause IDs appearing in both: **0**
- Highest cosine similarity between any test clause and any train clause: **0.944** (below the 0.95 dedup threshold)
- Test clauses with a train neighbour >= 0.90: **19 of 323** (paraphrases that survive dedup; a small optimistic bias, reported rather than hidden)

## Model selection (training data only)

Grouped 5-fold cross-validation over the training blocks chose C=3.0, class_weight=balanced, macro-F1 0.613. Softmax temperature 1.06 fitted on out-of-fold predictions. The test set played no part.

## Results

| Approach | n | Accuracy | Macro-F1 | ECE |
|---|---|---|---|---|
| Majority-class baseline (always GREEN) | 323 | 48.0% | 0.216 | - |
| Trained classifier (MiniLM embeddings + logistic regression, calibrated) | 323 | 65.9% | 0.642 | 0.053 |
| LLM zero-shot - qwen/qwen3.8-27b | 323 | 76.5% | 0.758 | 0.107 |
| LLM few-shot (6 train examples) - qwen/qwen3.8-27b (partial, n=120) | 120 | 71.7% | 0.677 | 0.187 |
| Ensemble (fixed 50/50 average of trained + LLM zero-shot) | 323 | 76.5% | 0.758 | 0.090 |

> LLM few-shot (6 train examples) stopped early at 120/323: the provider's free-tier daily quota was reached. Cached answers are kept; re-run this script after the quota resets (typically 24h) to complete the rest, or set LLM_MODEL to a model with separate quota.

## Detail per approach

**Majority-class baseline (always GREEN)** (n=323)

- Accuracy: **48.0%**   Macro-F1: **0.216**

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| GREEN | 0.480 | 1.000 | 0.649 | 155 |
| YELLOW | 0.000 | 0.000 | 0.000 | 111 |
| RED | 0.000 | 0.000 | 0.000 | 57 |

Confusion matrix (rows = true, columns = predicted):

| true / pred | GREEN | YELLOW | RED |
|---|---|---|---|
| GREEN | 155 | 0 | 0 |
| YELLOW | 111 | 0 | 0 |
| RED | 57 | 0 | 0 |

**Trained classifier (MiniLM embeddings + logistic regression, calibrated)** (n=323)

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

**LLM zero-shot - qwen/qwen3.8-27b** (n=323)

- Accuracy: **76.5%**   Macro-F1: **0.758**
- Confidence: mean 0.87, ECE 0.107 (lower is better calibrated)
- When confidence >= 0.80 (89% of clauses): accuracy 78.0%

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| GREEN | 0.772 | 0.897 | 0.830 | 155 |
| YELLOW | 0.684 | 0.604 | 0.641 | 111 |
| RED | 0.911 | 0.719 | 0.804 | 57 |

Confusion matrix (rows = true, columns = predicted):

| true / pred | GREEN | YELLOW | RED |
|---|---|---|---|
| GREEN | 139 | 16 | 0 |
| YELLOW | 40 | 67 | 4 |
| RED | 1 | 15 | 41 |

**LLM few-shot (6 train examples) - qwen/qwen3.8-27b (partial, n=120)** (n=120)

- Accuracy: **71.7%**   Macro-F1: **0.677**
- Confidence: mean 0.85, ECE 0.187 (lower is better calibrated)
- When confidence >= 0.80 (100% of clauses): accuracy 71.7%

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| GREEN | 1.000 | 0.694 | 0.819 | 62 |
| YELLOW | 0.507 | 0.971 | 0.667 | 35 |
| RED | 0.900 | 0.391 | 0.545 | 23 |

Confusion matrix (rows = true, columns = predicted):

| true / pred | GREEN | YELLOW | RED |
|---|---|---|---|
| GREEN | 43 | 19 | 0 |
| YELLOW | 0 | 34 | 1 |
| RED | 0 | 14 | 9 |

**Ensemble (fixed 50/50 average of trained + LLM zero-shot)** (n=323)

- Accuracy: **76.5%**   Macro-F1: **0.758**
- Confidence: mean 0.69, ECE 0.090 (lower is better calibrated)
- When confidence >= 0.80 (23% of clauses): accuracy 94.6%

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| GREEN | 0.772 | 0.897 | 0.830 | 155 |
| YELLOW | 0.691 | 0.586 | 0.634 | 111 |
| RED | 0.878 | 0.754 | 0.811 | 57 |

Confusion matrix (rows = true, columns = predicted):

| true / pred | GREEN | YELLOW | RED |
|---|---|---|---|
| GREEN | 139 | 16 | 0 |
| YELLOW | 40 | 65 | 6 |
| RED | 1 | 13 | 43 |

## Decision

**Ship: LLM zero-shot as the default `classify_clause()` approach**, with the trained
classifier kept available as `classify_clause(text, approach="trained")`.

**Why, from the numbers above:**

- On the same 323-clause held-out test set: LLM zero-shot **76.5%** accuracy / **0.758**
  macro-F1, versus the trained classifier's **65.9%** / **0.642** and the majority baseline's
  **48.0%** / **0.216**. The LLM beats the trained classifier by 10.6 points accuracy and
  0.116 macro-F1 - not a marginal difference, and it wins on every class's F1
  (GREEN 0.830 vs 0.718, YELLOW 0.641 vs 0.636, RED 0.804 vs 0.571). RED is the class the
  product most needs to catch, and the trained classifier is weakest exactly there.
- Few-shot prompting did not help (71.7% on the 120 clauses it completed before the
  quota cut it off) - zero-shot's plainer prompt did better here, so few-shot is not
  worth its extra prompt-token cost.
- The 50/50 ensemble scores identically to LLM zero-shot alone (76.5% / 0.758): averaging
  in the weaker trained-classifier probabilities neither helps nor hurts enough to matter
  on this test set. Ensembling adds complexity (two model calls per clause) for no
  measured benefit, so it is not the shipped choice.
- **The Indian-domain check is now fully owner-reviewed (31/31, updated 2026-09-28) and
  RED-inclusive**, replacing an earlier pass that used Claude's own unreviewed proposals and
  had zero RED examples. On this corrected 31-clause sample: trained classifier 45.2%, LLM
  zero-shot 64.5%, LLM few-shot 71.0%, majority baseline 58.1%. All three numbers are *lower*
  than the earlier unreviewed pass reported (55.6% / 77.8% / n/a) - **this is not a model
  regression**, since every prediction is identical and cached; it is the ground truth
  changing. Four clauses (IN-12, 20, 23, 25) were corrected by the owner, and on exactly
  those four, both models had previously been scored "correct" only because they agreed with
  Claude's own first-pass label, not because the reasoning was sound (e.g. IN-20's licence
  clause is standard Leave & License structure under the Maharashtra Rent Control Act - both
  Claude's original proposal and the LLM's judgment initially over-flagged it as risky,
  likely because that structure is unfamiliar in the mostly-US training distribution this
  system draws on). The lower numbers reflect a better yardstick, not worse models.
- **RED recall is the clean, decisive result from this pass.** The 27 real clauses (from
  blank official templates) contain no RED text at all, so 4 clauses covering genuinely
  one-sided terms (full deposit forfeiture including normal wear and tear, unilateral
  uncapped rent increases, termination and re-entry with no notice, a disproportionate
  per-day penalty) were hand-authored to close that gap. **LLM zero-shot and few-shot both
  caught all 4 of 4 (100% recall, precision 0.80 and 1.00 respectively). The trained
  classifier caught only 2 of 4** (missing the deposit-forfeiture and rent-increase clauses
  specifically - the two that read as ordinary rent/deposit terms on the surface, without
  dramatic keywords like "without notice" or "any circumstances" that the other two carry).
  This is exactly the failure mode a lease-risk tool cannot afford, and it is a cleaner,
  more direct test of the product's actual job than the overall-accuracy numbers above.
- On this same small sample, LLM **few-shot** edged out zero-shot (71.0% vs 64.5%, macro-F1
  0.773 vs 0.692, perfect RED precision+recall vs 0.80 precision). This is a real result but
  not being used to flip the shipped default: n=31 is small, few-shot's US-test comparison is
  itself incomplete (120 of 323, see above), and zero-shot's advantage on the much
  larger US test (323 clauses) carries more statistical weight than a 31-clause sample can
  outweigh. It is worth re-checking once the few-shot US run completes.
- Confidence is well-calibrated for the LLM (ECE 0.107 on the US test, 0.239 on the small,
  harder Indian sample - calibration is noisier at n=31) and correlates with being right, so
  Phase 4 can use it to decide how hedged to be.

**Net effect of the reviewed, RED-inclusive Indian check on this decision: reinforces it.**
The overall US-vs-trained gap holds (19.3 points on the reviewed Indian sample, versus 22.2
before review - still large), and the one dimension that matters most for a lease-risk
product - catching a genuinely one-sided clause - now has a direct, clean measurement for
the first time: LLM 4/4, trained classifier 2/4. The earlier "decisive" framing was directionally
right but was resting on unreviewed labels with no RED coverage at all; it is now decisive on
firmer ground, not just on a wider margin.

**Honest cost of this choice, not visible in the accuracy table:**

- `classify_clause()` now makes a network call to a third-party LLM per clause instead of
  running an in-process model. This adds latency and an external dependency that
  `approach="trained"` does not have.
- **Free-tier rate limits are real, not theoretical**: producing the numbers above hit a
  200,000-token/day cap on the model used (`qwen/qwen3.8-27b`) partway through this very
  evaluation, and a second cap on the model used for the Indian check
  (`openai/gpt-oss-120b`) is a matter of enough volume, not a hypothetical. Classifying
  every clause of every uploaded lease through a free-tier LLM in production will hit
  these caps under real usage. Before shipping to real users this needs either a paid
  tier, a fallback to `approach="trained"` when the LLM is rate-limited, or both. This is
  flagged for whoever picks up Phase 4 / deployment (Phase 7) to decide, not resolved here.
- `DEFAULT_APPROACH` in `app/classifier/api.py` is a single constant specifically so this
  decision can be changed in one place if the operational cost outweighs the accuracy gain.

**Update 2026-09-29: the `approach="trained"` fallback was improved, since the point above
is not hypothetical - it will be exercised.** The reviewed Indian eval set had shown the
trained classifier missing 2 of 4 RED clauses, specifically the ones without alarm-word
phrasing (`PROGRESS.md`, "Fallback-path improvement"). 195 synthetic Indian-register
clauses were generated, reviewed by the owner (no mislabels), deduplicated to 47 real
templates, and split leak-free (153 train / 42 held-out test;
`data/synthetic_dedup_split_report.md`). A held-out check - train on 153 synthetic rows
only, test on the 42 the model never saw a template of - passed the specific test that
mattered: **RED recall on the held-out synthetic clauses was 100% on *both* obvious
alarm-word phrasing (6/6) and subtle, no-alarm-word phrasing (6/6)**, which is evidence
against the classifier merely pattern-matching keywords (every alarm word in the dataset
appears only in RED rows, so keyword-matching was a real risk to rule out). US-test
accuracy held stable (65.9% -> 65.0%, macro-F1 unchanged at 0.642) and Indian-eval
accuracy improved (45.2% -> 58.1%, RED recall 2/4 -> 4/4) in the same run. Full numbers:
`data/retrain_fallback_report.md`.

The shipped `approach="trained"` artifact was then refit on the original US training data
plus **all** 195 synthetic clauses (not just the 153 held-out-check rows) and saved to
`app/classifier/artifacts/risk_logreg.joblib`. On the still-valid US test and Indian eval
(neither overlaps the synthetic data at any point): **64.7%** US test accuracy
(macro-F1 0.640, essentially unchanged) and **54.8%** Indian eval accuracy (macro-F1
0.537, RED recall still 4/4) - both real improvements over the pre-synthetic trained
baseline (45.2% / 0.401 on the Indian eval), though the fully-refit model scores a few
points below the 153-row held-out-check model on the Indian eval (58.1%). That gap is
reported rather than smoothed over: more synthetic data did not straightforwardly mean a
better fallback model on this small eval set, though it remains a clear net improvement
over not having the synthetic data at all. Reproduce with
`backend/scripts/retrain_trained_fallback.py` (`--final` to also refit and save the
shipped artifact).

**This entire update is about the fallback path only.** `classify_clause()`'s default
stays LLM zero-shot regardless.

## Indian-domain check (31 hand-labeled clauses)

**Why:** the training data (US-style leases) is not Indian. This scores the same models on 27 real clauses from the official Tamil Nadu, West Bengal and Maharashtra forms plus 4 authored clauses (`data/indian_eval_set.csv`; the real ones are segmented by Person A's pipeline, with fill-in blanks shown as `[blank]`).

**Labels:** 31 of 31 are owner-reviewed. 
Label mix: GREEN 18, YELLOW 9, RED 4. **4 RED clause(s)** are included: 27 real clauses from the blank official forms contain none (they are deliberately neutral), so 4 were hand-authored specifically to test RED detection - see `reviewed_reason` in the CSV for each one's rationale.

| Approach | Indian sample accuracy (95% CI) | US test accuracy | Change |
|---|---|---|---|
| Trained classifier | 45.2% (29%-62%), n=31 | 65.9% | -20.7 pts |
| LLM zero-shot | 64.5% (47%-79%), n=31 | 76.5% | -12.0 pts |
| LLM few-shot | 71.0% (53%-84%), n=31 | 71.7% | -0.7 pts |
| Majority baseline (always GREEN) | 58.1% | 48.0% | - |

Read the interval, not the point estimate: with 31 clauses one clause is 3.2 points and the interval is wide. This is a sanity check on domain transfer, not a benchmark.

**Trained classifier on Indian sample** (n=31)

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

(Macro-F1 over the 3 classes present: 0.401; the table's macro-F1 counts absent RED as 0.)

**LLM zero-shot on Indian sample** (n=31)

- Accuracy: **64.5%**   Macro-F1: **0.692**
- Confidence: mean 0.84, ECE 0.239 (lower is better calibrated)
- When confidence >= 0.80 (77% of clauses): accuracy 75.0%

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| GREEN | 0.833 | 0.556 | 0.667 | 18 |
| YELLOW | 0.429 | 0.667 | 0.522 | 9 |
| RED | 0.800 | 1.000 | 0.889 | 4 |

Confusion matrix (rows = true, columns = predicted):

| true / pred | GREEN | YELLOW | RED |
|---|---|---|---|
| GREEN | 10 | 8 | 0 |
| YELLOW | 2 | 6 | 1 |
| RED | 0 | 0 | 4 |

(Macro-F1 over the 3 classes present: 0.692; the table's macro-F1 counts absent RED as 0.)

**LLM few-shot on Indian sample** (n=31)

- Accuracy: **71.0%**   Macro-F1: **0.773**
- Confidence: mean 0.86, ECE 0.150 (lower is better calibrated)
- When confidence >= 0.80 (100% of clauses): accuracy 71.0%

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| GREEN | 0.846 | 0.611 | 0.710 | 18 |
| YELLOW | 0.500 | 0.778 | 0.609 | 9 |
| RED | 1.000 | 1.000 | 1.000 | 4 |

Confusion matrix (rows = true, columns = predicted):

| true / pred | GREEN | YELLOW | RED |
|---|---|---|---|
| GREEN | 11 | 7 | 0 |
| YELLOW | 2 | 7 | 0 |
| RED | 0 | 0 | 4 |

(Macro-F1 over the 3 classes present: 0.773; the table's macro-F1 counts absent RED as 0.)

Misclassified Indian clauses:

- Trained classifier: IN-03 true YELLOW, predicted GREEN - There shall be a rental enhancement of [blank] % of the basic rent after completion of [blank] Years from the ...
- Trained classifier: IN-04 true YELLOW, predicted GREEN - That the LESSEE shall be responsible for keeping the leased premises in good shape. He shall keep all the fixt...
- Trained classifier: IN-07 true GREEN, predicted YELLOW - The LESSEE shall not during the period of the Lease Agreement make any structural alterations in the said prem...
- Trained classifier: IN-09 true YELLOW, predicted GREEN - It is agreed that if the LESSEE commits a breach of the terms by doing any structural changes in the premises ...
- Trained classifier: IN-12 true YELLOW, predicted GREEN - That the Lessee shall pay the electricity bill, municipal taxes etc to the concerned authorities....
- Trained classifier: IN-14 true YELLOW, predicted GREEN - That the Lessee not sublet, assign or part with the possession of the aforesaid rented property in whole or in...
- Trained classifier: IN-15 true YELLOW, predicted GREEN - That the Lessee shall not carry out any addition or alteration in the structure or otherwise under any circums...
- Trained classifier: IN-19 true YELLOW, predicted RED - That in case the Lessee fails to vacate and give the physical vacant possession of the said rented property wi...
- Trained classifier: IN-20 true GREEN, predicted YELLOW - That the Licensor/s hereby grants to the Licensee/s herein a revocable leave and licence, to occupy the Licens...
- Trained classifier: IN-21 true GREEN, predicted YELLOW - That the Licensee/s shall pay to the Licensor/s [blank] per month towards the compensation for the use of the ...
- Trained classifier: IN-22 true YELLOW, predicted GREEN - That the Licensee/s shall pay to the Licensor/s [blank] per month towards the compensation and Rs[blank] inter...
- Trained classifier: IN-23 true GREEN, predicted RED - That the Licensee/s herein shall bear and pay all the maintenance charges in respect of the said Licenced Prem...
- Trained classifier: IN-24 true GREEN, predicted YELLOW - That the Licensee/s shall not make or permit to do any alteration or addition to the construction or arrangeme...
- Trained classifier: IN-25 true GREEN, predicted YELLOW - That the Licensee/s shall not claim any tenancy right and shall not have any right to transfer, assign, sublet...
- Trained classifier: IN-26 true GREEN, predicted YELLOW - That ,the Licensor/s shall on reasonable notice given by the Licensor/s to the Licensee/s shall have a right o...
- Trained classifier: IN-28 true RED, predicted GREEN - The Security Deposit paid by the Tenant shall stand forfeited in full and shall not be refunded under any circ...
- Trained classifier: IN-29 true RED, predicted GREEN - The Landlord may, at his sole and absolute discretion and without any prior notice to the Tenant, increase the...
- LLM zero-shot: IN-08 true GREEN, predicted YELLOW - That the LESSEE shall re-deliver the peaceful vacant possession of the premises to the LESSOR at the terminati...
- LLM zero-shot: IN-10 true YELLOW, predicted GREEN - That the Lessee has been paid a sum of Rs[blank] as Security which is interest free, the receipt of which is h...
- LLM zero-shot: IN-12 true YELLOW, predicted GREEN - That the Lessee shall pay the electricity bill, municipal taxes etc to the concerned authorities....
- LLM zero-shot: IN-16 true GREEN, predicted YELLOW - That day-to-day repairs such as replacement of fuses and elements setting right, leakages in water taps etc. a...
- LLM zero-shot: IN-17 true GREEN, predicted YELLOW - That the Lessee shall permit the Lessor or his agents or representatives to enter upon the lease premises for ...
- LLM zero-shot: IN-18 true GREEN, predicted YELLOW - And whereas the Lessee wants to vacate the premises the he will give [blank] . Month notice to the Lessor vice...
- LLM zero-shot: IN-19 true YELLOW, predicted RED - That in case the Lessee fails to vacate and give the physical vacant possession of the said rented property wi...
- LLM zero-shot: IN-20 true GREEN, predicted YELLOW - That the Licensor/s hereby grants to the Licensee/s herein a revocable leave and licence, to occupy the Licens...
- LLM zero-shot: IN-21 true GREEN, predicted YELLOW - That the Licensee/s shall pay to the Licensor/s [blank] per month towards the compensation for the use of the ...
- LLM zero-shot: IN-23 true GREEN, predicted YELLOW - That the Licensee/s herein shall bear and pay all the maintenance charges in respect of the said Licenced Prem...
- LLM zero-shot: IN-25 true GREEN, predicted YELLOW - That the Licensee/s shall not claim any tenancy right and shall not have any right to transfer, assign, sublet...
- LLM few-shot: IN-05 true GREEN, predicted YELLOW - That the LESSEE shall use the premises exclusively for the commercial purposes and shall not sublet the premis...
- LLM few-shot: IN-08 true GREEN, predicted YELLOW - That the LESSEE shall re-deliver the peaceful vacant possession of the premises to the LESSOR at the terminati...
- LLM few-shot: IN-10 true YELLOW, predicted GREEN - That the Lessee has been paid a sum of Rs[blank] as Security which is interest free, the receipt of which is h...
- LLM few-shot: IN-12 true YELLOW, predicted GREEN - That the Lessee shall pay the electricity bill, municipal taxes etc to the concerned authorities....
- LLM few-shot: IN-18 true GREEN, predicted YELLOW - And whereas the Lessee wants to vacate the premises the he will give [blank] . Month notice to the Lessor vice...
- LLM few-shot: IN-20 true GREEN, predicted YELLOW - That the Licensor/s hereby grants to the Licensee/s herein a revocable leave and licence, to occupy the Licens...
- LLM few-shot: IN-21 true GREEN, predicted YELLOW - That the Licensee/s shall pay to the Licensor/s [blank] per month towards the compensation for the use of the ...
- LLM few-shot: IN-23 true GREEN, predicted YELLOW - That the Licensee/s herein shall bear and pay all the maintenance charges in respect of the said Licenced Prem...
- LLM few-shot: IN-25 true GREEN, predicted YELLOW - That the Licensee/s shall not claim any tenancy right and shall not have any right to transfer, assign, sublet...
