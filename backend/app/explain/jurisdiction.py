"""Best-effort jurisdiction inference from a lease's own clause text.

This is a minimal, honest implementation of the Phase 3 task "system infers with
confirmation" - not a substitute for it. It returns a HINT plus the evidence behind it;
nothing in this codebase yet lets a user actually confirm or override that hint (a real
confirmation step is Phase 5/6 - chat/frontend - territory). Callers must treat the
result as provisional, never as authoritative.

Deliberately scans only clause text, never the title block. The Phase 1 synthetic test
fixtures carry a debug line in their title block ("State: Maharashtra | City: Mumbai |
Format: ...") that a real lease would never contain; keying off it would make this
function look accurate on the test corpus while being unable to infer anything on a real
document. Real signals - a city name in an address or an execution line ("made and
executed at Mumbai"), or a named state Act - appear in the clause body on both synthetic
and real leases alike, so that is what this scans.

Only Maharashtra and Delhi are inferable as a positive result, matching the two
jurisdictions Phase 3's statute KB actually covers. Any other state's signal is still
detected and returned (as `unsupported_hint`), so a caller can tell a user "this looks
like a Karnataka lease, which isn't covered yet" rather than silently returning nothing
with no explanation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

MAHARASHTRA_SIGNALS = re.compile(
    r"\b(maharashtra|mumbai|pune|nagpur|thane|navi mumbai|nashik|andheri|bandra)\b", re.I
)
DELHI_SIGNALS = re.compile(r"\b(delhi|new delhi|ncr)\b", re.I)

# Other pilot-adjacent states, checked only if neither Maharashtra nor Delhi matched, so
# an unsupported jurisdiction can be named rather than silently returning nothing.
OTHER_STATE_SIGNALS: dict[str, re.Pattern] = {
    "Karnataka": re.compile(r"\b(karnataka|bengaluru|bangalore|mysuru|mysore)\b", re.I),
    "Tamil Nadu": re.compile(r"\b(tamil nadu|chennai|coimbatore|madurai)\b", re.I),
    "Uttar Pradesh": re.compile(r"\b(uttar pradesh|lucknow|kanpur|noida|ghaziabad)\b", re.I),
    "West Bengal": re.compile(r"\b(west bengal|kolkata|howrah)\b", re.I),
    "Punjab": re.compile(r"\b(punjab|chandigarh|ludhiana|amritsar)\b", re.I),
    "Rajasthan": re.compile(r"\b(rajasthan|jaipur|jodhpur|udaipur)\b", re.I),
    "Gujarat": re.compile(r"\b(gujarat|ahmedabad|surat|vadodara)\b", re.I),
}


@dataclass
class JurisdictionHint:
    jurisdiction: str | None  # "Maharashtra" | "Delhi" | None
    confirmed: bool = False  # always False from this function - nothing confirms it yet
    evidence: list[str] = field(default_factory=list)
    unsupported_hint: str | None = None  # e.g. "Karnataka", detected but not in the KB
    ambiguous: bool = False


def infer_jurisdiction_for_document(clauses: list) -> JurisdictionHint:
    """Scans a document's clauses in order (never the title block) for the first
    definitive or unsupported-state signal. `clauses`: objects with a `.text` attribute.
    Still just a hint - see the module docstring."""
    for clause in clauses:
        hint = infer_jurisdiction(clause.text)
        if hint.jurisdiction or hint.unsupported_hint or hint.ambiguous:
            return hint
    return JurisdictionHint(jurisdiction=None)


def infer_jurisdiction(clause_text: str) -> JurisdictionHint:
    mh = sorted({m.lower() for m in MAHARASHTRA_SIGNALS.findall(clause_text)})
    dl = sorted({m.lower() for m in DELHI_SIGNALS.findall(clause_text)})

    if mh and dl:
        return JurisdictionHint(jurisdiction=None, evidence=mh + dl, ambiguous=True)
    if mh:
        return JurisdictionHint(jurisdiction="Maharashtra", evidence=mh)
    if dl:
        return JurisdictionHint(jurisdiction="Delhi", evidence=dl)

    for state, pattern in OTHER_STATE_SIGNALS.items():
        matches = sorted({m.lower() for m in pattern.findall(clause_text)})
        if matches:
            return JurisdictionHint(jurisdiction=None, unsupported_hint=state, evidence=matches)

    return JurisdictionHint(jurisdiction=None)
