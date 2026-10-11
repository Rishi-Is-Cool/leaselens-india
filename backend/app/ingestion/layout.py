"""Where each clause sits on the page, so the UI can highlight it on the original document.

Segmentation reshapes text (splits numbered runs, lifts headings out, rejoins paragraphs
across pages), so positions are not carried through it. Instead every clause is matched
back, in order, against the document's own word stream, which carries a box for every
word: from the PDF's text layer, or from Tesseract for scanned pages and photos. This
works the same for any state's format, and a clause whose wording cannot be found simply
gets no highlight rather than a wrong one.

Boxes are stored as fractions of the page (0-1), so the browser can draw them over a
page rendered at any size.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

TOKEN = re.compile(r"[a-z0-9]+")
# Words on one visual line differ in `top` by a few points at most.
SAME_LINE = 0.012
# How far ahead the next clause is searched for before falling back to the whole document.
SEARCH_WINDOW = 4000
# How many words of the document may be skipped to stay aligned (stray marks, page
# numbers, a heading that segmentation moved).
MAX_SKIP = 6
# A clause counts as located when at least this share of its words was found.
MIN_COVERAGE = 0.6


@dataclass
class Word:
    page: int  # 1-based
    x0: float  # fractions of the page width / height
    top: float
    x1: float
    bottom: float
    text: str


def tokens(text: str) -> list[str]:
    return TOKEN.findall(text.lower())


def _flatten(words: list[Word]) -> tuple[list[str], list[int]]:
    """The document as one token stream, with each token's source word."""
    stream: list[str] = []
    owner: list[int] = []
    for index, word in enumerate(words):
        for token in tokens(word.text):
            stream.append(token)
            owner.append(index)
    return stream, owner


def _find(stream: list[str], head: list[str], start: int, end: int) -> int | None:
    k = len(head)
    for j in range(start, max(start, end - k + 1)):
        if stream[j : j + k] == head:
            return j
    return None


def _align(stream: list[str], wanted: list[str], start: int) -> list[int]:
    """Indices in `stream` matching `wanted` in order, tolerating small differences."""
    matched: list[int] = []
    j = start
    for token in wanted:
        if j >= len(stream):
            break
        if stream[j] == token:
            matched.append(j)
            j += 1
            continue
        ahead = next((j + s for s in range(1, MAX_SKIP + 1) if j + s < len(stream) and stream[j + s] == token), None)
        if ahead is not None:
            matched.append(ahead)
            j = ahead + 1
        # Otherwise the clause has a token the page lacks (OCR noise): skip it.
    return matched


def _line_boxes(words: list[Word], indices: list[int]) -> list[list[float]]:
    """Merge matched words into one box per visual line: [page, x0, top, x1, bottom]."""
    boxes: list[list[float]] = []
    for index in sorted(set(indices)):
        word = words[index]
        last = boxes[-1] if boxes else None
        if last and last[0] == word.page and abs(last[2] - word.top) <= SAME_LINE:
            last[1] = min(last[1], word.x0)
            last[3] = max(last[3], word.x1)
            last[2] = min(last[2], word.top)
            last[4] = max(last[4], word.bottom)
        else:
            boxes.append([word.page, word.x0, word.top, word.x1, word.bottom])
    return [[int(b[0])] + [round(v, 4) for v in b[1:]] for b in boxes]


def locate_clauses(words: list[Word], clauses: list[tuple[str, str]]) -> dict[str, list[list[float]]]:
    """`clauses`: (clause_id, text) in document order. Returns clause_id -> line boxes,
    omitting clauses that could not be located reliably."""
    stream, owner = _flatten(words)
    located: dict[str, list[list[float]]] = {}
    cursor = 0
    for clause_id, text in clauses:
        wanted = tokens(text)
        if not wanted:
            continue
        # Most specific first: the clause's opening words just after the previous clause,
        # then anywhere; shorter openings only if those fail. Each candidate must align.
        matched: list[int] | None = None
        for k in sorted({min(4, len(wanted)), min(2, len(wanted)), 1}, reverse=True):
            for lo, hi in ((cursor, min(len(stream), cursor + SEARCH_WINDOW)), (0, len(stream))):
                start = _find(stream, wanted[:k], lo, hi)
                if start is None:
                    continue
                candidate = _align(stream, wanted, start)
                if len(candidate) >= MIN_COVERAGE * len(wanted):
                    matched = candidate
                    break
            if matched:
                break
        if not matched:
            continue
        located[clause_id] = _line_boxes(words, [owner[j] for j in matched])
        cursor = matched[-1] + 1
    return located


def pdf_text_words(page, number: int) -> list[Word]:
    """Words from a pdfplumber page's text layer."""
    width, height = float(page.width), float(page.height)
    return [
        Word(number, w["x0"] / width, w["top"] / height, w["x1"] / width, w["bottom"] / height, w["text"])
        for w in page.extract_words()
    ]


def ocr_words(tsv: str, number: int, width: int, height: int) -> list[Word]:
    """Words from Tesseract's TSV output for an image of `width` x `height` pixels."""
    words: list[Word] = []
    rows = tsv.splitlines()
    if not rows:
        return words
    header = rows[0].split("\t")
    col = {name: i for i, name in enumerate(header)}
    for row in rows[1:]:
        cells = row.split("\t")
        if len(cells) != len(header) or cells[col["level"]] != "5":
            continue
        text = cells[col["text"]].strip()
        try:
            confidence = float(cells[col["conf"]])
        except ValueError:
            continue
        if not text or confidence < 0:
            continue
        left, top = int(cells[col["left"]]), int(cells[col["top"]])
        w, h = int(cells[col["width"]]), int(cells[col["height"]])
        words.append(Word(number, left / width, top / height, (left + w) / width, (top + h) / height, text))
    return words
