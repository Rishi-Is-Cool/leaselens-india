# LeaseLens — Remaining Work Checklist

Audited against the repo and CI on 2026-10-05. Tick items off as they are verified,
not as they are written.

## A. Do first — demo blockers

- [ ] **Commit and push the working UI.** Uncommitted: frontend rebuild (`App.tsx`,
      `api.ts`, `styles.css`), `backend/app/routers/demo.py`, `main.py`, `documents.py`
      (list endpoint), `test/maharashtra.pdf`. None of it is on GitHub yet.
- [ ] Add `*.pid` to `.gitignore` (`backend/.server.pid`, `.frontend-server.pid`).
- [ ] **Fix the demo data.** `demo.py:21` prefers `data/phase4_raw_results.json`, which has
      82 errors in 92 clauses and 0 cross-clause connections. Point it at the clean
      sample, or regenerate the results (back up first).
- [ ] **Fix CI (red since Sep 22).** `tests/test_retention.py` fails on an empty Postgres
      because the `documents` table doesn't exist there. 117 pass, 2 fail.
- [ ] Install missing deps: `pip install -r backend/requirements.txt` (`numpy` and
      `openpyxl` missing, so 5 test files cannot be collected locally).
- [ ] Put Tesseract on PATH (`C:\Program Files\Tesseract-OCR`).
- [ ] Rotate exposed secrets: Supabase `service_role`, `sb_secret_`, and the DB password.

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

## C. Docs that currently say untrue things

- [ ] `leaselens-complete-handoff.md`: chat endpoint "ready", Phase 6 "complete",
      retention "not enforced", Phase 2 "trained classifier selected", wrong file names,
      116-tests claim
- [ ] `README.md` still says "Phase 0 (scaffolding)"
- [ ] `PROGRESS.md` checklist: Phases 1, 5, 6, 7 unticked or stale

## D. Done and verified

- [x] Phases 0–4 built; CI shows 117 tests passing
- [x] Segmentation 100% (92/92) on 9 synthetic leases; content coverage 99.2% mean
- [x] 24h upload retention enforced and tested against Supabase
- [x] Code on GitHub with single-author history; no secrets found in full git history
- [x] Analysis UI rebuilt and running locally (plain-language labels, statutes, disclaimer)
