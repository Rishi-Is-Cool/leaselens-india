"""Content-completeness accounting for segmentation.

Clause-count accuracy cannot see text that is dropped rather than mis-split: a
segmenter that silently discards a paragraph still reports the expected number of
clauses. This measures the share of source words that survive into the emitted
output, which is the check that catches that failure mode.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from app.ingestion.segment import SegmentedDocument

WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9'/,.\-]*")


def _tokens(text: str) -> Counter:
    """Trailing punctuation is stripped: the full stop closing a run-in heading is
    consumed when the heading is lifted out, and would otherwise read as a lost word."""
    return Counter(w.rstrip(".,;:").lower() for w in WORD.findall(text) if w.rstrip(".,;:"))

# Structural markers legitimately consumed when a heading is lifted out of a clause.
CONSUMED_MARKER = re.compile(r"^(?:\d{1,3}[.)]?|[IVXLC]{1,6}[.)]?|ARTICLE|SECTION|CLAUSE|PARA)$", re.I)


@dataclass
class Coverage:
    source_words: int
    emitted_words: int
    missing: Counter = field(default_factory=Counter)

    @property
    def percent(self) -> float:
        if not self.source_words:
            return 100.0
        return (self.source_words - sum(self.missing.values())) / self.source_words * 100

    @property
    def unexplained(self) -> dict[str, int]:
        return {w: n for w, n in self.missing.items() if not CONSUMED_MARKER.match(w)}


def measure(paragraphs: list[str], parsed: SegmentedDocument) -> Coverage:
    source = _tokens(" ".join(paragraphs))
    emitted = _tokens(
        " ".join(
            parsed.title_block
            + parsed.section_headings
            + [f"{c.section_heading or ''} {c.text}" for c in parsed.clauses]
            + parsed.signature_block
        )
    )
    return Coverage(
        source_words=sum(source.values()),
        emitted_words=sum(emitted.values()),
        missing=source - emitted,
    )
