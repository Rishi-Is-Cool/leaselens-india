# LeaseLens — Phase 3 Step 12 Report

## Step 12 — Complete Notice + Rent Escalation Topic Coverage

**Date:** 2026-09-26

### Work completed

Four verified statute records were added to the Phase 3 working master KB:

| ID | Jurisdiction | Provision | Topic | Scope |
|---|---|---|---|---|
| `MH_NOTICE_001` | Maharashtra | Maharashtra Rent Control Act, 1999, s.15(2) | `notice`, `notice_period` | 90-day written demand period before a possession suit on the specified non-payment ground |
| `MH_RENT_001` | Maharashtra | Maharashtra Rent Control Act, 1999, s.11(1) | `rent_escalation` | 4% per annum statutory increase for premises covered by s.2(1) |
| `DL_RENT_001` | Delhi | Delhi Rent Control Act, 1958, s.6A | `rent_escalation` | 10% increase every three years, subject to DRCA applicability |
| `DL_NOTICE_001` | Delhi | Delhi Rent Control Act, 1958, s.8 | `notice`, `notice_period`, `rent_escalation` | 30-day written notice period before a lawful rent increase becomes recoverable |

### Important scope limitation

The new notice entries are deliberately narrow. `MH_NOTICE_001` is **not** a universal 90-day termination notice; it applies to the statutory non-payment-of-rent possession suit in MRCA s.15(2). `DL_NOTICE_001` is **not** a universal one-month tenancy termination rule; it concerns notice of a rent increase under DRCA s.8. General termination notice remains dependent on the applicable contract/local law and, where applicable, Central TPA s.106.

### Working KB/index result

- Working KB: **28 entries** (10 Maharashtra + 11 Delhi + 7 Central).
- Required topic keys now represented in the index: `security_deposit`, `notice`, `eviction`, `maintenance`, `rent_escalation`, `registration`.
- Maharashtra now has `notice` and `rent_escalation` buckets.
- Delhi now has `notice` and `rent_escalation` buckets.
- Central `notice` remains available separately for TPA s.106.

### Retrieval verification

The Step 12 working retrieval checks returned only the expected jurisdiction's new entries for each state/topic query. No Maharashtra query returned a Delhi entry and no Delhi query returned a Maharashtra entry. `last_verified_date` propagated from the KB entry for every new retrieval result.

### Automated test result

The updated Step 12 test run completed:

```text
TOTAL TESTS: 60
PASSED:      60
FAILED:      0
FINAL STATUS: PASS
```

The 16 additional Step 12 assertions cover presence of all four new IDs, topic retrieval, cross-pilot-jurisdiction isolation, and per-entry verification-date propagation.

### Coverage run

The existing mechanically defined coverage script was rerun against the Step 12 KB/index. It reports **10/10 (100.0%) topic-bucket matches** for both Maharashtra and Delhi because the sample's `notice` and `rent_escalation` topics now have indexed entries. This number should be treated as **retrieval/topic-bucket coverage, not a legal-correctness judgment**: the manually written notice samples describe general termination, while the newly added state-specific notice entries cover narrower statutory notice situations.

### Source verification basis

- Maharashtra entries use the official Maharashtra Government Act PDF.
- Delhi entries use the official India Code Delhi Rent Control Act PDF; the exact s.6A/s.8 wording was also cross-checked against a Delhi High Court report reproducing those provisions.

### Remaining Phase 3 blockers

Step 12 does **not** by itself close Phase 3. Remaining closure items are:

1. Confirm final storage implementation against the handoff requirement of Postgres; current working reference remains JSON.
2. Resolve the documented historical `DL_SEC_001`/`DL_SEC_002` ID/content issue if the team requires it before closure.
3. Resolve the duplicate filename/path issue so the automated test always loads the intended master KB/index rather than stale generic filenames.
4. Re-run final verification against the final project files and only then update the project `PROGRESS.md` and make the required final commit.
