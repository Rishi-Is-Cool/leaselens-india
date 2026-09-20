# LeaseLens — Phase 1 Handoff (Person A)

**Paste this into your Claude Code session, or drop it into `CLAUDE.md` / your project
instructions file. Phase 0 is already complete — this scopes Claude Code to Phase 1 only.**

---

## Scope lock (read first)

You are building **Phase 1 only: Document Ingestion & Clause Segmentation.**

Do NOT start the risk classifier, statute knowledge base, LLM explanation layer, chat,
frontend, or any other phase. If you find yourself about to write code for anything beyond
turning a lease file into structured clause objects in Postgres, stop and ask me first.

Rules of engagement (from the project's rules, apply throughout):
- Do not mark this phase done with failing tests, partial implementation, or unresolved
  errors. If blocked, say so specifically — what's blocking, what you tried — instead of
  working around it silently.
- Commit at the end of this phase with a message naming it:
  `feat: phase 1 - document ingestion + clause segmentation`. Do not squash with other work.
- No hardcoded secrets — config via `.env`, with `.env.example` checked in and `.env`
  gitignored.
- When you finish, run the verification steps yourself, report results plainly (what was
  built, what was tested, what passed/failed), update `PROGRESS.md`, then stop and wait for
  my confirmation before touching Phase 2.

---

## Goal

Given a lease file (clean PDF or scanned/photographed image-PDF), produce a clean list of
clause objects, stored in Postgres.

## Tech stack for this phase

- **Backend:** FastAPI (Python)
- **PDF/text extraction:** `pdfplumber` or `PyMuPDF` — try `pdfplumber` first
- **OCR fallback:** `pytesseract` (or a cloud OCR API if budget allows)
- **Storage:** Postgres
- **Segmentation:** rule-based only (numbering patterns, headings, paragraph breaks) — no ML
  needed for this phase

If a different tool is clearly better for a specific piece (e.g. a PDF library that handles
a real test document better), you may substitute — but say so and why, don't swap silently.

## Tasks

1. Build `POST /documents`, accepting PDF, JPEG, and PNG files.
2. Extract text directly first (`pdfplumber`/`PyMuPDF`).
3. If a page has little/no extractable text, fall back to OCR (`pytesseract`).
4. Write a rule-based clause segmenter: numbering patterns, ALL-CAPS/heading patterns, and
   plain paragraph-break patterns (some of my test docs have no numbering at all — see below
   — so the paragraph-break fallback matters, don't only key off numbers).
5. Output clause objects shaped `{clause_id, section_heading, text, order}`.
6. Store parsed clauses in Postgres, linked to the source document.

## Test set

I've added **5 lease PDFs** to `[UPDATE: your folder path, e.g. /data/test-leases/]`:

| File | State | Structural style — what it's testing |
|---|---|---|
| `01_maharashtra_leave_license_mumbai.pdf` | Maharashtra | Numbered clauses, ALL-CAPS section headings |
| `02_delhi_rent_agreement.pdf` | Delhi | Bold run-in headings ("Rent:", "Security Deposit:"), no numbering |
| `03_karnataka_rental_agreement_bangalore.pdf` | Karnataka | Numbered clauses with lettered sub-points (a), (b), (c) |
| `04_tamil_nadu_lease_agreement_chennai.pdf` | Tamil Nadu | Plain prose paragraphs — no numbering or headings at all (hardest case) |
| `05_uttar_pradesh_lease_deed_lucknow.pdf` | Uttar Pradesh | Mixed: ARTICLE headings + numbered sub-clauses (2.1, 2.3(a)) |

These are clean, text-based (not scanned) — they test extraction + segmentation logic, not
OCR. I still need to add:
- 3–5 more documents to reach the 8–10 target test-set size
- 2–3 **scanned/photographed** versions (I'll print and photograph a couple of the above)
  once the segmenter is working on clean text — no point testing OCR noise on top of a
  segmenter that's still breaking on clean input.

## Verification — run this, don't just claim it works

1. Run the full pipeline on all 5 PDFs currently in the folder.
2. For each file, show me: (a) the raw extracted text, (b) the segmented clause list with
   `{clause_id, section_heading, text, order}`. Don't silently fix anything first — show me
   the raw output so I can check it against the source PDF myself.
3. Manually check each file's segmentation against what a human would call correct:
   - No clause split mid-sentence
   - No two clauses merged into one
   - Headings recognized correctly, including Delhi's un-numbered "Rent:" style heading
   - Tamil Nadu's no-numbering, paragraph-only file is the real stress test — if the
     segmenter only keys off numbering patterns, this file will likely come back as one giant
     clause. That's a genuine signal the paragraph-break fallback needs work, not a bug to
     paper over.
4. Count it: total real clauses across the 5 docs vs. how many were split cleanly and
   correctly. That percentage is the measured accuracy — write the actual number to
   `PROGRESS.md`, not "looks good."
5. Confirm OCR fallback triggers and produces usable text once I've added the scanned
   samples (separate check, after the clean-text segmentation is solid).

## Definition of Done

- Pipeline runs on the full 8–10 doc test set (once complete), including 2–3
  scanned/photographed ones.
- Measured segmentation accuracy ≥90%, recorded in `PROGRESS.md` with the actual number.
- OCR fallback demonstrably triggers and produces usable text on the scanned samples.
- Clauses stored in Postgres, linked to source document.

---

**Next step after this phase is confirmed done:** clauses get handed to Phase 2 (risk
classifier) and Phase 4 (explanation layer) downstream — so before closing this phase out,
confirm the `{clause_id, section_heading, text, order}` shape is stable, since other people
are building against it.
