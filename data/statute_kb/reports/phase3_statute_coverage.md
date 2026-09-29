# LeaseLens — Phase 3 Statute Coverage Report

Date: 2026-09-26

## Coverage result

The Phase-1 lease-clause pipeline is not wired into this Phase-3 package, so coverage is measured using the committed manual representative clause set in `tests/phase3_coverage_test.py`.

| Jurisdiction | Default retrieval (`include_central=False`) | Central-enabled retrieval |
|---|---:|---:|
| Maharashtra | 10/10 = **100.0%** | 10/10 = **100.0%** |
| Delhi | 10/10 = **100.0%** | 10/10 = **100.0%** |

A clause is counted as matched when retrieval returns at least one entry for the clause's stated jurisdiction and topic bucket.

## Important interpretation

These percentages are **manual topic-bucket retrieval coverage**, not a claim that every possible rental clause is legally covered or that every returned statute is applicable to every factual situation. In particular, notice coverage includes narrow statutory notice rules; it should not be interpreted as a universal lease-termination notice rule.

Central-enabled results are reported separately because Central law is explicitly opt-in in the retrieval policy. The default pilot-jurisdiction result is therefore the primary Phase-3 coverage figure.

## Verification

The coverage script was rerun against the canonical clean-package KB/index after the path cleanup and completed successfully for all 20 representative clauses.
