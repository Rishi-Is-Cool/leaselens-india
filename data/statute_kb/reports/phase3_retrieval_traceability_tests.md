# Phase 3 Retrieval & Citation Traceability Test Report

## 1. Test Environment

- **KB file:** `leaselens_statute_kb.json` (24 entries: 10 Maharashtra, 7 Delhi, 7 Central)
- **Index file:** `leaselens_statute_index.json`
- **Retrieval implementation:** `src/statute_retrieval.py` — deterministic keyword/topic reference implementation, NOT a production embedding/semantic-search system
- **Test file:** `tests/test_phase3_retrieval.py` — plain Python assertions, run with `python3 test_phase3_retrieval.py`, no internet or external dependencies required
- **Date executed:** 2026-09-26
- **Retrieval method:** jurisdiction filter → topic filter (both via the master index, applied *before* any scoring) → keyword-overlap relevance scoring within the already-filtered candidate set only

All results below are copied directly from an actual run of the test file (35/35 assertions), not asserted from design intent.

---

## 2. Retrieval Tests

| Test | Jurisdiction | Topic | Expected Entries | Returned Entries | Result |
|---|---|---|---|---|---|
| TEST01 | Maharashtra | security_deposit | {MH_SEC_001} | {MH_SEC_001} | PASS |
| TEST02 | Maharashtra | registration | {MH_REG_001} | {MH_REG_001} | PASS |
| TEST03 | Maharashtra | eviction | {MH_EVICTION_001–005, MH_LICENCE_001} | {MH_EVICTION_001–005, MH_LICENCE_001} | PASS |
| TEST04 | Maharashtra | maintenance | {MH_MAINT_001, MH_MAINT_002} | {MH_MAINT_001, MH_MAINT_002} | PASS |
| TEST05 | Delhi | security_deposit | {DL_SEC_001, DL_SEC_002} | {DL_SEC_001, DL_SEC_002} | PASS |
| TEST06 | Delhi | registration | {DL_REG_004} (no Central) | {DL_REG_004} | PASS |
| TEST06c | Delhi | registration (`include_central=True`) | {DL_REG_004, DL_REG_001, DL_REG_002, DL_REG_003} | same | PASS |
| TEST07 | Delhi | eviction | {DL_EVICTION_001, DL_EVICTION_002} (no Central) | same | PASS |
| TEST07c | Delhi | eviction (`include_central=True`) | + DL_EVICTION_003, DL_EVICTION_004 | same | PASS |
| TEST08 | Delhi | maintenance | {DL_MAINT_001, DL_MAINT_004} (no Central) | same | PASS |
| TEST08c | Delhi | maintenance (`include_central=True`) | + DL_MAINT_002, DL_MAINT_003 | same | PASS |

**Note on TEST03:** `MH_LICENCE_001` is topic-tagged `licence_expiry`/`possession_after_expiry`/`overstay` in the KB itself, not `eviction` — it only appears in Maharashtra/eviction retrieval because that is how it was explicitly placed in the master index during Step 9 consolidation (a documented judgment call, not a silent reclassification). TEST03c additionally confirms it stays in the candidate set even when the query text doesn't mention "licence" or "possession" — topic-set membership, not query wording, controls candidacy; query wording only affects ranking.

---

## 3. Jurisdiction Isolation Tests

| Test | Input Jurisdiction | Forbidden Jurisdiction | Returned Forbidden Entry? | Result |
|---|---|---|---|---|
| J1 | Maharashtra | Delhi | No (checked with `include_central=True` too) | PASS |
| J2 | Delhi | Maharashtra | No (checked with `include_central=True` too) | PASS |
| J3 | Maharashtra | Delhi | No | PASS |
| J4 | Delhi | Maharashtra | No | PASS |

All four run with `include_central=True` where applicable, specifically to prove that enabling Central law never leaks a cross-pilot-jurisdiction entry — isolation is enforced independently of the Central-law flag by a defensive filter inside `retrieve_statute` that drops any candidate whose own `jurisdiction` field matches the *other* pilot jurisdiction, regardless of how it got into the candidate list.

---

## 4. Citation Traceability Tests

| Test | Retrieved Entry | Displayed Citation | Expected | Actual | Result |
|---|---|---|---|---|---|
| CITE_VALID | MH_MAINT_001 (in a Maharashtra/maintenance retrieval) | `"Section 14, Maharashtra Rent Control Act, 1999 (Mah. Act No. 18 of 2000)"` (its own citation) | True | True | PASS |
| CITE_FAIL_1 | MH_MAINT_001 (same retrieval) | `"Section 44, Delhi Rent Control Act, 1958"` | False | False | PASS |
| CITE_FAIL_2 | DL_MAINT_001 (in a Delhi/maintenance retrieval) | `"Section 14, Maharashtra Rent Control Act, 1999"` | False | False | PASS |
| CITE_SCOPE | Delhi/maintenance retrieved set (does not contain MH_MAINT_001) | MH_MAINT_001's own (valid, real) citation | False | False | PASS |

CITE_SCOPE is the critical proof required by the spec: MH_MAINT_001's citation is a real, valid citation that genuinely exists in the master KB — but because it does not belong to any entry in *this specific* Delhi retrieval, the check correctly fails. This confirms `validate_citation_traceability` checks membership in the retrieved set for this query, not mere existence anywhere in the 24-entry KB.

---

## 5. Excerpt Traceability

| Test | Result |
|---|---|
| EXCERPT_VALID — unmodified `excerpt_text` displayed against its own entry | PASS |
| EXCERPT_FAIL — one phrase changed ("fifteen days" → "thirty days") in an otherwise identical excerpt | PASS (correctly returns False) |
| EXCERPT_FAIL_DIFFERS — sanity check that the tampered string actually differs from the original | PASS |

---

## 6. Source URL Traceability

| Test | Result |
|---|---|
| URL_VALID — MH_MAINT_001's own URL displayed against itself | PASS |
| URL_FAIL — MH_MAINT_001's URL displayed as if it were DL_MAINT_001's source | PASS (correctly returns False) |

---

## 7. Failure Demonstration

All four required failure modes were exercised and confirmed to fail as required — not skipped, not asserted only in the positive direction:

- **Wrong citation → FAIL:** CITE_FAIL_1, CITE_FAIL_2, CITE_SCOPE
- **Wrong excerpt → FAIL:** EXCERPT_FAIL
- **Wrong source URL → FAIL:** URL_FAIL
- **Wrong jurisdiction → FAIL (i.e., never returned in the first place):** J1–J4, plus TEST01b/02b/03b/04b/05b/06b/06d/07b/08b, which each assert the forbidden cross-jurisdiction IDs are absent from the result set

---

## 8. Final Result

**35 / 35 assertions passed on actual execution.**

**PASS**

- All 8 core retrieval tests (TEST01–TEST08, including the `include_central` variants) match the expected ID sets exactly.
- All 4 jurisdiction isolation tests (J1–J4) confirm zero cross-pilot-jurisdiction leakage, with and without Central law enabled.
- Citation traceability correctly distinguishes "exists somewhere in the KB" from "belongs to this retrieval's result set" (CITE_SCOPE is the decisive test here).
- Excerpt and source-URL traceability both correctly reject any deviation, however small.
- The Central-law policy (documented in `central_law_policy()` and enforced in `retrieve_statute()`) is applied identically for both pilot jurisdictions and never included by default — only on explicit `include_central=True`, and only entries the index itself already lists under that exact topic.

No legal KB content was modified during this step.
