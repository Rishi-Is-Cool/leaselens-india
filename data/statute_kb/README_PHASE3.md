# LeaseLens — Phase 3 Clean Package

## Canonical final artifacts
- `kb/leaselens_statute_kb.json` — Step-12 master corpus (28 entries)
- `kb/leaselens_statute_index.json` — Step-12 master retrieval index
- `src/statute_retrieval.py` — reference retrieval implementation
- `src/phase3_postgres_retrieval.py` — PostgreSQL retrieval adapter
- `database/phase3_statute_schema.sql` — PostgreSQL schema
- `database/phase3_postgres_migrate.py` — PostgreSQL migration script
- `tests/test_phase3_retrieval.py` — Step-12 retrieval/traceability tests
- `tests/phase3_coverage_test.py` — coverage test
- `reports/` — verification and coverage reports

## Cleanup policy
Older/duplicate KB and index JSON files are not treated as canonical and are not copied into `kb/`.
Individual statute/source artifacts are retained under `audit_sources/` for traceability.
`PROGRESS.md` is finalized for this clean package after the final verification run. It records the 28-entry corpus, test results, coverage, PostgreSQL verification, and the documented ephemeral-Colab limitation.

## PostgreSQL verification performed in Colab
- 28 rows loaded into `statute_entries`
- Maharashtra: 12
- Delhi: 9
- Central: 7
- Jurisdiction isolation test: PASS
- PostgreSQL evidence traceability test: PASS

## Final verification
- Retrieval suite: 60/60 PASS.
- Coverage suite: PASS; 10/10 representative clauses matched for Maharashtra and Delhi under default retrieval.
- PostgreSQL: verified in temporary Google Colab (28 rows; 12/9/7 counts; isolation and evidence traceability PASS).
- See `reports/phase3_final_verification.md` and `PROGRESS.md`.
