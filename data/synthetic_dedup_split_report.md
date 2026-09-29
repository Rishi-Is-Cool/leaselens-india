# Synthetic Indian clauses — dedup & leak-free split

**Input:** `data/synthetic_indian_clauses.csv` — 195 generated clauses (Step 1 of the
trained-classifier fallback improvement work).

## Problem

The 195 clauses are built from 47 underlying templates (`backend/scripts/
generate_synthetic_indian_clauses.py`), each cloned across 2-5 states with only
party-name, property-term, and (for RED clauses) obvious/subtle wording varied. Splitting
this file at the row level, or even by treating each state-variant as a separate
"document", would not prevent leakage: a template's state-variants are near-duplicates of
each other, and having one land in train and another in test would inflate test accuracy
without testing real generalization.

## Method

1. **Rule-based clustering.** Normalize party terms (Licensee/Tenant/Lessee →
   `PARTY_A`, etc.), property references, and amounts to placeholders, then exact-match
   the normalized text.
2. **Embedding cross-check.** Cosine similarity ≥ 0.95 on `all-MiniLM-L6-v2`, as an
   independent second method.
3. Split at the **cluster level** (not row, not just document), stratified by label,
   75/25 train/test.
4. Verify no cluster appears on both sides.

## Result

| | rows | templates | GREEN | YELLOW | RED |
|---|---|---|---|---|---|
| train | 153 | 36 | 50 | 50 | 53 |
| test | 42 | 11 | 15 | 15 | 12 |

**0 of 47 templates appear on both sides.** Label balance holds on both sides
(~34/33/33% and ~36/36/29%).

## The cross-check disagreed — here's what that means

The rule-based method found 47 clusters; the embedding method found 141, and 43 of the 47
rule-based clusters span more than one embedding cluster. That sounds like the rule-based
clustering might be wrong (under-merging real duplicates, or over-merging distinct
clauses). It's neither. Direct inspection resolves it:

- **Every rule-based cluster contains exactly one topic and one label** (checked
  programmatically — 0 false merges). So the rule-based method never wrongly combined two
  different clauses.
- **Cluster sizes exactly match the generator's own template structure**: 8 clusters of
  size 2, 8 of size 3, 31 of size 5 (47 total) — precisely the RED obvious/subtle
  state-split (2s and 3s) plus the GREEN/YELLOW/round-2 bodies applied to all 5 states
  (5s). This is independent confirmation the rule-based grouping recovered the true
  generative structure, because that structure was known in advance from how the data was
  built.
- Manually reading a size-5 cluster (e.g. the security-deposit GREEN template) confirms
  all 5 rows are the same clause with only the actor nouns and property term swapped —
  genuinely one template, exactly as the rule-based method says.

So why does the embedding method disagree? Because MiniLM's cosine similarity is
sensitive to the specific actor noun used — "Licensee" vs "Tenant" vs "Lessee" register as
different enough that cosine similarity for otherwise-identical sentences often falls
below 0.95, splitting genuine duplicates apart. This is a known limitation of a fixed
similarity threshold applied to *mechanically substituted* near-duplicates (as opposed to
naturally-occurring paraphrases, which is what 0.95 was originally tuned for on the real
1,682-clause dataset — see `data/classifier_eval.md`). **For this dataset, the rule-based
clustering is the one to trust, and the embedding cross-check — now actually run, closing
the gap the first pass of this analysis flagged — does not overturn it.**

## Files

- `data/synthetic_indian_clauses_with_split.csv` — the 195 rows plus `template_id`,
  `embedding_cluster_id`, and `split` (train/test) columns. Filter on `split` for
  training; don't re-split this file yourself.
- `backend/scripts/dedup_and_split_synthetic.py` — re-runnable; regenerates both output
  files from `data/synthetic_indian_clauses.csv`.
- `data/synthetic_dedup_split_report.json` — the numbers above, machine-readable.

## What this changes for Step 3 (retraining)

This reveals that "add all 195 synthetic clauses to training" (as originally scoped)
would train on 47 real templates repeated 2-5x each, not 195 independent examples — a
mild redundancy, not a leakage risk against the existing US test (323) or Indian eval (31)
sets, since neither of those shares any template with this file. But it also means a
**third, honest check is now available for free**: train on the original US split plus
only the 153 *train*-side synthetic rows, then also evaluate on the 42 *test*-side
synthetic rows the model never saw a template of. That measures generalization to unseen
synthetic templates specifically, which "add all 195 to training" cannot measure. This
is an addition to the plan, not what was originally asked for — flagged for a decision
before retraining, not applied silently.
