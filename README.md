# LeaseLens

AI-assisted lease analysis: upload a lease, get clauses segmented, risk-flagged
(GREEN / YELLOW / RED), and explained with citations traced to a curated statute
knowledge base.

> **Not legal advice.** LeaseLens surfaces AI-assisted information and flags
> *potential* concerns. Laws vary by location and change over time — verify with a
> qualified professional before acting.

**Build status:** Phase 0 (scaffolding). See [PROGRESS.md](PROGRESS.md) for what is
built and what is measured. The phased plan lives in
[LeaseLens_ClaudeCode_Handoff.md](LeaseLens_ClaudeCode_Handoff.md).

## Architecture

```
frontend/  React 18 + Vite + TypeScript   →  calls the API, renders results
backend/   FastAPI + SQLAlchemy           →  ingestion, classification, explanation
data/      clause dataset + statute KB    →  (populated in Phases 2 and 3)
```

Postgres stores documents, clauses, classifier output, chat history, and the statute
knowledge base.

## Setup

Requires Python 3.11+, Node 18+, and a Supabase project (hosted Postgres).

**1. Configure environment**

```bash
cp .env.example .env
```

**2. Get your Supabase connection string**

In the Supabase dashboard: **Project Settings → Database → Connection string**. Copy the
**Session pooler** or **Transaction pooler** URI — not the direct-connection host
(`db.<ref>.supabase.co`), which is IPv6-only on new projects and fails on IPv4-only
networks.

Paste it into `.env` as `DATABASE_URL`, changing the scheme from `postgresql://` to
`postgresql+psycopg://`. The backend adds `sslmode=require` automatically, and disables
psycopg's prepared statements when it detects the transaction pooler (PgBouncer cannot
replay them).

**3. Backend**

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate      # Windows;  source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs at http://localhost:8000/docs, health at http://localhost:8000/health.

**4. Frontend**

```bash
cd frontend
npm install
npm run dev
```

Opens at http://localhost:5173 and displays the backend health check.

## Tests

```bash
cd backend && pytest
```

## Jurisdiction coverage

Pilot jurisdictions are **Maharashtra** and **Delhi** (Phase 3). Statute citations are
only shown for jurisdictions present in the curated knowledge base; unsupported
jurisdictions are labelled as such rather than answered from model memory.

## Deployment

Backend on Render, database on Supabase, frontend on Vercel. Committed in Phase 0 — see
PROGRESS.md.
