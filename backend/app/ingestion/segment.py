"""Rule-based clause segmentation.

Operates on the paragraph list produced by extraction, applying three independent
strategies so that a lease using any one convention still segments: explicit
numbering, heading patterns (standalone or run-in), and — when a document carries
neither — the paragraph boundaries themselves.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# "1. GRANT OF LICENSE. ..." and "Clause 3. Maintenance. ..." — a number, optionally
# spelled out as "Clause N", followed by a run-in heading closed with a full stop. The
# heading may be all-caps or title case; length and word-count guards below stop an
# ordinary sentence ("2. The Tenant shall pay ... Rs.") being mistaken for one.
NUMBERED_RUN_IN_HEADING = re.compile(
    r"^(?:(?i:clause|article|section|para(?:graph)?)\s+)?(\d+)\.\s+"
    r"([A-Za-z][A-Za-z &'\-/]{2,60}?)\.\s+(?=[A-Z\"“(])"
)
# "USE OF PREMISES The Tenant shall use..." — an all-caps heading run straight into its
# body with neither number nor colon. The trailing title-case word is what separates a
# heading from an ordinary opening like "THIS LEASE DEED is executed...", where the next
# word is lower case.
# Covers both "USE OF PREMISES The Tenant..." and "1. PREMISES AND TERM The Landlord...",
# where the heading closes with no full stop. The body may open with a title-case word or
# with a bullet, as it does when a heading introduces a list.
CAPS_RUN_IN_HEADING = re.compile(
    r"^(?:(?i:clause|article|section|para(?:graph)?)\s+)?(?:\d+[.)]\s+)?"
    r"([A-Z][A-Z &'\-/()]{2,45}?)\s+(?=[A-Z][a-z]|[••])"
)

# A list item continuing the clause above it, rather than starting a new one.
BULLET_LINE = re.compile(r"^\s*[••▪◦‣·*]\s+")
# "2.1 The term of this lease..." — hierarchical sub-clause numbering.
SUB_NUMBERED = re.compile(r"^(\d+\.\d+(?:\.\d+)*)\s+")
# "4. The Tenant shall pay..." / "Clause 4. ..." — plain numbering.
NUMBERED = re.compile(r"^(?:(?i:clause|article|section|para(?:graph)?)\s+)?(\d+)[.)]\s+")
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
STANDALONE_HEADING = re.compile(r"^[(A-Z0-9][A-Z0-9 &,.'\-/()]{2,60}:?$")

# The closing attestation ends the operative sections, so it must not inherit the
# section heading of whatever clause preceded it.
CLOSING_FORMULA = re.compile(r"^IN\s+WITNESS(?:ES)?\s+WHERE", re.IGNORECASE)
# "TERMS AND CONDITIONS: 1. This Agreement..." — the same banner, but sharing a paragraph
# with the first clause it governs. It scopes every clause that follows, not just this one.
INLINE_BANNER = re.compile(r"^([A-Z][A-Z0-9 &,'/()-]{2,60}):\s+(?=\d+[.)]\s)")

# "LESSOR: ______________" — a signing line. These trail the closing clause, sometimes in
# the same paragraph, so they are stripped out rather than used to discard the paragraph.
SIGNATURE_RUN = re.compile(r"(?:[A-Z][A-Z\s.0-9]*:|\d{1,2}\.)\s*_{3,}[\s_]*")

# "BETWEEN :" and "AND" introduce the parties to a deed. They are fixed structural
# keywords of the instrument, like ARTICLE, and one carries a colon while the other
# does not — so they are matched by name to keep their treatment consistent.
DEED_CONNECTOR = re.compile(r"^(BETWEEN|AND|WITNESSETH)\b\s*:?\s+(?=\S)")

# An all-caps line closing with a colon or semicolon divides the recitals from the
# operative terms, so the recital heading must not carry on past it.
SECTION_DIVIDER = re.compile(r"^[A-Z0-9][^a-z]{10,}[;:]\s*$")
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


def _split_signature_runs(paragraph: str) -> tuple[str, list[str]]:
    """Separate signing lines from any clause prose sharing the paragraph.

    Returns the prose and the signing lines, rather than discarding the latter: a
    closing attestation often shares its paragraph with "LESSOR: ______", and no
    text from the source document should vanish from the output.
    """
    if "_" not in paragraph:
        return paragraph, []
    signatures = [m.strip() for m in SIGNATURE_RUN.findall(paragraph) if m.strip()]
    return SIGNATURE_RUN.sub("", paragraph).strip(" _"), signatures


def _is_bare_heading(paragraph: str) -> bool:
    """A heading with no body of its own — usually orphaned by a page break."""
    if len(paragraph) > 60:
        return False
    return paragraph.endswith(":") or bool(STANDALONE_HEADING.match(paragraph))


def _is_section_banner(paragraph: str) -> bool:
    """An all-caps banner heads a run of clauses; it is context, not a clause label."""
    stripped = paragraph.rstrip(":").strip()
    return bool(stripped) and stripped == stripped.upper() and any(c.isalpha() for c in stripped)


def _merge_bullet_lists(paragraphs: list[str]) -> list[str]:
    """Attach list items to the clause that introduces them.

    A bullet list is laid out with its own line spacing, so each item arrives as its
    own paragraph. The items qualify the heading above them ("SCHEDULE OF FIXTURES
    INCLUDED"), and splitting them into separate clauses would strip that context.
    """
    merged: list[str] = []
    for paragraph in paragraphs:
        if merged and BULLET_LINE.match(paragraph):
            merged[-1] = f"{merged[-1]} {paragraph.strip()}"
            continue
        merged.append(paragraph)
    return merged


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


MAX_HEADING_WORDS = 5
MAX_HEADING_CHARS = 45


def _is_plausible_heading(candidate: str) -> bool:
    """Guard against a sentence opening being lifted out as a heading.

    "2. The Tenant shall pay a monthly rent of Rs. 28,000" ends its first full stop
    after "Rs", which otherwise reads as a run-in heading. Real headings are short.
    """
    return len(candidate) <= MAX_HEADING_CHARS and len(candidate.split()) <= MAX_HEADING_WORDS


def _split_heading(paragraph: str) -> tuple[str | None, str]:
    """Pull an inline heading off the front of a paragraph, if it has one."""
    match = NUMBERED_RUN_IN_HEADING.match(paragraph)
    if match and _is_plausible_heading(match.group(2)):
        return match.group(2).strip(), paragraph[match.end() :].strip()

    match = RUN_IN_HEADING.match(paragraph)
    if match and _is_plausible_heading(match.group(1)):
        return match.group(1).strip(), paragraph[match.end() :].strip()

    match = CAPS_RUN_IN_HEADING.match(paragraph)
    if match and _is_plausible_heading(match.group(1)):
        return match.group(1).strip(), paragraph[match.end() :].strip()

    match = DEED_CONNECTOR.match(paragraph)
    if match:
        return match.group(1), paragraph[match.end() :].strip()

    return None, paragraph.strip()


MAX_TITLE_BLOCK_PARAGRAPHS = 3
MAX_TITLE_LINE_CHARS = 150


def split_title_block(paragraphs: list[str]) -> tuple[list[str], list[str]]:
    """Separate the masthead from the agreement body.

    A lease opens with a title, and sometimes a filing or reference line, before the
    operative text begins. These are short and are not sentences, whereas the body
    opens with one ("This Rent Agreement is made at..."). So the block runs from the
    top until the first paragraph that terminates like prose — bounded to a few
    paragraphs so an unusual document cannot swallow real clauses.
    """
    title: list[str] = []
    for index, paragraph in enumerate(paragraphs):
        if index >= MAX_TITLE_BLOCK_PARAGRAPHS:
            break
        # A colon ends an operative opening ("...is entered into on 14th March 2026:")
        # as surely as a full stop does, so it closes the masthead too.
        if paragraph.rstrip().endswith((".", ";", "!", "?", ":")):
            break
        if len(paragraph) > MAX_TITLE_LINE_CHARS:
            break
        title.append(paragraph)
    return title, paragraphs[len(title) :]


@dataclass
class SegmentedDocument:
    """Every paragraph of the source lands in exactly one of these three parts."""

    title_block: list[str]
    clauses: list[Clause]
    signature_block: list[str]
    # Banners such as "NOW THIS AGREEMENT WITNESSETH AS FOLLOWS:" scope the clauses
    # beneath them, but a clause carrying its own run-in heading never adopts one.
    # Recording every banner keeps that text in the output instead of dropping it.
    section_headings: list[str] = field(default_factory=list)


def segment(paragraphs: list[str]) -> list[Clause]:
    return segment_document(paragraphs).clauses


def segment_document(paragraphs: list[str]) -> SegmentedDocument:
    cleaned = [p.strip() for p in paragraphs if p.strip()]
    title_block, cleaned = split_title_block(cleaned)
    signature_block: list[str] = []
    section_headings: list[str] = []
    candidates = _merge_orphan_headings(_merge_bullet_lists(cleaned))

    clauses: list[Clause] = []
    current_section: str | None = None
    section_pending = False

    for paragraph in candidates:
        paragraph, signatures = _split_signature_runs(paragraph)
        signature_block.extend(signatures)
        if not paragraph:
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
            heading = paragraph.rstrip(":").strip()
            # Consecutive standalone headings are one compound section, so a
            # subheading such as "(DEMISED PREMISES)" joins the line above it
            # rather than replacing it or being dropped.
            current_section = f"{current_section} {heading}" if section_pending else heading
            if section_pending and section_headings:
                section_headings[-1] = current_section
            else:
                section_headings.append(current_section)
            section_pending = True
            continue

        if CLOSING_FORMULA.match(paragraph) or SECTION_DIVIDER.match(paragraph):
            current_section = None

        banner = INLINE_BANNER.match(paragraph)
        if banner:
            current_section = banner.group(1).strip()
            section_headings.append(current_section)
            paragraph = paragraph[banner.end() :].strip()

        inline_heading, text = _split_heading(paragraph)
        if not text:
            continue

        section_pending = False
        order = len(clauses)
        clauses.append(
            Clause(
                clause_id=f"c{order + 1:03d}",
                section_heading=inline_heading or current_section,
                text=text,
                order=order,
            )
        )

    # A heading no clause ever consumed still has to survive: a document ending
    # "WITNESSES : 1. ____ 2. ____" leaves the label with nothing beneath it once the
    # signing slots are lifted out, and dropping it would lose source text.
    return SegmentedDocument(
        title_block=title_block,
        clauses=clauses,
        signature_block=signature_block,
        section_headings=section_headings,
    )
