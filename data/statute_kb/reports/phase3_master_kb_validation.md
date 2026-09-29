# Phase 3 Master KB Validation

**Date:** 2026-09-26
**Task:** Correction — add verified Maharashtra records to the master statute KB (consolidation only; no new legal research performed)

---

## 1. Consolidation Summary

Recalculated directly from the regenerated `leaselens_statute_kb.json`.

| Metric | Count |
|---|---|
| **Total entries in master KB** | **24** |
| Maharashtra entries | **10** |
| Delhi entries | **7** |
| Central entries | **7** |
| Topics represented (Maharashtra) | security_deposit, registration, eviction, maintenance |
| Topics represented (Delhi) | security_deposit, registration, eviction, maintenance |

This corrects the prior consolidation, which contained 14 entries (0 Maharashtra) because the Maharashtra source files were not available at that time. The 10 Maharashtra records below were added from the verified project source files:

`MH_SEC_001`, `MH_REG_001`, `MH_EVICTION_001`–`005`, `MH_MAINT_001`, `MH_MAINT_002`, `MH_LICENCE_001`.

---

## 2. Coverage Matrix

| Jurisdiction | Security Deposit | Registration | Eviction | Maintenance |
|---|---|---|---|---|
| Maharashtra | COVERED (MH_SEC_001 — MRCA §56(ii); no numeric deposit cap established, documented in entry notes) | COVERED (MH_REG_001 — MRCA §55) | PARTIAL (MH_EVICTION_001–005 cover §15 and 4 of the ~14 grounds in §16; §16(d),(e),(f),(h)–(m), §§22–23 not yet researched; MH_LICENCE_001 covers the separate licence-expiry mechanism under §24) | COVERED (MH_MAINT_001 — MRCA §14 landlord duty + tenant repair-and-deduct remedy; MH_MAINT_002 — MRCA §11(2) ordinary-repair/structural-improvement distinction) |
| Delhi | COVERED (DL_SEC_001, DL_SEC_002) | COVERED (DL_REG_004 + Central registration entries) | COVERED (DL_EVICTION_001–002 + Central) | COVERED (DL_MAINT_001, DL_MAINT_004 + Central) |

Delhi's matrix is carried forward unchanged from the prior validation report, consistent with the instruction not to re-touch or re-verify Delhi/Central content in this pass.

---

## 3. Jurisdiction Distribution

### Maharashtra
- MH_SEC_001
- MH_REG_001
- MH_EVICTION_001
- MH_EVICTION_002
- MH_EVICTION_003
- MH_EVICTION_004
- MH_EVICTION_005
- MH_MAINT_001
- MH_MAINT_002
- MH_LICENCE_001

### Delhi
- DL_SEC_001
- DL_SEC_002
- DL_REG_004
- DL_EVICTION_001
- DL_EVICTION_002
- DL_MAINT_001
- DL_MAINT_004

### Central
- DL_REG_001 (Registration Act)
- DL_REG_002 (TPA)
- DL_REG_003 (Registration Act)
- DL_EVICTION_003 (TPA §106)
- DL_EVICTION_004 (TPA §111)
- DL_MAINT_002 (TPA §108(f))
- DL_MAINT_003 (TPA §108(m))

---

## 4. Duplicate Check

- **Duplicate IDs found?** NO. All 24 IDs in the consolidated master KB are unique — verified programmatically against the actual file, not assumed.
- **Duplicate legal records found?** NO exact duplicates among the 24 consolidated entries.
- **MH_LICENCE_001 placement:** this record (MRCA §24 — licence expiry, possession after expiry, overstay) does not cleanly fit any of the four required topic buckets; it was placed under **eviction** in the index because it is functionally the licensor's mechanism for recovering possession, which is the closest existing category. Its own `topic_tags` field was left unchanged (`licence_expiry`, `possession_after_expiry`, `overstay`) — only its index placement reflects this judgment call. Flagging this explicitly rather than silently deciding it belongs there.

### ⚠️ Important integrity finding — NOT a duplicate within the master KB, but a cross-context conflict

This conversation independently drafted its own `DL_SEC_001` and `DL_SEC_002` records earlier (Delhi Rent Control Act §5(2) and §5(4)) during Step 4 of this project. Those drafts were **never added to any master KB** and are sitting only in this session's working files. The master KB you uploaded already contains **different records with the same IDs** — its `DL_SEC_001` covers all of DRCA §5(1)–(4) in one entry, and its `DL_SEC_002` is a *different provision entirely* (topic-tagged `deposit_of_rent`, likely §27, not §5(4)).

Per your instruction not to alter existing Delhi/Central entries, **I did not touch or overwrite the uploaded versions** — they are preserved exactly as uploaded. But you now have two non-identical candidate records for the IDs `DL_SEC_001`/`DL_SEC_002` across two different work sessions. This needs your explicit decision (which version is authoritative) before Delhi security-deposit citations can be trusted as consistent — I'm surfacing it rather than silently picking one.

- **CENTRAL_MAINT_001 status:** per your instruction to use only a "verified" version and exclude any version with `confidence: pending_primary_source_verification`, I checked this session's copy of `CENTRAL_MAINT_001` (TPA §108(f)) — it is the parked version from Step 3, still `pending_primary_source_verification` (India Code has no fetchable document for the Transfer of Property Act at this time; see that entry's `verification_status` field). **No other, verified version of CENTRAL_MAINT_001 exists in this session's files.** Consistent with your instruction, it was **not added**. Note the uploaded master KB already has a functionally similar record under a different ID (`DL_MAINT_002`, TPA §108(f)) — possibly the "verified" counterpart you had in mind from the other session; I did not merge or compare these further since that would mean modifying an existing Central entry.
- **CENTRAL_NOTICE_001** (TPA §106, this session) was likewise not added — it isn't on your explicit list of records to add, and the master KB's existing `DL_EVICTION_003` already covers TPA §106 under a different ID.

---

## 5. Schema Validation

Recalculated by checking every one of the 24 entries for `id`, `citation`, `excerpt_text`, `source_url`, `jurisdiction`, `topic_tags`, `last_verified_date`.

**Result: PASS.** Zero entries missing any required field.

---

## 6. Source Validation

Every one of the 24 entries has a non-empty `source_url`. No URLs were invented or altered during this consolidation.

**Result: PASS.**

---

## 7. Excerpt Integrity

Verified programmatically, not asserted:
- All 14 pre-existing (Delhi/Central) entries are **byte-for-byte identical** to the uploaded master KB — zero fields changed.
- All 10 new Maharashtra entries are **byte-for-byte identical** to their verified source files in the project workspace — no paraphrasing, shortening, or correction applied during consolidation.

**Result: PASS.**

---

## 8. Jurisdiction Isolation

**Maharashtra + maintenance:**
- Allowed: `MH_MAINT_001`, `MH_MAINT_002`
- Allowed (if the application elects to surface Central law): none currently linked — see gap below regarding `CENTRAL_MAINT_001`/`DL_MAINT_002`
- **Not allowed:** `DL_MAINT_001`, `DL_MAINT_004` (Delhi-specific)

**Delhi + maintenance:**
- Allowed: `DL_MAINT_001`, `DL_MAINT_004`
- Allowed (Central, if surfaced): `DL_MAINT_002`, `DL_MAINT_003`
- **Not allowed:** `MH_MAINT_001`, `MH_MAINT_002` (Maharashtra-specific)

**Maharashtra + security deposit:**
- Allowed: `MH_SEC_001`
- **Not allowed:** `DL_SEC_001`, `DL_SEC_002`

**Delhi + security deposit:**
- Allowed: `DL_SEC_001`, `DL_SEC_002`
- **Not allowed:** `MH_SEC_001`

**Maharashtra + registration:**
- Allowed: `MH_REG_001`
- **Not allowed:** `DL_REG_004`, and Central registration entries unless explicitly enabled

**Delhi + registration:**
- Allowed: `DL_REG_004`
- Allowed (Central, if surfaced): `DL_REG_001`, `DL_REG_002`, `DL_REG_003`
- **Not allowed:** `MH_REG_001`

**Maharashtra + eviction:**
- Allowed: `MH_EVICTION_001`–`005`, `MH_LICENCE_001`
- **Not allowed:** `DL_EVICTION_001`, `DL_EVICTION_002`

**Delhi + eviction:**
- Allowed: `DL_EVICTION_001`, `DL_EVICTION_002`
- Allowed (Central, if surfaced): `DL_EVICTION_003`, `DL_EVICTION_004`
- **Not allowed:** `MH_EVICTION_001`–`005`, `MH_LICENCE_001`

Central entries remain labelled `"jurisdiction": "Central"` throughout and are never counted as Maharashtra- or Delhi-specific statutes.

---

## 9. Known Gaps

1. **Maharashtra eviction — partial.** Only 5 of the Maharashtra Rent Control Act's ~14 grounds under §16 are covered (non-payment relief under §15; damage/unauthorized structures §16(1)(a)-(b); nuisance/illegal use §16(1)(c); bona fide occupation §16(1)(g); non-use §16(1)(n)). Not yet researched: subletting/assignment §16(1)(e), service-tenancy cessation §16(1)(f), the repair/demolition cluster §16(1)(h)-(l), excess-rent subletting §16(1)(m), tenant-notice prejudice §16(1)(d), and Sections 22–23.
2. **Maharashtra security deposit — no numeric cap.** MRCA §56(ii) legalizes a landlord receiving a deposit but establishes no month-based limit; this is documented in the entry itself, not silently assumed.
3. **DL_SEC_001/DL_SEC_002 ID conflict** (see Section 4 above) — unresolved, needs your decision.
4. **CENTRAL_MAINT_001 has no verified version in this session** — parked at `pending_primary_source_verification` since India Code currently has no fetchable Transfer of Property Act document; the uploaded master's `DL_MAINT_002` may already be the intended verified counterpart, but this was not confirmed against this session's parked record.
5. **Leave-and-licence applicability** — as in the prior report, several Maharashtra entries (the eviction/maintenance provisions keyed to "tenant" under the Rent Control Act) explicitly do **not** extend to leave-and-license agreements, which is the dominant modern rental structure in Maharashtra; this gap was flagged per-entry rather than left implicit.
6. Prior Delhi gaps (structural repairs marked PARTIAL, leave-and-licence applicability, Delhi Rent Act 1995 non-operative) are carried forward unchanged, not re-verified in this pass.

---

## 10. Final Status

**PASS WITH DOCUMENTED GAPS**

- All 8 required jurisdiction/topic areas (Maharashtra × 4 topics, Delhi × 4 topics) now have at least one entry — the blocking gap from the prior report (missing Maharashtra) is resolved.
- Schema validation, unique IDs, source URLs, and excerpt integrity all pass on the actual 24-entry file, verified programmatically.
- The remaining gaps (Maharashtra eviction coverage breadth, the DL_SEC_001/002 ID conflict, and the CENTRAL_MAINT_001 ambiguity) are genuine open items requiring either further research or an explicit decision from you — not integrity failures in what has been consolidated, but they are not swept under "PASS" either.

---

## Source files used for this consolidation pass

| File | Status |
|---|---|
| `leaselens_statute_kb.json` (uploaded, 14 entries) | Used as base, entries preserved unchanged |
| `leaselens_statute_index.json` (uploaded) | Used as base, Delhi/Central sections preserved unchanged |
| `MH_SEC_001.json` through `MH_LICENCE_001.json` (10 files, this session's verified Maharashtra KB) | Added |
| `CENTRAL_MAINT_001.json` (this session, parked) | Reviewed, excluded per instruction |
| `CENTRAL_NOTICE_001.json`, `DL_SEC_001.json`, `DL_SEC_002.json` (this session's own unconsolidated drafts) | Reviewed, excluded — not on the add-list; DL_SEC_001/002 conflict with uploaded master noted above |
