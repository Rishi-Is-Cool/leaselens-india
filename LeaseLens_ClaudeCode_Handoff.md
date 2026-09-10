# LeaseLens — Claude Code Build Handoff

**Purpose of this document:** this is a phased, gated execution plan for building LeaseLens. It is written to be pasted into a Claude Code session (or referenced from `CLAUDE.md` / a project instructions file) so an agent can build the product incrementally without derailing, skipping validation, or shipping ungrounded legal claims.

---

## 0. Rules of engagement (read first, apply to every phase)

1. **Work in phase order. Do not start Phase N+1 until Phase N's exit criteria are met.** Each phase below has an explicit "Definition of Done." Treat it as a hard gate, not a suggestion.
2. **After finishing a phase**, run its verification steps yourself, report the results plainly (what was built, what was tested, what passed/failed), update `PROGRESS.md` at the repo root (create it in Phase 0), and then stop and wait for explicit confirmation before moving on — unless you have been told this is an unattended/autonomous run, in which case proceed only if every exit criterion is objectively met, and stop and explain if any is not.
3. **Never mark a phase done with failing tests, partial implementation, or unresolved errors.** If blocked, say so specifically (what's blocking, what you tried) instead of working around it silently.
4. **Commit at the end of each phase** with a message naming the phase (e.g. `feat: phase 2 - risk classifier + dataset audit`). Do not squash phases together.
5. **No hardcoded secrets.** All API keys/config via `.env`, with `.env.example` checked in and `.env` gitignored.
6. **Legal-safety rule (applies everywhere, non-negotiable):** the system never states a clause is "illegal" or gives a definitive legal conclusion. It flags "potential concern," cites its evidence (clause text and/or statute excerpt), and separates document facts from AI interpretation. Every screen showing AI output carries a visible disclaimer: *"This is AI-assisted information, not legal advice. Laws vary by location and change over time — verify with a qualified professional before acting."*
7. **No invented citations.** Any law/statute reference shown to a user must trace back to a retrieved entry in the curated statute knowledge base (Phase 3). If nothing relevant is retrieved, the system says so explicitly rather than letting the LLM fill the gap from its own training data. This rule gets an automated test — see Phase 3 and Phase 4 exit criteria.
8. **Privacy default:** uploaded lease documents are personal/sensitive. Default behavior is to delete extracted text and the source file after a bounded retention window (e.g. 24–72 hours) unless the user explicitly opts to save it to an account. This must be implemented, not just promised — see Phase 7.

---

## 1. Tech stack (lock these in Phase 0, don't relitigate mid-build)

- **Backend:** FastAPI (Python)
- **Frontend:** React (Vite), TypeScript
- **PDF/text extraction:** `pdfplumber` or `PyMuPDF`; OCR fallback via `pytesseract` (or a cloud OCR API if budget allows) for scanned/photographed leases
- **Embeddings / vector search:** start with a lightweight local option (`chromadb` or `pgvector` on Postgres) — no need for a managed vector DB at MVP scale
- **Classifier:** scikit-learn or a small HF transformer fine-tune for the GREEN/YELLOW/RED classifier; compare against an LLM zero-shot baseline (see Phase 2 — do not assume the trained classifier wins without measuring)
- **LLM:** Claude API for explanation generation, chat, and cross-clause reasoning
- **Database:** Postgres (documents, clauses, classifier outputs, chat history, statute KB)
- **Deployment target:** pick one and commit — e.g. Render/Fly.io for backend + Postgres, Vercel for frontend. Decide in Phase 0, don't change later without a documented reason.

If Claude Code judges a different tool is clearly better for a specific piece (e.g. a different PDF library that handles a real test document better), it may substitute — but it must say so and why, not swap silently.

---

## Phase 0 — Scaffolding & environment

**Goal:** a working skeleton, nothing more.

Tasks:
- Repo structure: `/backend`, `/frontend`, `/data` (for the clause dataset and statute KB), `PROGRESS.md`, `README.md`, `.env.example`.
- FastAPI app with a `GET /health` endpoint.
- React app shell that calls `/health` on load and displays the result.
- Postgres connection configured and confirmed reachable from the backend.
- Basic CI stub (even just "run backend tests on push") is a plus but not required to pass this gate.

**Definition of Done (verify before proceeding):**
- `curl /health` returns 200 from a running backend.
- Frontend loads and visibly shows a successful health-check response.
- `PROGRESS.md` created with a checklist of all phases in this document, Phase 0 checked off.

---

## Phase 1 — Document ingestion & clause segmentation

**Goal:** given a lease file (clean PDF or scanned/photographed image-PDF), produce a clean list of clause objects.

Tasks:
- Upload endpoint (`POST /documents`) accepting PDF (and JPEG/PNG for photographed leases).
- Text extraction pipeline: try direct text extraction first; if the page has little/no extractable text, fall back to OCR.
- Clause segmentation: heuristic splitter (numbering patterns, headings, paragraph breaks) that outputs `{clause_id, section_heading, text, order}` objects. This does not need to be ML-based yet — a solid rule-based segmenter is fine for MVP.
- Store parsed clauses in Postgres, linked to the source document.

**Definition of Done:**
- Assemble a small test set of 8–10 real or realistic lease documents, including at least 2–3 scanned/photographed ones.
- Run the pipeline on all of them; manually check clause segmentation accuracy — target ≥90% of clauses correctly and cleanly split (no clause split mid-sentence, no two clauses merged) on this test set. Record the actual measured accuracy in `PROGRESS.md`, don't just assert it passed.
- OCR fallback demonstrably triggers and produces usable text on the scanned samples.

---

## Phase 2 — Dataset audit & risk classifier

**Goal:** a working GREEN/YELLOW/RED clause classifier, with an honest comparison against an LLM baseline.

Tasks:
- Load the existing ~1,846-clause labeled dataset.
- Audit: check class balance, deduplicate exact and near-duplicate clauses (embedding similarity), and split train/test **at the document level** (not clause level) to prevent leakage from clauses of the same lease appearing in both sets.
- Train a baseline supervised classifier (embeddings + simple classifier head, or small transformer fine-tune).
- Build a second baseline: LLM zero-/few-shot classification of the same test clauses using a clear risk-classification prompt.
- Compare both on the leakage-free test split (accuracy, per-class F1, confusion matrix).
- Decide and document which to ship: trained classifier, LLM baseline, or an ensemble — based on the actual numbers, not assumption.

**Definition of Done:**
- Audit results (class balance, duplicate count, leakage check) written to `PROGRESS.md`.
- Both classifiers evaluated on the same held-out set; results table committed to the repo (e.g. `data/classifier_eval.md`).
- Chosen approach beats a majority-class baseline by a meaningful margin, and the choice + reasoning is documented.
- Classifier wrapped behind a single internal function/endpoint (`classify_clause(text) -> risk_label`) so the rest of the system doesn't care which approach is underneath.

---

## Phase 3 — Statute knowledge base & Official Law Reference (pilot jurisdictions only)

**Goal:** ground explanations in real, citable law for a deliberately small starting scope.

Tasks:
- Pick **two pilot jurisdictions** (recommend: Maharashtra and Delhi, given the India-focused positioning) and hand-curate a structured statute dataset covering the topics most relevant to lease risk: security deposit limits, notice periods, eviction grounds, maintenance responsibility, rent escalation rules, registration/stamp duty requirements.
- Schema per entry: `citation, excerpt_text, source_url, jurisdiction, topic_tags[], last_verified_date`.
- Build retrieval: match a flagged clause to relevant statute entries by topic tag first, then embedding similarity within that jurisdiction's entries only. Never retrieve across jurisdictions.
- Store this as its own table/corpus, separate from the lease-clause data — this is not something the LLM free-generates from.
- User selects (or the system infers, with user confirmation) a jurisdiction before analysis runs.

**Definition of Done:**
- Statute KB contains a meaningful, real set of entries for both pilot jurisdictions (not placeholder text) with working source URLs.
- Automated test: for a sample of flagged clauses, every law citation shown in output must exactly match an entry that was actually retrieved — write a test that fails the build if a citation appears that isn't traceable to a KB entry.
- Coverage report: what % of flagged clauses in the pilot jurisdictions get at least one relevant statute match. Low coverage is fine to ship (it's honest), silently fabricated coverage is not.

---

## Phase 4 — LLM explanation layer, cross-clause detection, hallucination guardrails

**Goal:** turn a risk label + retrieved evidence into a trustworthy explanation.

Tasks:
- Prompt design for explanation generation that receives: the clause text, its risk label, any matched statute excerpts from Phase 3, and instructions to separate "what the document says" from "why this might be a concern."
- Cross-clause connection detection: embedding similarity to shortlist candidate related clauses, then an LLM pass to confirm/explain the relationship (e.g. termination-notice clause + early-termination-payment clause).
- Grounding guardrail: implement an automated check that every factual claim in a generated explanation is traceable to either (a) a quote/paraphrase of the clause text or (b) a retrieved statute excerpt. Flag or block ungrounded output.

**Definition of Done:**
- Run the pipeline on the Phase 1 test document set; manually review a sample of generated explanations for accuracy and groundedness.
- Automated grounding-check pass rate ≥95% on a test batch (document the actual number).
- At least 3 real cross-clause connections correctly identified and explained across the test set (or, if the test set doesn't contain any, a synthetic test case confirms the mechanism works).

---

## Phase 5 — Document-aware chat

**Goal:** Q&A scoped to the uploaded lease (and its jurisdiction's statutes), not general legal chat.

Tasks:
- Chat endpoint retrieval-augmented over: the current document's clauses + the jurisdiction's statute KB. No open-ended general legal advice.
- Quick actions: "Explain this simply," "Why was this flagged?," "What should I check here?"
- Guardrails: if asked something outside the document/jurisdiction scope, the system says so rather than guessing; if asked for a definitive legal conclusion ("is this enforceable"), it hedges per the Phase 0 legal-safety rule.

**Definition of Done:**
- Manual adversarial test: attempt to get the chat to (a) answer about a different lease/jurisdiction than the one loaded, (b) give a definitive "yes this is legal/illegal" answer. It should decline or redirect both times.
- Normal-path test: the three quick actions produce grounded, on-topic answers for at least 5 different clauses across risk levels.

---

## Phase 6 — Frontend: highlighting UI, clause detail, obligation map

**Goal:** the actual end-to-end user experience.

Tasks:
- Upload flow with progress state (extraction → segmentation → classification → analysis).
- Document view with GREEN/YELLOW/RED clause highlighting.
- Clause detail panel: explanation, matched statute citation(s) with source link and "last verified" date, related-clause links, chat entry point.
- Lease obligation map view (tenant must-do / landlord can-do / payments / key dates), generated from the analyzed clauses.
- Jurisdiction selector shown clearly, with a visible note when a jurisdiction isn't yet supported.

**Definition of Done:**
- Full manual walkthrough works end-to-end on a real test document: upload → see highlights → open a clause → see explanation + citation → ask a follow-up in chat → view obligation map.
- UI clearly shows the legal disclaimer and the "last verified" date on any statute citation.
- Basic responsive check (usable on a phone-width viewport).

---

## Phase 7 — Testing, privacy, deployment, docs

**Goal:** a live, public, safely-operating prototype.

Tasks:
- Integration tests covering the full pipeline (upload → classify → explain → cite → chat).
- Implement the data-retention policy from Phase 0 rule 8: uploaded documents and extracted text deleted after the stated window unless the user opts to save; document this in a visible privacy note in the UI.
- Deploy backend + Postgres + frontend to the chosen targets from Phase 0.
- `README.md` covers setup, architecture overview, and current jurisdiction coverage.
- Finalize disclaimer and privacy-policy copy (short, plain-language, visible before upload).

**Definition of Done:**
- Deployed URL is publicly reachable and the full flow from Phase 6 works against the deployed instance, not just locally.
- Retention/deletion mechanism verified by test: upload a document, confirm it's gone (or inaccessible) after the retention window in a test run with a shortened window.
- `PROGRESS.md` shows all phases 0–7 checked off with their recorded metrics (segmentation accuracy, classifier F1, grounding pass rate, coverage report).

---

## Phase 8 — Post-MVP backlog (do not start until Phases 0–7 are live and stable)

These are differentiation/growth features discussed separately — sequence them after the core product is proven, not folded into the MVP:

- Negotiation/redline assistant (suggest counter-language for flagged clauses)
- Post-signing utility layer (extract key dates into reminders)
- Two-sided fairness scoring (flag landlord-unfavorable clauses too) — opens a B2B path
- Crowdsourced, anonymized clause benchmark across users
- Additional jurisdictions beyond the two pilots
- OCR quality improvements / handling messier scans
- B2B API for property managers/agencies

Do not let Claude Code start on any of these until it has explicitly confirmed Phases 0–7 are complete and stable, per the rules in Section 0.

---

## Appendix: `PROGRESS.md` template (create this in Phase 0)

```markdown
# LeaseLens Build Progress

- [ ] Phase 0 — Scaffolding & environment
- [ ] Phase 1 — Document ingestion & clause segmentation
- [ ] Phase 2 — Dataset audit & risk classifier
- [ ] Phase 3 — Statute knowledge base (pilot jurisdictions)
- [ ] Phase 4 — LLM explanation layer & cross-clause detection
- [ ] Phase 5 — Document-aware chat
- [ ] Phase 6 — Frontend: highlighting, clause detail, obligation map
- [ ] Phase 7 — Testing, privacy, deployment, docs
- [ ] Phase 8 — Post-MVP backlog (not started until above are done)

## Phase notes & metrics
(record actual measured results here as each phase completes — segmentation accuracy %, classifier F1, grounding pass rate %, coverage %, etc.)
```
