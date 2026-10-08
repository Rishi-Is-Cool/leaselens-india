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

- [x] **Live analysis of uploaded leases** (local app). Upload → state inferred and confirmed
      by the user → background review with a progress bar → risk level for every clause +
      matching statutes with official links. Stored per document, re-runnable with a
      different state, deleted with the upload. Verified in the browser on a Delhi lease.
- [ ] **Plain-language explanations on uploads need an LLM key.** Without one the review
      runs on the offline model (less accurate) and skips explanations + cross-clause links,
      and says so. Setting `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` in `.env` turns them
      on with no code change (~42 calls for a 13-clause lease).
- [ ] LLM capacity: add a paid key, or verify fresh free-tier headroom before any live run.
- [ ] Re-run Phase 4 on the full corpus and keep a clean copy. The only clean data now is
      13 Maharashtra clauses; the 92/92 grounding and 29-connection runs are lost.

**Phase 5 — document-aware chat**
- [x] Chat endpoint scoped to the document + its jurisdiction's statutes (`b3598d6`)
- [x] Quick actions: explain simply / why flagged / what to check, on every live clause card
- [x] Refusal behaviour: other jurisdiction refused before any model call; verdicts,
      uncited law and invented amounts retried once then replaced (19 tests, fake model)
- [x] Chat UI: drawer with citation chips (jump to clause / official source), disclaimer,
      clear messages for no provider, rate limit and network errors. Verified in the
      browser against a stand-in model
- [ ] Run the adversarial checks against the real Groq model once a key is added

**Phase 6 — frontend**
- [ ] Obligation map (tenant must-do / landlord can-do / payments / key dates)
- [x] Jurisdiction selector: inferred from the lease, confirmed by the user, with an
      "Another state (no law check yet)" option
- [ ] Highlighting on the document itself
- [x] Phone-width check of the analysis view and chat (375 px: no horizontal scroll,
      chat goes full-screen)

**Phase 1 leftovers**
- [ ] OCR quality: the JPG test OCR'd but came out garbled
- [ ] Commit 2–3 scanned/photographed samples and record an OCR result
- [ ] Official government templates under-split (recall 18% / 13% / 6%)
- [ ] Tick Phase 1 in `PROGRESS.md` once the above are resolved or consciously deferred

**Phase 7 — deploy and polish**
- [x] **Hosted demo live: https://leaselens-india.vercel.app** (Vercel, backend-free, replays
      saved analyses; auto-redeploys on every push to master). Regenerate its data with
      `python backend/scripts/build_demo_analysis.py` whenever the saved analysis changes;
      a test fails if the bundle goes stale.
- [x] Deploy-ready API: `Dockerfile` (Tesseract + ONNX embeddings, ~350 MB peak, fits
      Render free) and `render.yaml` blueprint. Hugging Face Docker Spaces were tried and
      now need a paid plan
- [x] **Full app live:** API on Render (https://leaselens-api-0adw.onrender.com, Supabase
      connected, Groq configured), frontend on Vercel pointed at it
- [ ] Opt-in "save to account" option (24h auto-delete is already enforced)
- [x] Privacy note visible before upload, plus "Delete this lease now"
- [ ] Plan for Supabase free-tier pausing after ~7 idle days
- [x] **Uploads scoped to the browser that made them** (random client id, stored hashed).
      Listing, opening, reviewing, chatting and deleting all return 404 to anyone else.
- [x] Per-visitor hourly limits on uploads / reviews / chat for the public host

## C. Docs that currently say untrue things

- [ ] `leaselens-complete-handoff.md`: chat endpoint "ready", Phase 6 "complete",
      retention "not enforced", Phase 2 "trained classifier selected", wrong file names,
      116-tests claim
- [x] `README.md` rewritten: features, guardrails, privacy, architecture, deploy
- [ ] `PROGRESS.md` checklist: Phases 1, 5, 6, 7 unticked or stale

## D. Done and verified

- [x] Phases 0–4 built; 141 tests pass locally
- [x] Segmentation 100% (92/92) on 9 synthetic leases; content coverage 99.2% mean
- [x] 24h upload retention enforced and tested against Supabase
- [x] Code on GitHub with single-author history; no secrets found in full git history
- [x] Analysis UI rebuilt (plain-language labels, real statute citations with source links, disclaimer)
- [x] Public demo link live on Vercel, verified anonymous: no login wall, no API calls, no leaks
