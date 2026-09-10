# LeaseLens Build Progress

- [x] Phase 0 — Scaffolding & environment
- [ ] Phase 1 — Document ingestion & clause segmentation
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
