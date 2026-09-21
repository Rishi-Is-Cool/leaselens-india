"""Text extraction from lease files, with an OCR fallback for scanned pages.

Paragraph boundaries are recovered from line geometry rather than blank lines:
PDF text extraction yields no blank lines between paragraphs, but the vertical
gap between paragraphs is markedly larger than the gap between wrapped lines of
the same paragraph. Preserving those boundaries is what lets the segmenter cope
with leases that carry no numbering or headings at all.
"""

from __future__ import annotations

import io
import re
import statistics
from dataclasses import dataclass, field
from typing import Literal

import pdfplumber

# A genuinely scanned page yields essentially no extractable words. A sparse but real
# text page (a signature block, say) can be well under 100 characters, so the threshold
# is deliberately low and paired with an image check before falling back to OCR.
MIN_CHARS_FOR_TEXT_PAGE = 20

# Words whose baselines differ by less than this are treated as the same visual line.
LINE_TOLERANCE_PX = 3.0

# A vertical gap this many times the document's normal line spacing starts a new paragraph.
PARAGRAPH_GAP_RATIO = 1.35

ExtractionMethod = Literal["text", "ocr"]


class OcrUnavailableError(RuntimeError):
    """Raised when a page needs OCR but the Tesseract binary is not installed."""


@dataclass
class Page:
    number: int
    paragraphs: list[str]
    method: ExtractionMethod

    @property
    def char_count(self) -> int:
        return sum(len(p) for p in self.paragraphs)


@dataclass
class ExtractedDocument:
    pages: list[Page] = field(default_factory=list)

    @property
    def paragraphs(self) -> list[str]:
        return _rejoin_split_paragraphs([p for page in self.pages for p in page.paragraphs])

    @property
    def full_text(self) -> str:
        return "\n\n".join(self.paragraphs)

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def ocr_page_numbers(self) -> list[int]:
        return [p.number for p in self.pages if p.method == "ocr"]

    @property
    def method(self) -> str:
        methods = {p.method for p in self.pages}
        if methods == {"text"}:
            return "text"
        if methods == {"ocr"}:
            return "ocr"
        return "mixed"


def _rejoin_split_paragraphs(paragraphs: list[str]) -> list[str]:
    """Reunite a paragraph torn in two by a page break.

    Paragraph geometry is per-page, so a clause continuing onto the next page
    surfaces as two fragments. An unterminated paragraph followed by one opening
    in lower case is that continuation, and joining them is what keeps a clause
    from being split mid-sentence.
    """
    joined: list[str] = []
    for paragraph in paragraphs:
        previous = joined[-1] if joined else None
        if (
            previous
            and not previous.rstrip().endswith((".", ";", ":", "!", "?"))
            and paragraph[:1].islower()
        ):
            joined[-1] = f"{previous} {paragraph}"
            continue
        joined.append(paragraph)
    return joined


# pdfminer (under pdfplumber) emits "(cid:N)" when a font supplies no usable ToUnicode
# entry for a glyph. PyMuPDF resolves the same glyphs natively, so this is an extractor
# limitation rather than a damaged file. Only bullet-like codes are mapped: guessing at
# an arbitrary cid would silently substitute a wrong character, so anything unrecognised
# is deliberately left visible.
CID_ARTIFACT = re.compile(r"\(cid:(\d+)\)")
KNOWN_CID_CHARS = {
    127: "•",  # bullet, as used by Helvetica/Symbol subsets
    149: "•",
    183: "•",
}


def _normalize_cid_artifacts(text: str) -> str:
    return CID_ARTIFACT.sub(
        lambda m: KNOWN_CID_CHARS.get(int(m.group(1)), m.group(0)), text
    )


def _cluster_words_into_lines(words: list[dict]) -> list[tuple[float, str]]:
    """Group words sharing a baseline into lines, ordered top to bottom."""
    lines: list[tuple[float, str]] = []
    for word in sorted(words, key=lambda w: (w["top"], w["x0"])):
        text = _normalize_cid_artifacts(word["text"])
        if lines and abs(word["top"] - lines[-1][0]) <= LINE_TOLERANCE_PX:
            top, existing = lines[-1]
            lines[-1] = (top, f"{existing} {text}")
        else:
            lines.append((word["top"], text))
    return lines


def _baseline_line_gap(gaps: list[float]) -> float:
    """Normal wrapped-line spacing: the most common gap, not the median.

    Leases often use three spacings — within a paragraph, heading-to-body, and
    between blocks. The median lands on the middle one whenever body lines are not
    an outright majority, which then merges every block into a single paragraph.
    The most frequent gap is the line leading regardless of that mix.
    """
    counts: dict[float, int] = {}
    for gap in gaps:
        bucket = round(gap * 2) / 2
        counts[bucket] = counts.get(bucket, 0) + 1
    # Ties break toward the smaller gap, which is the more conservative split point.
    return min(counts, key=lambda bucket: (-counts[bucket], bucket))


def _group_lines_into_paragraphs(lines: list[tuple[float, str]]) -> list[str]:
    if not lines:
        return []
    if len(lines) == 1:
        return [lines[0][1].strip()]

    gaps = [lines[i][0] - lines[i - 1][0] for i in range(1, len(lines))]
    body_gap = _baseline_line_gap(gaps)
    threshold = body_gap * PARAGRAPH_GAP_RATIO

    paragraphs: list[str] = []
    current = [lines[0][1]]
    for index, gap in enumerate(gaps, start=1):
        if gap > threshold:
            paragraphs.append(" ".join(current).strip())
            current = [lines[index][1]]
        else:
            current.append(lines[index][1])
    paragraphs.append(" ".join(current).strip())

    return [p for p in paragraphs if p]


def _ocr_page_image(page) -> str:
    try:
        import pytesseract
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise OcrUnavailableError("pytesseract is not installed") from exc

    from pytesseract import TesseractNotFoundError

    image = page.to_image(resolution=300).original
    try:
        return pytesseract.image_to_string(image)
    except TesseractNotFoundError as exc:
        raise OcrUnavailableError(
            "The Tesseract OCR binary was not found. Install it and ensure it is on PATH "
            "(Windows: https://github.com/UB-Mannheim/tesseract/wiki)."
        ) from exc


def _paragraphs_from_ocr_text(text: str) -> list[str]:
    """OCR returns flowed text with blank lines between blocks, not geometry."""
    blocks = [b.strip() for b in text.split("\n\n")]
    return [" ".join(b.split()) for b in blocks if b.strip()]


def extract_pdf(data: bytes, *, allow_ocr: bool = True) -> ExtractedDocument:
    document = ExtractedDocument()

    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for index, page in enumerate(pdf.pages, start=1):
            words = page.extract_words()
            embedded_chars = sum(len(w["text"]) for w in words)

            # Only treat a page as scanned when it has next to no text AND carries an
            # image worth reading; otherwise a sparse text page would be sent to OCR.
            if embedded_chars >= MIN_CHARS_FOR_TEXT_PAGE or not page.images:
                paragraphs = _group_lines_into_paragraphs(_cluster_words_into_lines(words))
                document.pages.append(Page(index, paragraphs, "text"))
                continue

            if not allow_ocr:
                document.pages.append(Page(index, [], "text"))
                continue

            paragraphs = _paragraphs_from_ocr_text(_ocr_page_image(page))
            document.pages.append(Page(index, paragraphs, "ocr"))

    return document


def extract_image(data: bytes) -> ExtractedDocument:
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - dependencies are declared
        raise OcrUnavailableError("pytesseract and Pillow are required for image input") from exc

    from pytesseract import TesseractNotFoundError

    try:
        text = pytesseract.image_to_string(Image.open(io.BytesIO(data)))
    except TesseractNotFoundError as exc:
        raise OcrUnavailableError(
            "The Tesseract OCR binary was not found. Install it and ensure it is on PATH "
            "(Windows: https://github.com/UB-Mannheim/tesseract/wiki)."
        ) from exc

    return ExtractedDocument(pages=[Page(1, _paragraphs_from_ocr_text(text), "ocr")])


def extract(data: bytes, content_type: str) -> ExtractedDocument:
    if content_type == "application/pdf":
        return extract_pdf(data)
    if content_type in {"image/jpeg", "image/png"}:
        return extract_image(data)
    raise ValueError(f"Unsupported content type: {content_type}")
