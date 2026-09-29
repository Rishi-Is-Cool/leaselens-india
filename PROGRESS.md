# LeaseLens Build Progress

- [x] Phase 0 — Scaffolding & environment
- [ ] Phase 1 — Document ingestion & clause segmentation (100% on a 9-document corpus;
      blocked only on scanned samples to exercise the OCR fallback)
- [x] Phase 2 — Dataset audit & risk classifier (LLM zero-shot shipped as default, beats
      trained classifier and holds up on an Indian-domain sanity check; see notes)
- [x] Phase 3 — Statute knowledge base (Person C's work, integrated 2026-09-29 after
      2 fixes; 60/60 retrieval tests, 100%/100% coverage on the representative sample)
- [x] Phase 4 — LLM explanation layer & cross-clause detection (100% grounding-guardrail
      pass rate on the full Phase 1 corpus, 29 cross-clause connections found)
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

**Fixes applied 2026-09-26 (working tree, not yet committed).**

- *`clause_number` added to the clause contract.* Clauses now carry the number printed in
  the source (`"4"`, `"2.1"`, `"IV"`, or `null` when unnumbered) as its own field, so it
  survives heading lifting. It is stored in `clauses.clause_number` (added to an existing
  table by `create_tables()` with `ALTER TABLE ... IF NOT EXISTS`) and returned by the API.
  Clause `text` is unchanged. Phase 2/4 should consume this field rather than parse text.
- *Official-template segmentation.* The segmenter now splits a paragraph that holds several
  consecutively numbered clauses (`_split_numbered_runs`), accepting only the next number in
  sequence, hierarchical sub-numbers (`2.1)`), or a restart at 1. Page-break rejoin also
  recognises a defined term opening a continuation ("LESSEE agrees ..."), and a numbered
  paragraph is no longer glued onto a bare label above it. Measured share of the form's
  numbered clauses recovered as their own clause object (top-level numbers):

  | Document | Before | After |
  | --- | --- | --- |
  | Tamil Nadu official | 18% | 11 / 11 (100%) |
  | West Bengal official | 6% | 16 / 16 (100%) |
  | Maharashtra official | 13% | 12 / 12 (100%) in the agreement section |

  Maharashtra remains unresolved: pages 7-13 are a five-column data-entry table that repeats
  the agreement text with "Compulsory / data to be filled" annotations, so the document still
  yields ~98 clause objects, including duplicates and blank-marker numbers such as `(23)`.
  Handling that table needs a decision on what the annotation columns are (form metadata,
  not lease text). Zero unexplained source-text loss on all three forms (test-gated).
- *Test corpus PDFs corrupted by git line-ending conversion.* `core.autocrlf=true` rewrote
  LF to CRLF inside the binary PDFs on checkout; `06_west_bengal` then failed to parse
  (10 tests failing). Restored byte-exact from git and added `.gitattributes` marking
  `*.pdf`/images as binary. Anyone else who cloned with autocrlf on should re-checkout.
- *West Bengal official form* has a near-empty page (14 characters) that also holds an image,
  so the extractor routes it to OCR: uploading it to the API returns 503 until Tesseract is
  installed. Real behaviour, not yet exercised on a scan.

Backend test suite: **70 passed**. OCR remains unproven: no scanned samples, no Tesseract.

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

### Phase 2 — Dataset audit & risk classifier

**Status:** functionally complete (2026-09-27). All required deliverables are built, tested
and measured: audit, leak-checked split, all three baselines on the same held-out set,
`classify_clause()`, and the Indian-domain check. Two informational items remain open (below)
but do not block the pipeline. Full method, tables and the ship decision's reasoning:
[`data/classifier_eval.md`](data/classifier_eval.md). Reproduce with `python
scripts/run_phase2.py` from `backend/` (needs `LLM_API_KEY`, a free-tier key, in `.env`);
`python scripts/run_indian_check.py` refreshes just the Indian section.

**Audit (before any modeling).**

| Check | Result |
| --- | --- |
| Rows | 1,682 (docs said ~1,846; confirmed 1,682 with the owner) |
| Class balance | GREEN 811 (48.2%), YELLOW 584 (34.7%), RED 287 (17.1%) |
| Exact duplicates | 0 |
| Near-duplicates (cosine >= 0.95, all-MiniLM-L6-v2) | 283 clauses in 123 clusters; **160 removed -> 1,522**. No cluster mixed labels. Median distance between twins 490 rows: the same boilerplate copied across different leases. |
| Lease ID column | **none** — `clause_id` is a global row number |

**Split (leak-checked).** No lease ID exists, so contiguous blocks of 30 rows stand in for
leases (rows are in lease order) and whole blocks go to train or test, after dedup. Train
1,199 / test 323 (class mix matches). Verified on the real split: 0 shared blocks, 0 shared
clause IDs, highest test-to-train cosine 0.944 (< 0.95). 19 of 323 test clauses (5.9%) still
have a train paraphrase >= 0.90 — a small optimistic bias, reported not hidden. The block
split is a **proxy**: a real lease can straddle a block edge.

**Results (same 323-clause held-out test set).**

| Approach | n | Accuracy | Macro-F1 |
| --- | --- | --- | --- |
| Majority class (always GREEN) | 323 | 48.0% | 0.216 |
| Trained: MiniLM embeddings + logistic regression, calibrated | 323 | 65.9% | 0.642 |
| **LLM zero-shot (`qwen/qwen3.8-27b`, free tier)** | 323 | **76.5%** | **0.758** |
| LLM few-shot (6 examples) | 120 of 323 — quota cut the run short | 71.7% | 0.677 |
| Ensemble (50/50 trained + LLM zero-shot) | 323 | 76.5% | 0.758 |

Hyper-parameters (C=3, balanced class weights) were chosen by grouped 5-fold CV on train
only. LLM zero-shot beats the trained classifier by 10.6 points accuracy and 0.116 macro-F1,
and wins on every class including RED (0.804 vs 0.571 F1) — the class the product most needs
to catch. Few-shot prompting did not help where it could be measured, and the ensemble did
not beat the LLM alone, so neither is shipped. Confidence is calibrated for both models (ECE
0.107 LLM, 0.053 trained); full per-class F1 and confusion matrices are in
`classifier_eval.md`.

**Indian-domain check — complete for all three approaches, fully owner-reviewed, and now
RED-inclusive (31 clauses: 27 real from the official Tamil Nadu, West Bengal and Maharashtra
forms, plus 4 hand-authored RED examples the blank templates don't contain any of;
`data/indian_eval_set.csv`). Updated 2026-09-28 after the owner reviewed all 27 original
proposed labels — 4 were corrected (IN-12, IN-20, IN-23, IN-25).**

| Approach | Indian sample accuracy | US test accuracy | Change |
| --- | --- | --- | --- |
| Trained classifier | 45.2% (95% CI 29–62%) | 65.9% | **−20.7 pts** |
| LLM zero-shot | 64.5% (95% CI 47–79%) | 76.5% | −12.0 pts |
| LLM few-shot | 71.0% (95% CI 53–84%) | 71.7% | −0.7 pts |
| Majority baseline (always GREEN) | 58.1% | 48.0% | — |

**These overall numbers are lower than the previous (unreviewed, 27-clause) pass reported —
that is a correction to the ground truth, not a model regression.** All predictions are
identical and cached; only 4 true labels changed. On exactly those 4, both models had scored
as "correct" only because they agreed with Claude's own first-pass proposal, not because the
judgment was sound — e.g. IN-20 describes the standard Leave & License structure under the
Maharashtra Rent Control Act, which both the original proposal and the LLM initially
over-flagged as risky, plausibly because that legal structure is unfamiliar outside Indian
tenancy law. The lower numbers reflect a better yardstick.

**RED recall is the clean result this update was for.** The 27 real clauses contain no RED
text (blank official templates are deliberately neutral), so 4 were hand-authored to close
that gap: full deposit forfeiture including normal wear and tear, an uncapped unilateral rent
increase, termination/re-entry with no notice, and a disproportionate per-day penalty. **LLM
zero-shot and few-shot each caught all 4 of 4 (100% recall). The trained classifier caught
only 2 of 4** — missing the deposit-forfeiture and rent-increase clauses specifically, both
of which read as ordinary rent/deposit terms on the surface with no dramatic keywords. This
is the most direct test yet of the product's actual job, and it favors the LLM decisively.

**Known limitation — domain mismatch (recorded regardless of result, per the owner's explicit
instruction).** The training data is US-style lease language (Landlord/Tenant, "Texas Lease
Agreement", `$`; zero Indian references), while LeaseLens targets Indian leases. The trained
classifier's edge over guessing does not survive the domain shift (it now falls *below* the
Indian sample's own majority baseline by 12.9 points), while the LLM's does, and its RED
recall on Indian text is measured and perfect where the trained classifier's is not. Caveats
that still apply: n=31 is small (a 95% CI of order ±15 points), the 4 RED clauses are
authored, not drawn from a real document (a genuine risky Indian lease may not resemble
them), and the earlier round's "no RED clauses" gap is now closed but the sample is still
tiny. Re-run `python scripts/run_indian_check.py` if more real (not authored) Indian RED
examples are added later.

**Decision: ship LLM zero-shot as the default, trained classifier as an explicit fallback.**
`classify_clause(text)` (`backend/app/classifier/api.py`) defaults to the LLM approach and
automatically falls back to the trained classifier if the LLM call fails for any reason (no
key, rate limit, network error) — this is not a hypothetical: producing the numbers above hit
free-tier daily quota caps on two different Groq models mid-evaluation. The result carries
`approach="trained (llm fallback)"` when that happens, so it is observable. Full reasoning is
in `classifier_eval.md`'s "Decision" section, including the honest operational cost (network
dependency, real rate limits) that a bare accuracy table would hide. `classify_clause()`
returns `label`, `confidence` and per-class `probabilities` (the owner chose label +
confidence over label only, so Phase 4 can hedge its wording), and takes a clause's `text`
directly — confirmed against a handful of live clauses, not just the pre-built test set.

**Open items (informational, non-blocking):** (1) LLM few-shot only finished 120/323 US test
clauses before hitting its daily quota — zero-shot already answers the "is the LLM baseline
good enough" question decisively, so this is not being chased further; re-run
`scripts/run_phase2.py` after a quota reset if a complete few-shot number is wanted. (2) Owner
review of the 27 Indian labels is still pending — re-run `run_indian_check.py` once reviewed.
(3) The Maharashtra-table segmentation question (Phase 1, unresolved) affects what text
`classify_clause()` will actually see for that document class. (4) Result shape should be
confirmed with whoever picks up Phase 4.

**Fallback-path improvement — done (2026-09-29).** The reviewed Indian eval set (above) had
shown `approach="trained"` missing 2 of 4 RED clauses on Indian text - specifically the ones
without alarm-word phrasing. Fixed by adding reviewed synthetic Indian training data (the LLM
stays the default regardless):

- **Step 1.** Generated 195 synthetic Indian-register clauses across 5 states (Leave & License /
  Rent Agreement / Rental Agreement / Lease Deed / Deed of Lease terminology) and 8 topics,
  balanced 65/65/65 GREEN/YELLOW/RED (not the real data's skew), with RED covering both obvious
  and subtle (no-alarm-word) phrasing — `data/synthetic_indian_clauses.csv`.
- **Dedup + leak-free split.** Audit found the 195 rows are 47 underlying templates cloned 2-5x
  across states — a plain split would leak near-duplicates across train/test. Clustered two ways
  (rule-based normalization + an embedding cosine cross-check) and verified by hand: 0 false
  merges, cluster sizes exactly match the generator's own template structure, 0 of 47 templates
  land on both sides of a 75/25 label-stratified split (153 train / 42 test). Details and the
  explainable rule-based-vs-embedding disagreement: `data/synthetic_dedup_split_report.md`.
- **Step 2.** Owner reviewed all 195 rows / 47 templates: rubric sound, consistently applied, no
  mislabels. Two borderline RED calls flagged as defensible judgment calls, not corrections.
  Confirmed every alarm-word phrase in the dataset (e.g. "sole discretion", "any circumstances")
  appears only in RED rows — a real risk that a classifier could pattern-match keywords rather
  than learn the underlying reasoning, and the reason the held-out check below specifically
  breaks out obvious vs. subtle RED.
- **Step 3, decision: option (b).** Train on the 153 train-side synthetic rows only first; hold
  out the 42 test-side rows as a third generalization check the model never saw a template of.
  **Held-out check passed the specific test that mattered**: RED recall on the 42 held-out rows
  was **100% on both obvious (6/6) and subtle, no-alarm-word (6/6)** phrasing — evidence against
  keyword-matching, since a shortcut classifier would show a gap between the two. In the same
  run: US test accuracy held stable (65.9% → 65.0%, macro-F1 unchanged at 0.642) and Indian eval
  accuracy improved (45.2% → 58.1%, RED recall 2/4 → 4/4).
- **Final fit, shipped.** Refit on the original US training data plus **all** 195 synthetic
  clauses (not just the 153 check-only rows) and saved to
  `backend/app/classifier/artifacts/risk_logreg.joblib`. On the still-valid US test and Indian
  eval (neither overlaps the synthetic data): **64.7%** US test (macro-F1 0.640) and **54.8%**
  Indian eval (macro-F1 0.537, RED recall still 4/4) — both real improvements over the
  pre-synthetic baseline (45.2% / 0.401 on the Indian eval). Honestly reported: the fully-refit
  model scores a few points below the 153-row held-out-check model on the Indian eval (58.1%) —
  more synthetic data did not straightforwardly mean better, though it's still a clear net gain
  over no synthetic data. Full numbers and methodology: `data/retrain_fallback_report.md`.
  Reproduce with `backend/scripts/retrain_trained_fallback.py [--final]`.

Backend test suite: **83 passed**, including the leakage checks, calibration, the published
`{clause_id, clause_number, section_heading, text, order}` clause contract, and a test that
`classify_clause()` degrades to the trained model (rather than raising) when the LLM fails.

### Phase 3 — Statute knowledge base (Person C)

**Status:** integrated 2026-09-29, after fixing 2 known issues plus 1 found during the fix.
Person C hand-curated 28 statute entries (Maharashtra 12, Delhi 9, Central 7) covering
security deposit, notice, eviction, maintenance, rent escalation and registration, with a
deterministic jurisdiction-first/topic-second retrieval implementation and citation/
excerpt/source-URL traceability validators. An independent review re-ran their tests rather
than just reading their report, confirming 60/60 retrieval checks pass (including negative
controls: a tampered excerpt, a wrong citation, and a wrong source URL are all correctly
rejected) and 100%/100% coverage on a 20-clause representative sample (honestly caveated by
Person C as illustrative, not the real Phase 1 pipeline's actual output). Real government
source URLs, correct jurisdiction isolation (a Maharashtra query never returns a Delhi
entry and vice versa, even with Central law included).

**Fix 1 — Central ID prefix.** All 7 "Central" jurisdiction entries used a `DL_` (Delhi) ID
prefix instead of `CENTRAL_` (functionally harmless — retrieval filters on the
`jurisdiction` field, which was already correct and tested — but confusing and inconsistent
with the `audit_sources/` file naming for the same entries). Renamed throughout the KB, the
index, and every audit-source file that references them: `CENTRAL_REG_001/002/003`,
`CENTRAL_EVICTION_003/004`, `CENTRAL_MAINT_002/003`.

**Fix 2 — stale audit-source drafts.** `audit_sources/` had "(1)"-suffixed files that didn't
match the id of the final KB entry they document, some genuinely stale, some just oddly
named:

- `CENTRAL_MAINT_001` had two draft versions disagreeing on verification status — one
  claimed `verified_cross_checked_secondary_sources`, the other (later, more cautious)
  downgraded to `pending_primary_source_verification` with a note that India Code's
  listing for the Act said "under updation." Kept the more cautious version as
  authoritative, renamed to match its actual final KB id (`CENTRAL_MAINT_002.json`), and
  moved the superseded draft to `audit_sources/superseded/`.
- `MH_MAINT_002` had two drafts reaching the same conclusion with no verification
  conflict, just a clearer rewrite — kept the clearer one, archived the other the same way.
- `CENTRAL_NOTICE_001_FINAL.json` documented Section 106 of the Transfer of Property Act,
  which is actually KB entry `DL_EVICTION_003` (now `CENTRAL_EVICTION_003`) — its own id
  never matched what it documented. Renamed to match.
- `MH_EVICTION_004`, `MH_EVICTION_005`, and the two `LeaseLens_Delhi_*_KB_Entries` batch
  files had a spurious "(1)" suffix with no real duplicate — just renamed.

**Fix 3 (new, found while investigating fix 2) — a citation's source URL predates its own
excerpt.** `CENTRAL_EVICTION_003` (Section 106, Transfer of Property Act — lease
termination notice periods) quotes the *current*, 2003-amended text (sub-sections (1)-(4),
including "the period... shall commence from the date of receipt of notice"). Downloading
the actual PDF at its `source_url` and reading it end to end showed it contains the
*pre-amendment* text — no sub-sections at all. Cross-verified independently against
[IndianKanoon](https://indiankanoon.org/doc/80042/) (Section 106, Transfer of Property Act,
1882): the excerpt is accurate, current law; the specific PDF cited as its source just
doesn't contain it. The three sibling Central entries sharing the same source PDF (Section
108(f), 108(m), Section 111) were checked too and do match that PDF word for word — this
issue is specific to Section 106 only, not systemic. **This was not checked for the other
26 entries** — that would be re-doing Person C's whole verification pass, out of scope
here; entries not specifically investigated are trusted as Person C reported.

**Decision recorded against `CENTRAL_EVICTION_003` (2026-09-30, was left unresolved after
the initial fix — this closes it).** Three options were on the table:

- (a) Replace `source_url` with an official source that actually contains the amended
  text.
- (b) Keep `source_url`, add an explicit disclosure that the source predates the
  amendment and the excerpt is cross-verified elsewhere.
- (c) Something else.

**Genuinely attempted (a) first, four ways, all before settling on (b):**
1. The current `source_url` itself (`indiacode.nic.in/bitstream/.../14648/1/tpa.pdf`) —
   reachable, confirmed pre-amendment (already the finding above).
2. A second India Code bitstream for the same Act
   (`.../14037/1/transfer_of_property_act8_(1).pdf`, surfaced via web search) — server
   error on every attempt (curl and the browser both failed to load it).
3. A government CDN copy linked from `legislative.gov.in`
   (`cdnbbsr.s3waas.gov.in/.../2022090983.pdf`) — downloaded successfully (356 pages,
   ~7.9 MB), but it is a **scanned image PDF with no text layer** (confirmed: 0
   characters extracted via `pdfplumber`, one image per page). OCR-ing 356 pages to find
   one section is disproportionate, and Tesseract isn't installed in this environment
   regardless (see Phase 1's own OCR-fallback status).
4. `legislative.gov.in`'s own Act page — client-rendered, no extractable text via a
   direct fetch.

No working, text-extractable, official source containing the amended text was found
after this genuine effort. **Decision: (b).** `source_url` stays as the India Code
bitstream (it correctly identifies the Act; the limitation is edition, not wrong
identity). The entry already carries, and keeps: `confidence:
"verified_current_text_secondary_cross_check"`, `source_type:
"primary_legislation_url_predates_amendment"`, and a `notes` field disclosing the
pre-/post-amendment discrepancy and the IndianKanoon cross-check
(https://indiankanoon.org/doc/80042/) in full. Re-open this if India Code ever
republishes a working, current-text copy of the Act (worth a periodic recheck, same
recommendation the original stale audit-source draft made for a different reason).

**Integration.** Data lives at `data/statute_kb/` (KB, index, audit sources incl.
`superseded/`, coverage results, original reports and README kept for provenance). Code
lives at `backend/app/statute_kb/retrieval.py` (unchanged logic from Person C's
`src/statute_retrieval.py`, just the 7 renamed ids and default paths pointed at
`data/statute_kb/`). Tests: `backend/tests/test_statute_retrieval.py` (Person C's 60
checks, converted to pytest, ids updated, 2 new edge-case tests added). Coverage script:
`backend/scripts/statute_kb_coverage.py`. A `StatuteEntry` SQLAlchemy model was added to
`app/models.py` for optional Postgres persistence (`backend/scripts/
load_statute_kb_postgres.py`), matching this project's existing persistence pattern —
retrieval itself works entirely from the JSON files and needs no database, which is what
Phase 4 uses directly. Person C's original Colab Postgres-verification notebook and
raw-SQL schema are kept under `data/statute_kb/` for reference.

Backend test suite: **86 passed** (83 + 3 for Phase 3).

### Phase 4 — LLM explanation layer, cross-clause detection, grounding guardrail

**Status:** done, 2026-09-29. Run on the full Phase 1 test corpus (9 documents, 92
clauses). Reproduce with `python scripts/run_phase4.py` from `backend/`; full output in
[`data/phase4_report.md`](data/phase4_report.md) and raw per-clause records in
`data/phase4_raw_results.json` (kept specifically so the grounding check can be re-run
later without spending fresh LLM calls - see below, this mattered).

**Architecture** (`backend/app/explain/`): `generate.py` builds a prompt with the clause
text, its Phase 2 risk label, and any Phase 3 statute excerpts retrieved for it, and asks
for **structured JSON** - `document_says` (a faithful restatement of the clause),
`concern` (why it might matter, hedged), and `statute_support` (citations, restricted to
exactly the ids passed in) - rather than free prose, specifically so the output can be
checked mechanically instead of re-read by a human. The legal disclaimer is fixed,
constant text appended by the pipeline, never model-generated, so its wording can't
drift. `cross_clause.py` shortlists candidate clause pairs by embedding similarity
(reusing Phase 2's cached MiniLM embeddings), then an LLM pass confirms/explains the
actual connection - embedding similarity alone is deliberately not treated as evidence of
a real connection, only as a way to keep the number of LLM calls proportional to document
size. `grounding.py` is the automated guardrail; `topics.py` is a small keyword-based
clause-to-statute-topic tagger (Phase 3's own retrieval is itself keyword-based, so this
is stylistically consistent rather than a mismatched ML component). A new shared
`app/llm_client.py` handles throttling/retry/daily-quota detection for Phase 4's LLM
calls; `app/classifier/llm.py` (Phase 2) was left untouched rather than refactored onto
it, to avoid risking already-shipped, tested code.

**Jurisdiction — status as of 2026-09-30, corrected after an earlier draft of this section
conflated two different claims.** Retrieval behaving correctly given a jurisdiction is not
the same thing as jurisdiction selection existing, and an earlier version of this writeup
said the second when it had only shown the first. Precisely, what exists now:

- **A real inference mechanism, in minimal form, per the Phase 3 handoff's own bar.**
  `app/explain/jurisdiction.py::infer_jurisdiction_for_document()` scans a document's own
  clause text (never the title block - the Phase 1 synthetic fixtures carry a debug line,
  `"State: X | City: Y | Format: ..."`, that a real lease would never contain, so keying
  off it would look accurate here while inferring nothing on a real document) for city/
  state name signals, and returns a jurisdiction **hint** plus its evidence.
- **Measured accuracy: 9/9 (100%)** against the known state each Phase 1 fixture
  represents - `data/phase4_report.md`'s "Jurisdiction inference" table. Correctly
  identified Maharashtra (evidence: mumbai, andheri, pune) and Delhi (evidence: delhi, new
  delhi), and correctly named all 7 other states as detected-but-unsupported (e.g.
  Karnataka from "bengaluru", Tamil Nadu from "chennai") rather than silently returning
  nothing. This inference step makes no LLM call, so this accuracy figure holds regardless
  of any LLM quota issue.
- **What does not exist: confirmation, or any caller other than this test script.**
  Nothing lets a real user see, correct, or approve this hint - `run_phase4.py` is the
  only thing calling it, there is no API endpoint parameter, no UI, and the hint's own
  `confirmed` field is hardcoded `False` because nothing sets it to `True` anywhere. This
  is explicitly Phase 5/6/7 work (the chat/frontend layer), not done here, and previous
  wording that implied otherwise was wrong.
- Only Maharashtra and Delhi are in the Phase 3 KB; a document whose inferred jurisdiction
  is `None` (unsupported or no signal) correctly retrieves no statutes - "say so
  explicitly rather than fabricate," not a gap.

**Grounding guardrail: 100% (92/92)** on the full corpus, 0 pipeline errors. Five checks,
all must pass: citations restricted to the exact retrieved set (no invented citations -
the direct test of the project's own rule 7), no statute reference smuggled into free
text outside the citation field, `document_says` introduces no new number/amount/date and
has enough word overlap with the clause to be a restatement rather than an invention, no
unhedged legal conclusion ("is illegal", "is void" - rule 6), and a YELLOW/RED clause's
`concern` is a real, non-placeholder explanation.

**A calibration bug was found and fixed before this number is trustworthy.** The first
full run scored 89.1% (82/92), with every failure the same check (`DOCUMENT_GROUNDED`)
on short, formal clauses (e.g. "IN WITNESS WHEREOF the parties hereto have set their
respective hands..."). Manually regenerating those specific clauses showed the
explanations were completely faithful, accurate paraphrases - the guardrail's raw
word-overlap-ratio metric was simply unfair to short clauses, where a legitimate
paraphrase of archaic legal language ("have set their hands" -> "signed") shares few
words in absolute terms even with nothing invented. Fixed the check to (a) directly test
for the thing that actually matters - no new number/amount/date appearing in
`document_says` that isn't in the clause - and (b) relax the lexical-overlap floor to an
absolute-count-or-ratio test so short clauses aren't penalised for having few words to
overlap on. Caught a second, smaller bug while writing the fix's own tests: the
number-extraction regex swallowed a trailing sentence comma as part of a number ("50,000,"
vs "50,000"), which would have caused false fabricated-number failures on any amount
followed immediately by a comma. Both fixes have dedicated regression tests
(`test_short_boilerplate_clause_with_faithful_paraphrase_passes`,
`test_number_with_trailing_sentence_comma_is_not_a_false_mismatch`,
`test_invented_amount_fails_even_with_high_word_overlap` - confirming real fabrication is
still caught). The 100% figure above is from the corrected metric.

**Model note:** producing these numbers required switching the LLM model mid-task.
`qwen/qwen3.8-27b` (Phase 2's model) hit its free-tier daily quota (200,000 tokens/day)
partway through the first re-run, caused by the cumulative cost of the smoke test plus
two earlier full runs the same day - every clause after that point failed identically
until quota reset (visible in `phase4_report.md`'s history if re-run mid-exhaustion).
Switched to `openai/gpt-oss-120b` (separate quota pool) for the successful run. A side
effect worth being transparent about: `classify_clause()`'s on-disk cache is keyed by
model name, so switching models forced fresh classification calls for these 92 clauses
instead of reusing Phase 2's cached ones; a handful returned malformed JSON (this model
is a reasoning model, and Phase 2 already discovered this failure mode) and correctly
triggered `classify_clause()`'s existing fallback to the trained model rather than
crashing - the Phase 2 safety mechanism working as designed under real conditions, not a
new bug. Risk-label distribution for this run: 77 GREEN, 15 YELLOW, 0 RED (a property of
these synthetic Phase 1 fixtures, which were built to test segmentation robustness, not
risk-content diversity - not evidence of a classification problem).

**Cross-clause detection: 29 connections found across the corpus** (documents 1 and 5
alone produced 6 each), far exceeding the "at least 3" requirement. Includes the exact
pattern the handoff names as an example - a fixed-term clause and a separate
early-termination-notice clause - independently found in 4 different documents, plus
several new, real patterns: a security-deposit clause connected to a "deductions for
amounts lawfully due" clause (deposit money can be used to cover missed rent), and a
license-recharacterization clause connected to its own sub-licensing restriction (the
restriction is only enforceable because the arrangement is legally a licence, not a
tenancy). Manually spot-checked several explanations against both clauses' actual text;
all were substantive, grounded, and correctly hedged rather than stating a legal
conclusion.

**Manual review sample** (12 explanations spanning GREEN/YELLOW, with/without statute
matches, with/without cross-clause involvement): in `phase4_report.md`. One flagged
example worth noting as a *correct* non-citation: a security-deposit clause retrieved
`MH_SEC_001` (Section 56(ii), Maharashtra Rent Control Act), but the model chose not to
cite it - reading the excerpt shows it actually *permits* landlords to take such
deposits/premiums, so it doesn't support a "this is risky" framing. Not citing an
irrelevant retrieved statute is the correct behavior the prompt asks for, not a missed
opportunity.

**Re-run with inference wired in, instead of the hardcoded table above - numbers kept
separate, not merged, because this run did not finish.** Once
`infer_jurisdiction_for_document()` existed, `run_phase4.py` was changed to actually call
it and feed its result into the pipeline, rather than reading `KNOWN_JURISDICTION` (which
is now used only to score the inference, per the jurisdiction section above). Re-running
the full corpus this way: **jurisdiction inference matched the known value for all 9
documents** (confirming the 100%/29-connections run above is representative of what
inference-driven jurisdiction produces, since the values are identical), but
`openai/gpt-oss-120b` **also** hit its own free-tier daily quota partway through (visible
in the run's own output: "hit its free-tier daily limit... Used 199620" of 200,000) -
between this run and the earlier successful one, cumulative use of both available free
models exhausted both today. Of this run's 92 clauses, **42 completed with 0 grounding
failures** and **13 cross-clause connections were found** before the cutoff; the
remaining 50 (documents 5 through 9, plus 2 of document 4's clauses) errored on the daily
cap, not on anything specific to inference or grounding. Per instruction, a third model
was not tried without checking first - two exhausted quotas in one day is a real signal
to stop and ask, not silently keep swapping providers. A clean, single, fully
inference-driven confirmation run across all 92 clauses is the one thing still pending,
blocked only on quota reset (or the owner naming a third free-tier provider to try
today).

Backend test suite: **108 passed** (106 + the shortlist embedding test, run separately
since it loads the MiniLM model).

### Phase 4 — demo safety (2026-09-30)

**Bottom line: demo from cached/replayed data, not a live full-corpus run, until quota
headroom is verified fresh right before the demo.** `backend/scripts/demo_replay_phase4.py`
displays a saved run with **zero network calls** - it cannot fail live regardless of quota
state - and defaults to `data/phase4_demo_safe_sample.json`, a verified-clean single
document (13 clauses, 0 errors, 2 cross-clause connections).

**Correcting an earlier claim in this conversation: quota was NOT confirmed reset.** Two
large test calls succeeding was wrongly read as proof of a fresh daily quota. It wasn't -
Groq's own documentation (console.groq.com/docs/rate-limits) states plainly that the
`x-ratelimit-remaining-tokens` / `x-ratelimit-reset-tokens` headers **always refer to TPM
(tokens per minute)**, and `x-ratelimit-remaining-requests` / `-reset-requests` **always
refer to RPD (requests per day)** - **TPD (tokens per day, the 200,000/day cap that keeps
getting hit) is never exposed in headers at all.** It only reveals itself via a 429 once
crossed. So two calls fitting under the per-minute cap said nothing about the daily total,
and a follow-up full-corpus run confirmed it: `openai/gpt-oss-120b` was still at
~199,400-199,900/200,000 used, apparently unrecovered since the exhaustion documented
above. Reset timing (UTC midnight vs. something else) is not stated on Groq's own rate-limits
doc page for the free tier; a third-party blog's claim of a fixed UTC-midnight reset is
unverified against Groq's own docs. **The owner should check the exact reset countdown
themselves at Groq's account Limits page (logged in) - it is not queryable from outside the
account or via the API.**

**A real mistake made and fixed while investigating this.** A second confirmation attempt
(to verify inference end-to-end) overwrote the one complete, clean 92/92-clause dataset
before any backup existed, and that attempt then failed on `gpt-oss-120b`'s exhausted quota
- leaving neither a fresh clean run nor the old one. A subsequent cautious single-document
test on `qwen/qwen3.8-27b` (`--limit 1`) succeeded cleanly (13/13, 0 errors, 2 cross-clause
connections), but a full-corpus attempt immediately after exhausted `qwen` too - the single
test itself used the remaining daily headroom. **Both available free models are confirmed
exhausted as of this writing.** `run_phase4.py` now backs up any existing
`phase4_raw_results.json` / `phase4_report.md` before overwriting (timestamped
`.backup-YYYYMMDDTHHMMSS` files), so this cannot happen silently again; the one clean
dataset recovered from a backup is what `phase4_demo_safe_sample.json` now is.

**No paid API key is configured.** `ANTHROPIC_API_KEY` exists as a line in `.env` but is
empty - the project is fully dependent on free-tier daily caps for any live LLM call,
Phase 2 and Phase 4 alike, until a paid key is added.

**A live demo on ONE new document (not the 9-document corpus) needs surprisingly few
calls** - measured directly from the shortlist logic, not estimated: a 13-clause document
needs 13 (classify) + 13 (explain) + 16 (cross-clause shortlist pairs) = **42 total
calls**; a 7-clause document needs **25**. Against a 200,000-token daily cap that is a
small fraction (of order 5-15%) - safe **on a day with genuine fresh headroom**. It is
not safe today, and same-day heavy testing (exactly what happened today) can burn through
it before a scheduled demo without warning, since headroom cannot be checked in advance.

**Recommendation for the actual demo:** lead with `demo_replay_phase4.py` (zero risk,
already verified working). If a live moment is wanted as a flourish, run
`python scripts/run_phase4.py --limit 1` (or a single new document once that path exists)
15-30 minutes beforehand as a dry run - not assumed safe, tested. If that dry run fails on
a quota error, the cached replay is already the whole demo and nothing further should be
attempted live that day.
