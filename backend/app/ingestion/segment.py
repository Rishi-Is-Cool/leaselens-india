"""Rule-based clause segmentation.

Operates on the paragraph list produced by extraction, applying three independent
strategies so that a lease using any one convention still segments: explicit
numbering, heading patterns (standalone or run-in), and — when a document carries
neither — the paragraph boundaries themselves.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# "1. GRANT OF LICENSE. The Licensor hereby grants..." — number plus run-in caps heading.
NUMBERED_CAPS_HEADING = re.compile(
    r"^(\d+)\.\s+([A-Z][A-Z0-9 &,'\-/()]{2,60}?)\.\s+(?=[A-Z\"“])"
)
# "2.1 The term of this lease..." — hierarchical sub-clause numbering.
SUB_NUMBERED = re.compile(r"^(\d+\.\d+(?:\.\d+)*)\s+")
# "4. The Tenant shall pay..." — plain numbering.
NUMBERED = re.compile(r"^(\d+)[.)]\s+")
# "ARTICLE 2 – TERM AND RENT 2.1 The term..." — a section banner that often shares a
# paragraph with the clause beneath it. The title is the run of all-caps words, so the
# body is left intact rather than absorbed into the heading.
ARTICLE = re.compile(
    r"^(?i:ARTICLE|SECTION|CHAPTER|PART)\s+(?:[IVXLC]+|\d+)\s*[-–—:.]*\s*"
    r"(?P<title>[A-Z]{2,}(?:[ &'()/-]+[A-Z]{2,})*)?\s*(?P<body>.*)$"
)
# "Rent:" / "Security Deposit:" — a heading run into the start of its own paragraph.
RUN_IN_HEADING = re.compile(r"^([A-Z][A-Za-z][A-Za-z ,/&'\-]{1,44}):\s+(?=\S)")
# "TERMS AND CONDITIONS:" — a standalone all-caps banner on its own.
STANDALONE_HEADING = re.compile(r"^[A-Z0-9][A-Z0-9 &,.'\-/()]{2,60}:?$")
# "TERMS AND CONDITIONS: 1. This Agreement..." — the same banner, but sharing a paragraph
# with the first clause it governs. It scopes every clause that follows, not just this one.
INLINE_BANNER = re.compile(r"^([A-Z][A-Z0-9 &,'/()-]{2,60}):\s+(?=\d+[.)]\s)")

# "LESSOR: ______________" — a signing line. These trail the closing clause, sometimes in
# the same paragraph, so they are stripped out rather than used to discard the paragraph.
SIGNATURE_RUN = re.compile(r"[A-Z][A-Z\s.0-9]*:\s*_{3,}[\s_]*")
MIN_CLAUSE_CHARS = 20


@dataclass
class Clause:
    clause_id: str
    section_heading: str | None
    text: str
    order: int

    def as_dict(self) -> dict:
        return {
            "clause_id": self.clause_id,
            "section_heading": self.section_heading,
            "text": self.text,
            "order": self.order,
        }


def _strip_signature_runs(paragraph: str) -> str:
    """Drop signing lines, keeping any clause prose that shares the paragraph."""
    if "_" not in paragraph:
        return paragraph
    return SIGNATURE_RUN.sub("", paragraph).strip(" _")


def _is_bare_heading(paragraph: str) -> bool:
    """A heading with no body of its own — usually orphaned by a page break."""
    if len(paragraph) > 60:
        return False
    return paragraph.endswith(":") or bool(STANDALONE_HEADING.match(paragraph))


def _is_section_banner(paragraph: str) -> bool:
    """An all-caps banner heads a run of clauses; it is context, not a clause label."""
    stripped = paragraph.rstrip(":").strip()
    return bool(stripped) and stripped == stripped.upper() and any(c.isalpha() for c in stripped)


def _merge_orphan_headings(paragraphs: list[str]) -> list[str]:
    """Reattach a run-in label ("Notice Period:") stranded from its body.

    All-caps banners are deliberately left alone: they scope every clause that
    follows, so merging one into the next clause would both mislabel that clause
    and strip the section from its siblings.
    """
    merged: list[str] = []
    pending: str | None = None

    for paragraph in paragraphs:
        if pending is not None:
            merged.append(f"{pending} {paragraph}")
            pending = None
            continue
        if (
            _is_bare_heading(paragraph)
            and not _is_section_banner(paragraph)
            and not ARTICLE.match(paragraph)
        ):
            pending = paragraph
            continue
        merged.append(paragraph)

    if pending is not None:
        merged.append(pending)
    return merged


def _split_heading(paragraph: str) -> tuple[str | None, str]:
    """Pull an inline heading off the front of a paragraph, if it has one."""
    match = NUMBERED_CAPS_HEADING.match(paragraph)
    if match:
        return match.group(2).strip(), paragraph[match.end() :].strip()

    match = RUN_IN_HEADING.match(paragraph)
    if match:
        return match.group(1).strip(), paragraph[match.end() :].strip()

    return None, paragraph.strip()


def segment(paragraphs: list[str], *, skip_document_title: bool = True) -> list[Clause]:
    candidates = _merge_orphan_headings([p.strip() for p in paragraphs if p.strip()])

    if skip_document_title and candidates:
        # The first line is the instrument's title ("LEASE DEED"), not a clause.
        if _is_bare_heading(candidates[0]):
            candidates = candidates[1:]

    clauses: list[Clause] = []
    current_section: str | None = None

    for paragraph in candidates:
        paragraph = _strip_signature_runs(paragraph)
        if len(paragraph) < MIN_CLAUSE_CHARS:
            continue

        article = ARTICLE.match(paragraph)
        if article:
            title = (article.group("title") or "").strip(" .:-–—")
            if title:
                current_section = title
            # The banner usually shares its paragraph with the first clause beneath it,
            # so the remainder continues through segmentation instead of being dropped.
            paragraph = article.group("body").strip()
            if not paragraph:
                continue

        if _is_bare_heading(paragraph):
            current_section = paragraph.rstrip(":").strip()
            continue

        banner = INLINE_BANNER.match(paragraph)
        if banner:
            current_section = banner.group(1).strip()
            paragraph = paragraph[banner.end() :].strip()

        inline_heading, text = _split_heading(paragraph)
        if not text:
            continue

        order = len(clauses)
        clauses.append(
            Clause(
                clause_id=f"c{order + 1:03d}",
                section_heading=inline_heading or current_section,
                text=text,
                order=order,
            )
        )

    return clauses
