# LeaseLens Build Progress

- [x] Phase 0 — Scaffolding & environment
- [ ] Phase 1 — Document ingestion & clause segmentation (100% on a 9-document corpus;
      blocked only on scanned samples to exercise the OCR fallback)
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

**Status:** in progress (2026-09-21). Extraction, segmentation, and Postgres persistence
are complete, measured, and verified end to end over live HTTP. The corpus now stands at
9 documents, meeting the 8–10 target. One exit criterion remains open and awaits test
material rather than code: no scanned samples exist yet to exercise the OCR fallback.

**Operational note.** The Supabase project paused itself after ~7 days idle, which took
the database offline between sessions (the direct host stops resolving and the pooler
returns "Tenant or user not found"). Restoring it from the dashboard brought it back on
the same credentials. Expect this recurrence on the free tier; it matters for Phase 7.

**Measured segmentation accuracy: 100.0% (92 / 92 clauses), 0 mid-sentence fragments —
across the 9 synthetic documents only.** The three real official templates are a separate,
currently failing class; their numbers are reported below rather than averaged in.

Reproduce with `python scripts/run_pipeline.py` (add `--raw` to dump extracted text).

| Document | Style under test | Clauses | Expected |
| --- | --- | --- | --- |
| 01 Maharashtra | numbered + ALL-CAPS run-in headings | 13 | 13 |
| 02 Delhi | run-in headings, no numbering | 12 | 12 |
| 03 Karnataka | numbered + lettered sub-points | 12 | 12 |
| 04 Tamil Nadu | prose only, no numbering or headings | 7 | 7 |
| 05 Uttar Pradesh | ARTICLE headings + 2.1 / 2.3(a) nesting | 12 | 12 |
| 06 West Bengal | Roman-numeral clauses (I, II, III) | 10 | 10 |
| 07 Punjab | numbered caps headings + bullet schedule | 8 | 8 |
| 08 Rajasthan | numbered + embedded escalation schedule | 10 | 10 |
| 09 Gujarat | `Clause N.` numbering + bare caps heading | 8 | 8 |

**Note on numbering.** Document 09 is the Gujarat holdout, renamed from `06` when the
fixture generator later produced its own `06` (West Bengal). Renumbering it kept both.

Accuracy penalises over- and under-splitting alike rather than capping at the expected
count, so a segmenter that shattered clauses would score below 100, not at it.

**Held-out document (2026-09-20).** Document 06 was run blind, having been written
without the segmenter in view, and it failed in two ways that the first five could not
have caught. Both are fixed and regression-tested; the document is now part of the
corpus, so its value as a blind test is spent.

- *`Clause N.` numbering was unrecognised.* Numbering was matched as a bare `1.`, so
  `Clause 1. Premises.` matched nothing at all — neither the number nor its heading.
  Numbering now accepts a spelled-out `Clause` / `Article` / `Section` / `Para` prefix.
- *A caps heading run into its body was not extracted.* Every heading style in the first
  five carried a positional cue: a preceding number (Maharashtra), a trailing colon
  (Delhi), a standalone line, or an `ARTICLE` banner (UP). Gujarat's
  `USE OF PREMISES The Tenant shall...` has none, so the heading stayed inside `text`.
  A caps run followed by a title-case word is now recognised; the following word's case
  is what distinguishes it from an ordinary opening like `THIS LEASE DEED is executed`.

Lifting run-in headings out of sentences needs a guard, since `2. The Tenant shall pay
... Rs. 28,000` closes its first full stop after `Rs`. Headings are therefore capped at 5
words and 45 characters, which is asserted by a test.

**Second held-out round (2026-09-21).** West Bengal (Roman numerals) and Rajasthan
(embedded escalation schedule) passed untouched. Punjab failed in two further ways:

- *A numbered caps heading closed by no full stop.* `1. PREMISES AND TERM The Landlord
  lets out...` was matched by neither rule — the period-terminated pattern needs a full
  stop, and the bare-caps pattern is anchored at the start of the paragraph, so the
  leading number blocked it. The bare-caps rule now accepts an optional number prefix.
- *A bullet list became four clauses.* List items carry their own line spacing, so each
  arrived as its own paragraph and split away from the heading introducing them.
  Consecutive bullet lines now attach to the clause above.

**Filled official form (2026-09-21) — silent content loss, since fixed.** A completed
Tamil Nadu deed (`test/tamil_nadu_FILLED_lease_deed.pdf`) dropped four pieces of source
text outright. One root cause accounted for most of it: the minimum clause-length guard
ran *before* heading detection, so any heading shorter than 20 characters — `WHEREAS`,
`(DEMISED PREMISES)` — was discarded before it was ever examined. Also fixed:

- The title-block scan stopped only at `.`, `;`, `!`, `?`, so an opening line ending in a
  colon was absorbed into the masthead. It now stops at a colon too.
- `BETWEEN` was detected but `AND` was not. Not word-matching, as suspected — `BETWEEN`
  carries a colon in this document and `AND` does not. Both are now matched as deed
  connectors, which are fixed keywords of the instrument in the same way `ARTICLE` is.
- A section heading carried onto the closing attestation. The heading now resets at the
  closing formula and at an all-caps divider ending in a colon or semicolon.
- Witness signing slots (`1. ____`, `2. ____`) merged into one line; numbered slots are
  now recognised alongside labelled ones and stay distinct.

Section banners gained their own bucket: a clause carrying its own run-in heading never
adopts the banner above it, so banner text was being lost even when correctly detected.

**Real official templates (2026-09-21) — a class the segmenter does not yet handle.**
Three genuine state-government draft templates were run: Tamil Nadu Registration Dept,
Maharashtra IGR, and West Bengal Directorate of Registration and Stamp Revenue, held in
`official_format/`. These are blank, fillable forms rather than executed agreements.

*Extraction is clean.* Blank-fill markers survive intact — underscore runs
(`____________`), numbered parenthetical blanks (`(4)`, `(16)`), and dotted leaders. The
dotted blanks are genuine `U+2026 HORIZONTAL ELLIPSIS` (103 in the West Bengal form) and
there is not one `U+FFFD` replacement character or `(cid:N)` artifact across the three.
A long blank run does **not** cause a spurious paragraph split.

*Segmentation under-splits badly.* These forms set numbered clauses as continuous prose
with no extra leading between them, so paragraph geometry — the signal the whole
segmenter rests on — gives nothing to cut on. Measured as the share of numbered clause
markers in the source that begin their own clause object:

| Document | Numbered in source | Clause objects | Recall |
| --- | --- | --- | --- |
| Tamil Nadu official | 11 | 11 | 18% |
| Maharashtra official | 30 | 76 | 13% |
| West Bengal official | 16 | 14 | 6% |

Clause-object counts above shifted after the filled-form fixes restored dropped
paragraphs; the recall figures predate those fixes and are due a re-measure.

Maharashtra is a different failure again: most of its 13 pages are a five-column table
(`Cl.no | Title | Clause | Compulsory | data to be filled`), which extraction flattens
into interleaved prose. Its 57 objects are mostly table rows, not clauses.

Three further defects this class exposes, all currently unfixed:

- The title-block scan stops at `.`, `;`, `!` or `?`, so Tamil Nadu's opening line —
  which ends in a colon — is swallowed as masthead and lost.
- Cross-page rejoin only fires when the continuation opens lower case, so Tamil Nadu's
  `LESSEE agrees to take...` starts a clause mid-sentence.
- Signing lines in these forms (`LESSOR   LESSEE`, `Signature of the Lessor`) carry no
  underscore run, so the signature block comes back empty and those lines are dropped.

These numbers are reported separately rather than folded into the corpus accuracy below:
averaging a failing document class into a passing one would hide it.

**Font-mapping artifact.** Punjab's bullet glyph extracted as `(cid:127)`. pdfminer
(under `pdfplumber`) emits that form when a font supplies no usable ToUnicode entry;
PyMuPDF resolves the same glyph to `U+2022` and produces no artifacts, so this is an
extractor limitation rather than a damaged file. Extraction now maps the bullet-like cid
codes to `•`. Unrecognised codes are deliberately left visible — cid numbers are
font-specific, so guessing would silently substitute a wrong character. A test asserts no
`(cid:` artifact survives anywhere in the corpus. The fuller fix, if these recur on real
scans, is to move text extraction to PyMuPDF; the geometry logic would need porting with
it, so it is not worth doing on one known glyph.

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

**Content coverage: 96.6% minimum, 99.2% mean across 13 documents, with zero
unexplained losses.** Clause-count accuracy cannot see text that is *dropped* rather than
mis-split — a segmenter that silently discards a paragraph still reports the expected
clause count — so coverage is now measured and gated separately by
`app/ingestion/coverage.py`. It compares source tokens against everything emitted and
fails the build on any loss that is not an absorbed structural marker. The residual 0.4–3.4%
is exactly those markers: the `Clause` / `ARTICLE` keyword, the clause number, and the
full stop closing a lifted heading.

This check was added *before* fixing the filled-form bug below, and it reproduced the
loss immediately. It would have caught it the day it was introduced.

**Nothing from the source is discarded.** Segmentation returns four parts — a title
block, section headings, the clauses, and a signature block — and every paragraph of the
source lands in at least one of them. Signing lines (`OWNER: ______`) were previously stripped and
dropped, which silently lost them; they are now captured, persisted on the document, and
returned by the API. A test asserts per document that no source word disappears.

The one permitted loss is structural markers consumed when a heading is lifted out — the
`Clause` / `ARTICLE` keyword, the clause number, and the full stop closing the heading.
No substantive lease text is affected. **Open question:** clause numbering is citable
content, so if Phase 2 or a user-facing view needs "Clause 4", it should be carried in a
field rather than absorbed. That would add to the published clause contract, so it needs
a decision before downstream work depends on the current shape.

**Title block.** A lease opens with its title, and sometimes a filing or reference line,
before the operative text starts. These are no longer emitted as clauses: the block runs
from the top until the first paragraph that terminates like prose, bounded to three
paragraphs and 150 characters a line so an unusual document cannot swallow real clauses.
The rule is positional, not a pattern match on the fixtures' `State: ... | Format: ...`
line — matching that text would tune the segmenter to the test set.

Those generated lines are still worth removing from the fixtures, because each states the
document's expected format, which any future ML-based segmenter would learn to cheat
from.

**Exit criteria:**

| Criterion | Result |
| --- | --- |
| Rule-based segmentation across all structural styles | **pass** — 100.0%, target was ≥90% |
| No clause split mid-sentence / no clauses merged | **pass** — 0 fragments, enforced by test |
| Clauses stored in Postgres, linked to source document | **pass** — 61 clause rows across 5 documents, FK `on delete cascade`, order preserved |
| `POST /documents` → `GET /documents/{id}` round trip | **pass** — all 5 upload 201 and read back 200 over live HTTP |
| Pipeline runs on 8–10 documents | **pass** — 9 supplied |
| 2–3 scanned/photographed documents, OCR demonstrably triggering | **blocked** — none supplied; Tesseract binary also not installed |

Backend test suite: **63 passed**, including per-document clause counts, a mid-sentence
guard, the ≥90% accuracy threshold as a regression gate, a test pinning the
`{clause_id, section_heading, text, order}` contract, and one test per heading style so
a future change cannot silently narrow heading detection again.
