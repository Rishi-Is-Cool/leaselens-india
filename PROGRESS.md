# LeaseLens Build Progress

- [x] Phase 0 — Scaffolding & environment
- [ ] Phase 1 — Document ingestion & clause segmentation (segmentation done and measured;
      blocked on Postgres availability, OCR samples, and test-set size)
- [ ] Phase 2 — Dataset audit & risk classifier
- [ ] Phase 3 — Statute knowledge base (pilot jurisdictions)
- [ ] Phase 4 — LLM explanation layer & cross-clause detection
- [ ] Phase 5 — Document-aware chat
- [ ] Phase 6 — Frontend: highlighting, clause detail, obligation map
- [ ] Phase 7 — Testing, privacy, deployment, docs
- [ ] Phase 8 — Post-MVP backlog (not started until above are done)

## Phase notes & metrics

(record actual measured results here as each phase completes — segmentation accuracy %,
classifier F1, grounding pass rate %, coverage %, etc.)

### Phase 0 — Scaffolding & environment

**Completed:** 2026-09-10 — all four exit criteria met and verified.

**Environment (measured on the dev machine):**

| Tool | Version |
| --- | --- |
| Python | 3.13.2 |
| Node | 22.14.0 |
| npm | 11.19.0 |
| git | 2.49.0 |
| Docker | not installed |

A local PostgreSQL 17.4 service is installed and running on this machine, but the
project uses **Supabase** (hosted Postgres) instead — decided during Phase 0.

**Stack decisions locked (per handoff §1, not to be relitigated mid-build):**

- Backend: FastAPI + SQLAlchemy 2.x, `psycopg` (v3) driver
- Frontend: React 18 + Vite 6 + TypeScript (Next.js considered and declined — the
  backend is Python, the frontend is a pure API consumer, and no SSR/SEO need exists)
- Database: **Supabase** hosted Postgres. Chosen over the local instance for zero-ops
  managed hosting and first-class `pgvector`, which Phase 3 embedding retrieval needs.
- Deployment target: **Render** (backend) + **Supabase** (database) + **Vercel** (frontend)

**Supabase connection notes (both are real failure modes, handled in `backend/app/db.py`):**

- Direct-connection host `db.<ref>.supabase.co` is IPv6-only on new projects; use a
  pooler URI instead.
- The transaction pooler (PgBouncer, port 6543) cannot replay psycopg3's server-side
  prepared statements, so `prepare_threshold` is set to `None` when a pooler is detected.

**Exit criteria:**

| Criterion | Result |
| --- | --- |
| `curl /health` returns 200 from a running backend | **pass** — HTTP 200, `{"status":"ok"}` |
| Frontend loads and visibly shows a successful health-check response | **pass** — localhost:5173 renders `API status: ok`, `Database: connected — Postgres 17.6` |
| `PROGRESS.md` created with all phases checklisted | **pass** |
| Postgres reachable from the backend | **pass** — Supabase Postgres **17.6** via session pooler `aws-0-ap-northeast-2.pooler.supabase.com:5432` |

`pgvector` **0.8.2** confirmed available on the instance (not yet installed —
Phase 3 will `CREATE EXTENSION vector`). `pg_trgm` 1.6 also available.

Backend test suite: **3 passed** (`backend/tests/test_health.py`), covering the 200
response, the payload shape, and a regression guard that a DB error never leaks the DSN
(and therefore the password) into the health payload.

Frontend production build: **clean** (`tsc -b && vite build`, 28 modules).

**Owed to later phases (deliberately not built yet):**

- Legal disclaimer component — required by handoff rule 6 on every screen showing AI
  output. Phase 0 renders no AI output; this lands in Phase 6.
- `data/` holds only a `.gitkeep`. The ~1,846-clause labeled dataset (Phase 2) and the
  statute KB (Phase 3) are not present yet and must be sourced before those phases.

### Phase 1 — Document ingestion & clause segmentation

**Status:** in progress (2026-09-20). Extraction, segmentation, and Postgres persistence
are complete, measured, and verified end to end over live HTTP. Two exit criteria remain
open, both awaiting test material rather than code: the corpus is 5 documents rather than
8–10, and no scanned samples exist yet to exercise the OCR fallback.

**Operational note.** The Supabase project paused itself after ~7 days idle, which took
the database offline between sessions (the direct host stops resolving and the pooler
returns "Tenant or user not found"). Restoring it from the dashboard brought it back on
the same credentials. Expect this recurrence on the free tier; it matters for Phase 7.

**Measured segmentation accuracy: 100.0% (56 / 56 clauses), 0 mid-sentence fragments.**

Reproduce with `python scripts/run_pipeline.py` (add `--raw` to dump extracted text).

| Document | Style under test | Clauses | Expected |
| --- | --- | --- | --- |
| 01 Maharashtra | numbered + ALL-CAPS run-in headings | 13 | 13 |
| 02 Delhi | run-in headings, no numbering | 12 | 12 |
| 03 Karnataka | numbered + lettered sub-points | 12 | 12 |
| 04 Tamil Nadu | prose only, no numbering or headings | 7 | 7 |
| 05 Uttar Pradesh | ARTICLE headings + 2.1 / 2.3(a) nesting | 12 | 12 |

Counts exclude one synthetic header line per file (see *Fixture caveat* below).
Accuracy penalises over- and under-splitting alike rather than capping at the expected
count, so a segmenter that shattered clauses would score below 100, not at it.

**How paragraphs are recovered.** PDF extraction yields no blank lines between
paragraphs, so boundaries come from line geometry: within a paragraph lines sit ~15px
apart, between paragraphs ~25px. The baseline is the **most frequent** gap, not the
median — leases commonly use three spacings (within-paragraph, heading-to-body,
between-blocks) and the median lands on the middle one whenever body lines are not an
outright majority, which collapsed an entire page into a single clause during
development. This is what makes the no-numbering Tamil Nadu document tractable.

**Design decisions worth knowing (raise these before Phase 2 builds on them):**

- **Lettered sub-points stay with their parent clause.** Karnataka's `4. (a)...(b)...(c)`
  and UP's `2.3 (a)...(b)` are inline within one numbered item, so the document's own
  numbering is treated as the clause unit. Splitting them would need intra-paragraph
  cuts and would detach each fragment from its governing sentence.
- **Section banners scope every clause beneath them**, whether standalone
  (`TERMS AND CONDITIONS:`) or sharing a paragraph with the first clause they govern.
- **Clause text retains the document's own numbering** (`2.1 The term...`) for
  traceability, except where a run-in caps heading is lifted into `section_heading`.
- `clause_id` is a per-document sequential id (`c001`); the surrogate DB primary key is
  separate. `order` is stored as `order_index` because `order` is reserved in SQL, and is
  mapped back to `order` in the API response so the published contract is unchanged.

**Fixture caveat.** Every test PDF carries a generated second line —
`State: Tamil Nadu | City: Chennai | Format: Plain prose paragraphs, no numbering` —
which is not lease content and would not appear in a real document. It is **not**
special-cased in the segmenter (doing so would be tuning to the test set), so it surfaces
as one extra clause per file and is excluded from the counts above. Worth regenerating
the fixtures without it: besides polluting output, it states the expected format, which
any future ML-based segmenter would learn to cheat from.

**Exit criteria:**

| Criterion | Result |
| --- | --- |
| Rule-based segmentation across all structural styles | **pass** — 100.0%, target was ≥90% |
| No clause split mid-sentence / no clauses merged | **pass** — 0 fragments, enforced by test |
| Clauses stored in Postgres, linked to source document | **pass** — 61 clause rows across 5 documents, FK `on delete cascade`, order preserved |
| `POST /documents` → `GET /documents/{id}` round trip | **pass** — all 5 upload 201 and read back 200 over live HTTP |
| Pipeline runs on 8–10 documents | **blocked** — 5 supplied |
| 2–3 scanned/photographed documents, OCR demonstrably triggering | **blocked** — none supplied; Tesseract binary also not installed |

Backend test suite: **20 passed**, including per-document clause counts, a mid-sentence
guard, the ≥90% accuracy threshold as a regression gate, and a test pinning the
`{clause_id, section_heading, text, order}` contract.
