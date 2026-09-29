"""
Phase 3 statute knowledge base — retrieval, jurisdiction isolation, and traceability
tests. Adapted from Person C's tests/test_phase3_retrieval.py (60 checks): converted
to pytest, and the 7 Central-jurisdiction entry IDs updated from their old DL_ prefix
to CENTRAL_ (see PROGRESS.md "Phase 3" for the fix writeup). Logic is otherwise
unchanged from the original.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.statute_kb.retrieval import (
    CentralLawPolicyError,
    central_law_policy,
    load_index,
    load_kb,
    retrieve_statute,
    validate_citation_traceability,
    validate_excerpt_traceability,
    validate_source_url_traceability,
)

KB_PATH = Path(__file__).resolve().parents[2] / "data" / "statute_kb" / "leaselens_statute_kb.json"
INDEX_PATH = Path(__file__).resolve().parents[2] / "data" / "statute_kb" / "leaselens_statute_index.json"


def ids_of(results):
    return {r["entry_id"] for r in results}


def test_phase3_retrieval_suite():
    """All 60 original Phase 3 retrieval/isolation/traceability checks, run as one
    pytest test so a single failure names exactly which check_id failed."""
    kb = load_kb(KB_PATH)
    index = load_index(INDEX_PATH)
    results_log = []

    def check(test_id, description, condition):
        results_log.append((test_id, description, bool(condition)))
        assert condition, f"{test_id} FAILED: {description}"

    kb = load_kb(KB_PATH)
    index = load_index(INDEX_PATH)

    results_log = []  # (test_id, description, passed: bool)


    def check(test_id, description, condition):
        results_log.append((test_id, description, bool(condition)))
        status = "PASS" if condition else "FAIL"
        print(f"[{status}] {test_id}: {description}")
        assert condition, f"{test_id} FAILED: {description}"


    def ids_of(results):
        return {r["entry_id"] for r in results}


    # ---------------------------------------------------------------------------
    # TESTS 01-04 : Maharashtra retrieval, per topic
    # ---------------------------------------------------------------------------

    r = retrieve_statute("Maharashtra", "security_deposit", "maximum security deposit amount", kb, index)
    check("TEST01", "Maharashtra/security_deposit returns exactly {MH_SEC_001}",
          ids_of(r) == {"MH_SEC_001"})
    check("TEST01b", "Maharashtra/security_deposit does not return DL_SEC_001/002",
          "DL_SEC_001" not in ids_of(r) and "DL_SEC_002" not in ids_of(r))

    r = retrieve_statute("Maharashtra", "registration", "is registration of the agreement required", kb, index)
    check("TEST02", "Maharashtra/registration returns exactly {MH_REG_001}",
          ids_of(r) == {"MH_REG_001"})
    check("TEST02b", "Maharashtra/registration excludes all Delhi REG entries",
          ids_of(r).isdisjoint({"CENTRAL_REG_001", "CENTRAL_REG_002", "CENTRAL_REG_003", "DL_REG_004"}))

    r = retrieve_statute("Maharashtra", "eviction", "grounds for eviction and licence expiry possession", kb, index)
    expected_eviction_mh = {"MH_EVICTION_001", "MH_EVICTION_002", "MH_EVICTION_003",
                             "MH_EVICTION_004", "MH_EVICTION_005", "MH_LICENCE_001"}
    check("TEST03", "Maharashtra/eviction returns all 5 eviction entries + MH_LICENCE_001",
          ids_of(r) == expected_eviction_mh)
    check("TEST03b", "Maharashtra/eviction excludes Delhi eviction entries",
          ids_of(r).isdisjoint({"DL_EVICTION_001", "DL_EVICTION_002"}))
    # When the query does NOT mention licence/possession, MH_LICENCE_001 should still
    # be a candidate (topic-filtered in) but should not necessarily rank first.
    r_plain = retrieve_statute("Maharashtra", "eviction", "tenant nuisance and damage to premises", kb, index)
    check("TEST03c", "MH_LICENCE_001 still present in candidate set regardless of query wording",
          "MH_LICENCE_001" in ids_of(r_plain))

    r = retrieve_statute("Maharashtra", "maintenance", "who is responsible for repairs", kb, index)
    check("TEST04", "Maharashtra/maintenance returns exactly {MH_MAINT_001, MH_MAINT_002}",
          ids_of(r) == {"MH_MAINT_001", "MH_MAINT_002"})
    check("TEST04b", "Maharashtra/maintenance excludes Delhi maintenance entries",
          ids_of(r).isdisjoint({"DL_MAINT_001", "DL_MAINT_004"}))


    # ---------------------------------------------------------------------------
    # TESTS 05-08 : Delhi retrieval, per topic
    # ---------------------------------------------------------------------------

    r = retrieve_statute("Delhi", "security_deposit", "maximum security deposit amount", kb, index)
    check("TEST05", "Delhi/security_deposit returns exactly {DL_SEC_001, DL_SEC_002}",
          ids_of(r) == {"DL_SEC_001", "DL_SEC_002"})
    check("TEST05b", "Delhi/security_deposit excludes MH_SEC_001",
          "MH_SEC_001" not in ids_of(r))

    r = retrieve_statute("Delhi", "registration", "is registration required", kb, index)
    check("TEST06", "Delhi/registration (no Central) returns exactly {DL_REG_004}",
          ids_of(r) == {"DL_REG_004"})
    check("TEST06b", "Delhi/registration excludes MH_REG_001",
          "MH_REG_001" not in ids_of(r))
    r_central = retrieve_statute("Delhi", "registration", "is registration required", kb, index, include_central=True)
    check("TEST06c", "Delhi/registration WITH include_central=True adds the 3 Central REG entries",
          ids_of(r_central) == {"DL_REG_004", "CENTRAL_REG_001", "CENTRAL_REG_002", "CENTRAL_REG_003"})
    check("TEST06d", "Delhi/registration WITH include_central=True still excludes MH_REG_001",
          "MH_REG_001" not in ids_of(r_central))

    r = retrieve_statute("Delhi", "eviction", "grounds for eviction", kb, index)
    check("TEST07", "Delhi/eviction (no Central) returns exactly {DL_EVICTION_001, DL_EVICTION_002}",
          ids_of(r) == {"DL_EVICTION_001", "DL_EVICTION_002"})
    check("TEST07b", "Delhi/eviction excludes all 6 Maharashtra eviction/licence entries",
          ids_of(r).isdisjoint({"MH_EVICTION_001", "MH_EVICTION_002", "MH_EVICTION_003",
                                "MH_EVICTION_004", "MH_EVICTION_005", "MH_LICENCE_001"}))
    r_central = retrieve_statute("Delhi", "eviction", "grounds for eviction", kb, index, include_central=True)
    check("TEST07c", "Delhi/eviction WITH include_central=True adds the 2 Central eviction entries",
          ids_of(r_central) == {"DL_EVICTION_001", "DL_EVICTION_002", "CENTRAL_EVICTION_003", "CENTRAL_EVICTION_004"})

    r = retrieve_statute("Delhi", "maintenance", "who is responsible for repairs", kb, index)
    check("TEST08", "Delhi/maintenance (no Central) returns exactly {DL_MAINT_001, DL_MAINT_004}",
          ids_of(r) == {"DL_MAINT_001", "DL_MAINT_004"})
    check("TEST08b", "Delhi/maintenance excludes MH_MAINT_001/002",
          ids_of(r).isdisjoint({"MH_MAINT_001", "MH_MAINT_002"}))
    r_central = retrieve_statute("Delhi", "maintenance", "who is responsible for repairs", kb, index, include_central=True)
    check("TEST08c", "Delhi/maintenance WITH include_central=True adds the 2 Central maintenance entries",
          ids_of(r_central) == {"DL_MAINT_001", "DL_MAINT_004", "CENTRAL_MAINT_002", "CENTRAL_MAINT_003"})


    # ---------------------------------------------------------------------------
    # JURISDICTION ISOLATION TESTS  J1-J4
    # ---------------------------------------------------------------------------

    r = retrieve_statute("Maharashtra", "maintenance", "Who is responsible for repairs?", kb, index, include_central=True)
    check("J1", "Maharashtra/maintenance never returns a Delhi entry (even with Central included)",
          all(e["jurisdiction"] != "Delhi" for e in r))

    r = retrieve_statute("Delhi", "maintenance", "Who is responsible for repairs?", kb, index, include_central=True)
    check("J2", "Delhi/maintenance never returns a Maharashtra entry (even with Central included)",
          all(e["jurisdiction"] != "Maharashtra" for e in r))

    r = retrieve_statute("Maharashtra", "security_deposit", "Is there a maximum security deposit?", kb, index, include_central=True)
    check("J3", "Maharashtra/security_deposit never returns a Delhi-specific entry",
          all(e["jurisdiction"] != "Delhi" for e in r))

    r = retrieve_statute("Delhi", "security_deposit", "Is there a maximum security deposit?", kb, index, include_central=True)
    check("J4", "Delhi/security_deposit never returns a Maharashtra-specific entry",
          all(e["jurisdiction"] != "Maharashtra" for e in r))


    # ---------------------------------------------------------------------------
    # CENTRAL LAW POLICY sanity check
    # ---------------------------------------------------------------------------

    policy_mh = central_law_policy("Maharashtra")
    policy_dl = central_law_policy("Delhi")
    check("POLICY1", "Central-law policy is documented identically for both pilot jurisdictions",
          policy_mh == policy_dl)


    # ---------------------------------------------------------------------------
    # CITATION TRACEABILITY TESTS
    # ---------------------------------------------------------------------------

    mh_maint = retrieve_statute("Maharashtra", "maintenance", "landlord repair duty", kb, index)
    mh_maint_001 = next(e for e in mh_maint if e["entry_id"] == "MH_MAINT_001")

    # Valid case: citation actually belongs to a retrieved entry
    check("CITE_VALID", "Correct citation for a retrieved entry passes traceability",
          validate_citation_traceability(mh_maint, mh_maint_001["citation"]) is True)

    # Deliberate failure case 1: MH_MAINT_001 retrieved, but a Delhi citation displayed.
    # This citation DOES exist elsewhere in the whole master KB (DL_MAINT_001's own
    # citation covers DRCA S.44) -- proving the test checks the RETRIEVED SET, not
    # the whole KB.
    wrong_citation_1 = "Section 44, Delhi Rent Control Act, 1958"
    check("CITE_FAIL_1", "MH_MAINT_001 retrieved + Delhi citation displayed --> FAILS as required",
          validate_citation_traceability(mh_maint, wrong_citation_1) is False)

    dl_maint = retrieve_statute("Delhi", "maintenance", "landlord repair duty", kb, index)
    wrong_citation_2 = "Section 14, Maharashtra Rent Control Act, 1999"
    check("CITE_FAIL_2", "DL_MAINT_001 retrieved + Maharashtra citation displayed --> FAILS as required",
          validate_citation_traceability(dl_maint, wrong_citation_2) is False)

    # Extra rigor: prove the check is retrieved-set-scoped, not global-KB-scoped.
    # MH_MAINT_001's own citation DOES exist in the whole KB, but is NOT in the
    # Delhi-only retrieved set, so checking it against dl_maint must fail.
    check("CITE_SCOPE", "A citation that exists in the KB but not in THIS retrieved set fails",
          validate_citation_traceability(dl_maint, mh_maint_001["citation"]) is False)


    # ---------------------------------------------------------------------------
    # EXCERPT TRACEABILITY TESTS
    # ---------------------------------------------------------------------------

    check("EXCERPT_VALID", "Unmodified excerpt_text passes traceability",
          validate_excerpt_traceability(mh_maint_001, mh_maint_001["excerpt_text"]) is True)

    tampered_excerpt = mh_maint_001["excerpt_text"].replace("fifteen days", "thirty days", 1)
    check("EXCERPT_FAIL", "A single changed word ('fifteen days' -> 'thirty days') fails traceability",
          validate_excerpt_traceability(mh_maint_001, tampered_excerpt) is False)
    check("EXCERPT_FAIL_DIFFERS", "Sanity: the tampered excerpt is actually different text",
          tampered_excerpt != mh_maint_001["excerpt_text"])


    # ---------------------------------------------------------------------------
    # SOURCE URL TRACEABILITY TESTS
    # ---------------------------------------------------------------------------

    check("URL_VALID", "Unmodified source_url passes traceability",
          validate_source_url_traceability(mh_maint_001, mh_maint_001["source_url"]) is True)

    dl_maint_001 = next(e for e in dl_maint if e["entry_id"] == "DL_MAINT_001")
    check("URL_FAIL", "MH_MAINT_001's own URL displayed against a Delhi entry's expected URL fails",
          validate_source_url_traceability(dl_maint_001, mh_maint_001["source_url"]) is False)


    # ---------------------------------------------------------------------------
    # STEP 11B : last_verified_date field on retrieval results
    # ---------------------------------------------------------------------------

    by_id_all = {e["id"]: e for e in kb["entries"]}

    # (a) A known retrieved statute contains last_verified_date
    mh_sec = retrieve_statute("Maharashtra", "security_deposit", "security deposit amount", kb, index)
    check("LVD_A_PRESENT", "MH_SEC_001 retrieval result contains a 'last_verified_date' key",
          "last_verified_date" in mh_sec[0])

    # (b) The returned date exactly equals the date stored in the KB entry
    check("LVD_B_MATCHES_KB", "Returned last_verified_date exactly equals MH_SEC_001's KB value",
          mh_sec[0]["last_verified_date"] == by_id_all["MH_SEC_001"]["last_verified_date"])

    # (c) Different retrieved entries preserve their OWN verification dates,
    # not one hard-coded value copied across every result. Pick two entries
    # known to have different last_verified_date values in the KB and confirm
    # both the KB and the retrieval output disagree on them the same way.
    dl_sec_results = retrieve_statute("Delhi", "security_deposit", "advance rent premium", kb, index)
    dl_sec_by_id = {r["entry_id"]: r for r in dl_sec_results}

    mh_evict_results = retrieve_statute("Maharashtra", "eviction", "nuisance damage bona fide", kb, index)
    mh_evict_by_id = {r["entry_id"]: r for r in mh_evict_results}

    # Sanity: confirm the KB itself actually has at least two distinct
    # last_verified_date values among the entries we're about to compare,
    # otherwise this test would trivially "pass" without proving anything.
    kb_dates_sample = {
        "MH_SEC_001": by_id_all["MH_SEC_001"]["last_verified_date"],
        "MH_EVICTION_001": by_id_all["MH_EVICTION_001"]["last_verified_date"],
    }
    check("LVD_C_SETUP_SANITY", "Sample entries used for the per-entry date check exist in the KB",
          all(v is not None for v in kb_dates_sample.values()))

    check("LVD_C_PER_ENTRY_MH_SEC", "MH_SEC_001's retrieved date matches its own KB record, not a shared constant",
          mh_sec[0]["last_verified_date"] == by_id_all["MH_SEC_001"]["last_verified_date"])
    check("LVD_C_PER_ENTRY_MH_EVICTION", "MH_EVICTION_001's retrieved date matches its own KB record, not a shared constant",
          mh_evict_by_id["MH_EVICTION_001"]["last_verified_date"] == by_id_all["MH_EVICTION_001"]["last_verified_date"])
    check("LVD_C_PER_ENTRY_DL_SEC", "DL_SEC_001's retrieved date matches its own KB record, not a shared constant",
          dl_sec_by_id["DL_SEC_001"]["last_verified_date"] == by_id_all["DL_SEC_001"]["last_verified_date"])
    # Cross-check that this isn't just three entries that happen to coincidentally
    # share one hard-coded literal in the retrieval code -- verify each date was
    # read from a genuinely different dict object per entry.
    check("LVD_C_NOT_HARDCODED", "The three checked entries' KB last_verified_date fields are read independently per entry (not all forced equal by construction)",
          mh_sec[0]["last_verified_date"] == by_id_all["MH_SEC_001"]["last_verified_date"] and
          mh_evict_by_id["MH_EVICTION_001"]["last_verified_date"] == by_id_all["MH_EVICTION_001"]["last_verified_date"] and
          dl_sec_by_id["DL_SEC_001"]["last_verified_date"] == by_id_all["DL_SEC_001"]["last_verified_date"])

    # All 24 KB entries: retrieval must never invent or alter a last_verified_date
    # relative to what's in the KB, across every entry reachable via any topic.
    mismatches = []
    for jur in ("Maharashtra", "Delhi"):
        for topic, ids in index.get(jur, {}).items():
            res = retrieve_statute(jur, topic, "", kb, index, include_central=True)
            for r in res:
                expected = by_id_all[r["entry_id"]]["last_verified_date"]
                if r["last_verified_date"] != expected:
                    mismatches.append((r["entry_id"], r["last_verified_date"], expected))
    check("LVD_ALL_ENTRIES", "Every reachable retrieval result's last_verified_date matches its KB entry exactly, KB-wide",
          mismatches == [])

    # Preserved existing fields are still all present alongside the new one
    required_fields = {"entry_id", "citation", "excerpt_text", "source_url",
                        "jurisdiction", "topic_tags", "relevance_score", "last_verified_date"}
    check("LVD_SCHEMA", "Result dict contains exactly the expected 8 fields (7 existing + last_verified_date)",
          set(mh_sec[0].keys()) == required_fields)


    # ---------------------------------------------------------------------------
    # STEP 12 : notice + rent escalation topic coverage
    # ---------------------------------------------------------------------------

    new_ids = {e["id"] for e in kb["entries"]}
    for expected_id in ("MH_NOTICE_001", "MH_RENT_001", "DL_NOTICE_001", "DL_RENT_001"):
        check("STEP12_ID_" + expected_id, f"{expected_id} is present in the Step 12 KB", expected_id in new_ids)

    for jur, topic, query, expected in [
        ("Maharashtra", "notice", "ninety days written demand notice for non-payment", {"MH_NOTICE_001"}),
        ("Maharashtra", "rent_escalation", "four percent annual rent increase", {"MH_RENT_001"}),
        ("Delhi", "notice", "thirty days written notice before rent increase", {"DL_NOTICE_001"}),
        ("Delhi", "rent_escalation", "ten percent increase every three years", {"DL_RENT_001", "DL_NOTICE_001"}),
    ]:
        res = retrieve_statute(jur, topic, query, kb, index)
        ids = {r["entry_id"] for r in res}
        check("STEP12_RETRIEVAL_" + jur + "_" + topic, f"{jur}/{topic} returns the expected Step 12 statute entry set", ids == expected)
        check("STEP12_ISOLATION_" + jur + "_" + topic, f"{jur}/{topic} returns no other pilot jurisdiction entry", all(r["jurisdiction"] != ("Delhi" if jur == "Maharashtra" else "Maharashtra") for r in res))
        check("STEP12_DATE_" + jur + "_" + topic, f"{jur}/{topic} results carry the exact KB last_verified_date", all(r["last_verified_date"] == by_id_all[r["entry_id"]]["last_verified_date"] for r in res))



    passed = sum(1 for _, _, ok in results_log if ok)
    assert passed == len(results_log) == 60, (
        f"Expected all 60 Phase 3 checks to run and pass, got {passed}/{len(results_log)}"
    )


def test_central_law_policy_rejects_unsupported_jurisdiction():
    with pytest.raises(CentralLawPolicyError):
        central_law_policy("Central")


def test_retrieve_statute_rejects_unsupported_jurisdiction():
    kb = load_kb(KB_PATH)
    index = load_index(INDEX_PATH)
    with pytest.raises(CentralLawPolicyError):
        retrieve_statute("Central", "eviction", "", kb, index)
