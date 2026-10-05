# LeaseLens — Remaining Work Checklist

Audited against the repo and CI on 2026-10-05. Tick items off as they are verified,
not as they are written.

## A. Do first — demo blockers

- [x] **Commit and push the working UI** (`9662a21`).
- [x] Add `*.pid` to `.gitignore`.
- [x] **Fix the demo data.** The endpoint now serves the best record per document: the
      clean Maharashtra sample (13/13 explained, 2 connections) over the broken full run.
      The other 8 samples still have risk labels only. They cannot be regenerated until LLM
      quota is available (see B), and the UI says so rather than showing blanks.
- [x] **Fix CI (red since Sep 22).** Retention tests now create their tables. Confirmed
      green on GitHub Actions: 125 passed, backend and frontend jobs both succeed.
- [x] Install missing deps (`numpy`, `openpyxl`, `scikit-learn`, `sentence-transformers`).
      All test files now collect; 125 passed locally.
- [x] Tesseract: code now finds the default Windows install (or `TESSERACT_CMD`), no PATH
      edit needed. Verified: the image-only page of the West Bengal form routes to OCR.
- [ ] **Rotate exposed secrets** (you must do this in the dashboards): Supabase
      `service_role` and `sb_secret_` keys, and the database password.

## B. Product gaps

- [ ] **Live analysis endpoint.** No route runs classify + explain on an uploaded lease, so
      new uploads only get clause splitting. (~42 LLM calls for a 13-clause document.)
- [ ] LLM capacity: add a paid key, or verify fresh free-tier headroom before any live run.
- [ ] Re-run Phase 4 on the full corpus and keep a clean copy. The only clean data now is
      13 Maharashtra clauses; the 92/92 grounding and 29-connection runs are lost.

**Phase 5 — document-aware chat (not started)**
- [ ] Chat endpoint scoped to the document + its jurisdiction's statutes
- [ ] Quick actions: explain simply / why flagged / what to check
- [ ] Refusal behaviour: other jurisdiction, "is this legal?" — adversarial tests
- [ ] Chat UI

**Phase 6 — frontend**
- [ ] Obligation map (tenant must-do / landlord can-do / payments / key dates)
- [ ] Jurisdiction selector with a clear "not supported yet" note
- [ ] Highlighting on the document itself
- [ ] Phone-width check of the new analysis view

**Phase 1 leftovers**
- [ ] OCR quality: the JPG test OCR'd but came out garbled
- [ ] Commit 2–3 scanned/photographed samples and record an OCR result
- [ ] Official government templates under-split (recall 18% / 13% / 6%)
- [ ] Tick Phase 1 in `PROGRESS.md` once the above are resolved or consciously deferred

**Phase 7 — deploy and polish**
- [ ] Deploy: Render (API) + Vercel (frontend) + Supabase (DB); record the live URL
- [ ] Opt-in "save to account" option (24h auto-delete is already enforced)
- [ ] Privacy note visible before upload
- [ ] Plan for Supabase free-tier pausing after ~7 idle days
- [ ] **Scope `GET /documents` before any public deploy.** It lists every recent upload
      (filename and id) to anyone, and `GET /documents/{id}` returns the full clauses. On
      a shared host that exposes other people's leases. Needs per-session ownership.

## C. Docs that currently say untrue things

- [ ] `leaselens-complete-handoff.md`: chat endpoint "ready", Phase 6 "complete",
      retention "not enforced", Phase 2 "trained classifier selected", wrong file names,
      116-tests claim
- [ ] `README.md` still says "Phase 0 (scaffolding)"
- [ ] `PROGRESS.md` checklist: Phases 1, 5, 6, 7 unticked or stale

## D. Done and verified

- [x] Phases 0–4 built; 125 tests pass locally
- [x] Segmentation 100% (92/92) on 9 synthetic leases; content coverage 99.2% mean
- [x] 24h upload retention enforced and tested against Supabase
- [x] Code on GitHub with single-author history; no secrets found in full git history
- [x] Analysis UI rebuilt and running locally (plain-language labels, statutes, disclaimer)
