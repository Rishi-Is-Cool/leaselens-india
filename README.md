# LeaseLens

AI-assisted review of Indian rental agreements. Upload a lease (PDF, or a scan or photo)
and LeaseLens splits it into clauses, rates how much attention each one deserves, matches
it against your state's rental law with links to the official text, explains it in plain
language, and answers questions about that one lease.

**Live:** https://leaselens-india.vercel.app

> **Not legal advice.** LeaseLens surfaces AI-assisted information and flags *potential*
> concerns. It never says a clause is "legal" or "illegal". Laws vary by state and change
> over time, so verify with a qualified professional before acting.

## What it does

| Step | How |
| --- | --- |
| **Read the lease** | pdfplumber for text PDFs, Tesseract OCR for scans and photos (per page, so mixed documents work) |
| **Split into clauses** | Rule-based segmentation using paragraph geometry, numbering and headings. 100% clause recall on 9 synthetic leases from different states |
| **Rate each clause** | Looks standard / Worth a look / Needs attention. An LLM (zero-shot), with a trained fallback (logistic regression on MiniLM sentence embeddings) when no LLM is available |
| **Match the law** | Deterministic retrieval from a curated statute knowledge base (Maharashtra Rent Control Act, Delhi Rent Control Act, Transfer of Property Act), each entry with its official source URL and last-checked date. The state is inferred from the lease and confirmed by the user |
| **Explain** | Plain-language "what this says / why it matters", grounded in the clause text and the retrieved statutes only |
| **Connect clauses** | Embedding shortlist, then the LLM confirms pairs a tenant should read together (for example, termination notice and deposit deductions) |
| **Answer questions** | Document-aware chat with quick actions on every clause (explain simply / why this rating / what to check) |

### Guardrails (enforced in code, not just prompted)

- Every answer is checked before it is shown. If it gives a legal verdict ("is
  illegal/enforceable/void"), cites a law that was not retrieved, or invents an amount or
  date that is not in the lease, it is sent back for one rewrite. If it still fails, a
  safe answer replaces it.
- A statute is shown only if it was retrieved for this lease. Any other citation the
  model produces is dropped.
- Questions about another state's law are refused before any model call.
- Raw provider error text, which includes account IDs, never reaches the browser.

### Privacy

- No accounts. Each browser gets a random ID, and a lease is only ever served back to
  the browser that uploaded it (`backend/app/ownership.py`).
- Every upload is hard-deleted after 24 hours, or immediately with "Delete this lease
  now". The clauses, the review and anything derived from them are deleted with it.
- Embeddings of uploaded leases are never cached to disk.
- Per-visitor hourly limits on uploads, reviews and chat protect the free-tier quotas
  (`backend/app/ratelimit.py`).

## Architecture

```
frontend/  React 18 + Vite + TypeScript  -> Vercel
backend/   FastAPI + SQLAlchemy 2          -> Docker on Render (free, 512 MB)
           ingestion/  extract + segment
           classifier/ LLM + trained fallback, embeddings (PyTorch or ONNX Runtime)
           statute_kb/ retrieval over data/statute_kb/
           explain/    explanations, grounding checks, cross-clause links
           analysis/   background review job with progress
           chat/       document-aware Q&A with guardrails
database   Supabase Postgres: documents, clauses, analyses (JSONB)
LLM        any OpenAI-compatible endpoint (Groq free tier by default)
```

The hosted API runs the embedding model on ONNX Runtime instead of PyTorch so it fits a
512 MB instance (about 350 MB peak for a full review). The two backends give the same
vectors (cosine > 0.9999) and the same risk labels on all 195 evaluation clauses;
`tests/test_embeddings_backend.py` keeps them in step.

If the API is asleep or unreachable, the frontend still shows the saved sample reviews
bundled with the site, and switches uploads on once the API answers.

## Run locally

Requires Python 3.13, Node 18+, a Supabase project and, optionally, a Groq API key.

```bash
cp .env.example .env          # then fill in DATABASE_URL (and LLM_API_KEY for explanations + chat)
```

For `DATABASE_URL`, use the Supabase **session pooler** URI (Project Settings → Database →
Connection string) with the scheme changed to `postgresql+psycopg://`.

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows; source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

Without `LLM_API_KEY`, everything except explanations, cross-clause links and chat still
works. Risk levels then come from the offline model, and the UI says so.

## Tests

```bash
cd backend && pytest
```

CI (GitHub Actions) runs the backend suite against a Postgres service and builds the
frontend on every push.

## Deploy

**API (Render, free).** In Render: New → Blueprint → pick this repository. `render.yaml`
builds the `Dockerfile`. When asked, enter `DATABASE_URL` and, optionally, `LLM_API_KEY`.
The free instance sleeps after 15 idle minutes, and the frontend shows a "waking up"
notice while it starts.

**Frontend (Vercel).** The project root is `frontend/`. `frontend/.env.production` sets
`VITE_API_BASE_URL` to the Render URL. With `VITE_STATIC_DEMO=true` instead, it builds a
backend-free demo of the saved reviews.

## Jurisdiction coverage

Statute matching covers **Maharashtra** and **Delhi**, plus central law. Leases from
other states still get clause splitting, risk levels, explanations and chat. They are
labelled as having no state law check, and are never answered from the model's memory.
