"""Maps a lease clause to one of Phase 3's statute topics, by keyword — there is no
clause-topic classifier in this project, and Phase 3's own retrieval is itself
deterministic/keyword-based (see app.statute_kb.retrieval), so a keyword tagger here is
stylistically consistent rather than a mismatched ML component bolted onto simple rules.

A clause matching no keyword gets topic=None, and the pipeline correctly retrieves
nothing for it rather than forcing a guess - "no relevant statute" is a valid, honest
outcome per the project's no-invented-citations rule.
"""

from __future__ import annotations

import re

# Order matters: checked top to bottom, first match wins. "eviction"/"termination" is
# checked before "notice" so a termination clause that happens to mention a notice
# period is tagged by its substantive topic, not just the word "notice".
TOPIC_KEYWORDS: list[tuple[str, re.Pattern]] = [
    ("security_deposit", re.compile(r"\b(security deposit|deposit)\b", re.I)),
    ("eviction", re.compile(r"\b(evict|terminat|re-?enter|forfeit|repossess|vacate)\w*", re.I)),
    ("maintenance", re.compile(r"\b(maintain|maintenance|repair)\w*", re.I)),
    ("rent_escalation", re.compile(r"\b(rent|licen[cs]e fee)\w*\s+\w*\s*(increase|escalat|enhance)", re.I)),
    ("registration", re.compile(r"\b(regist(er|ration)|stamp duty)\w*", re.I)),
    ("notice", re.compile(r"\bnotice\b", re.I)),
]


def tag_topic(clause_text: str, section_heading: str | None = None) -> str | None:
    haystack = f"{section_heading or ''} {clause_text}"
    for topic, pattern in TOPIC_KEYWORDS:
        if pattern.search(haystack):
            return topic
    return None
