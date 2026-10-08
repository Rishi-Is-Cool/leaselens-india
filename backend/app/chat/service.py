"""Document-aware chat: questions about ONE uploaded lease, answered from its clauses and
its confirmed state's statutes only.

The model is instructed to stay in scope and never give a verdict, but instructions are
not a guarantee, so every reply is also checked here: a question naming a different state
is refused before any model call, citations are restricted to statutes actually retrieved
for this lease, and an answer that states a legal conclusion, cites a law it was not given,
or introduces an amount the lease does not contain is retried once and otherwise replaced
with a safe answer.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

import numpy as np

from app.explain.generate import DISCLAIMER
from app.explain.grounding import NUMBER_PATTERN, STATUTE_REFERENCE, UNHEDGED_CONCLUSIONS
from app.explain.jurisdiction import infer_jurisdiction

MAX_QUESTION_CHARS = 1000
MAX_HISTORY_TURNS = 6
CONTEXT_CLAUSES = 6
FULL_LEASE_CHARS = 6000
# The free tier allows ~8,000 tokens a minute. Sending every statute matched to the context
# clauses (often 10+, ~3,600 tokens) let two questions exhaust it, so only the most
# relevant few go to the model, each trimmed.
CONTEXT_STATUTES = 4
STATUTE_EXCERPT_CHARS = 700

ACTIONS = {
    "explain_simply": (
        "Explain clause {clause_id} in simple, everyday words, with a short example of how it "
        "would work in practice."
    ),
    "why_flagged": (
        "Why was clause {clause_id} rated \"{rating}\"? What in its wording led to that rating? "
        "Give the reasons as bullet points."
    ),
    "what_to_check": (
        "What should I check, ask about, or try to negotiate before agreeing to clause "
        "{clause_id}? Give each point as a bullet."
    ),
}
RATING_WORDS = {"GREEN": "Looks standard", "YELLOW": "Worth a look", "RED": "Needs attention"}

SYSTEM_PROMPT = """You answer a tenant's questions about ONE specific residential lease, inside a
lease-review tool. You are given excerpts from that lease (each tagged with a clause id such
as c004), the risk rating the tool gave each, and zero or more statute excerpts from the
lease's state (each tagged with an id such as MH_SEC_001).

Rules, all non-negotiable:
1. Answer ONLY from the lease and statute excerpts provided. Do not use outside knowledge
   of laws or other leases. If the lease does not directly answer the question, say so
   plainly, then explain what the lease DOES say that is related (for example: no clause
   allows a rent increase, and the fee is stated as a fixed amount for the term).
2. If the question is about a different lease or property, a different state's law, or a
   general legal topic not about this lease, set out_of_scope to true and say briefly that
   you can only discuss this lease.
3. NEVER say anything "is legal", "is illegal", "is enforceable", "is unenforceable", "is
   void", "is valid" or "is invalid". If asked for a verdict like that, say plainly that you
   cannot give a definitive legal conclusion and that a qualified lawyer can, then explain
   what the clause says and any potential concern using hedged words ("may", "could", "a
   court might").
4. List the clause ids you relied on in cited_clauses. Cite a statute ONLY by an id from the
   provided list, in cited_statutes. Never name any Act, Section or law that is not provided.
5. Do not introduce amounts, dates or periods that do not appear in the excerpts or question.
6. Write in plain, everyday language for someone who is not a lawyer. No legal jargon
   without explaining it.
7. Format "answer" in Markdown, laid out like this (about 80-180 words in total):
   - First line: the direct answer in one or two sentences, with the key fact in **bold**.
   - Then 2-4 short bullet points ("- ") with the details that matter, each starting with a
     **bold label** (for example "- **Notice period:** ...").
   - Then, when it helps, a line starting with "**Example:**" showing how this plays out in
     practice, using ONLY the names, amounts, dates and periods written in this lease.
   - When there is something worth doing, end with a line starting with "**Tip:**".
   Use "- " bullets only, never numbered lists. No headings, tables or links. Always use
   this layout, even for short answers.

Example of the layout (for a different lease; never reuse its facts):
You can get your deposit back **within 30 days of moving out**, minus any unpaid dues.
- **Amount:** Rs. 50,000, paid when you signed.
- **Deductions:** the landlord may deduct unpaid rent or repair costs.
- **Interest:** none is payable on the deposit.
**Example:** if you leave with all rent paid and no damage, the full Rs. 50,000 should come back within 30 days.
**Tip:** take dated photos of the flat when you hand over the keys.

Reply with ONLY a JSON object, no other text:
{"answer": "...", "cited_clauses": ["c004"], "cited_statutes": ["MH_SEC_001"], "out_of_scope": false}"""

FORMAT_REMINDER = (
    "(Reply in the JSON format. In \"answer\", use the rule 7 layout: a direct answer with the "
    "key fact in bold, then 2-4 \"- **Label:** ...\" bullets, then an **Example:** line using "
    "only this lease's figures, and a **Tip:** line if useful.)"
)

# The explanation guardrail's verdict patterns, plus the affirmative forms a chat question
# ("is this legal?") invites that an explanation never does.
VERDICTS = [p for p in UNHEDGED_CONCLUSIONS] + [
    re.compile(r"\b(?:is|are) (?:perfectly |completely |fully )?(?:legal|lawful|valid|enforceable)\b", re.I),
    re.compile(r"\b(?:is|are) (?:unlawful|invalid)\b", re.I),
]
ID_TOKEN = re.compile(r"\b(?:c\d{3}|[A-Z]{2,}_[A-Z]+_\d{3})\b")
# Markdown list markers ("1. ") are layout, not amounts the lease must contain.
LIST_MARKER = re.compile(r"^\s*\d+[.)]\s", re.M)
BULLET = re.compile(r"^\s*[-*] ", re.M)

VERDICT_FALLBACK = (
    "I can't tell you whether this is **legal or enforceable**. That needs a qualified lawyer "
    "who can look at your full situation.\n"
    "- **What I can do:** explain what any clause says, in plain words.\n"
    "- **What to look at:** the clauses rated *Needs attention* or *Worth a look* in the review.\n"
    "**Tip:** try \"Why was this clause rated Needs attention?\" or use the buttons on a clause."
)
UNRELIABLE_FALLBACK = (
    "I couldn't give a **reliable answer** to that from this lease.\n"
    "- **Try:** asking about one specific clause, or rephrasing the question.\n"
    "- **Or:** use *Explain simply* on the clause you're unsure about."
)


class ChatUnavailable(RuntimeError):
    """The provider is not configured, or cannot be reached right now."""


@dataclass
class ChatAnswer:
    answer: str
    cited_clauses: list[dict] = field(default_factory=list)
    cited_statutes: list[dict] = field(default_factory=list)
    out_of_scope: bool = False
    guarded: bool = False  # a guardrail refused or replaced the model's answer
    disclaimer: str = DISCLAIMER


def question_for(action: str, clause: dict) -> str:
    return ACTIONS[action].format(
        clause_id=clause["clause_id"], rating=RATING_WORDS.get(clause["risk_label"], "not assessed")
    )


def _state_named(question: str) -> str | None:
    hint = infer_jurisdiction(question)
    return hint.jurisdiction or hint.unsupported_hint


def out_of_scope_state(question: str, jurisdiction: str | None) -> str | None:
    """A state the question names that isn't the one this lease was checked against."""
    named = _state_named(question)
    return named if named and named != jurisdiction else None


def select_clauses(question: str, clauses: list[dict], anchor: str | None, k: int = CONTEXT_CLAUSES) -> list[dict]:
    """The whole lease when it is short; otherwise the anchored clause first, then those most
    similar to the question. Always in lease order.

    Similarity alone misses wording the question doesn't share: "can the rent go up?"
    did not retrieve a clause about the "monthly licence fee". Most residential leases fit
    in about 1,500 tokens, so they are sent whole."""
    if sum(len(c["text"]) for c in clauses) <= FULL_LEASE_CHARS:
        return list(clauses)

    from app.classifier.embeddings import embed

    # Never cached: an uploaded lease's text must not outlive its retention window on disk.
    vectors = embed([question] + [c["text"] for c in clauses], cache=False)
    similarity = vectors[1:] @ vectors[0]
    order = list(np.argsort(-similarity))
    chosen = {i for i, c in enumerate(clauses) if c["clause_id"] == anchor}
    for i in order:
        if len(chosen) >= k:
            break
        chosen.add(int(i))
    return [clauses[i] for i in sorted(chosen)]


def select_statutes(question: str, context: list[dict], anchor: str | None,
                    k: int = CONTEXT_STATUTES) -> list[dict]:
    """The statutes matched to the context clauses that best fit the question: those of the
    anchored clause first, then by similarity of their text to the question and anchor."""
    from app.classifier.embeddings import embed

    by_id: dict[str, dict] = {}
    for clause in context:
        for statute in clause.get("retrieved_statutes", []):
            by_id.setdefault(statute["entry_id"], statute)
    candidates = list(by_id.values())
    if len(candidates) <= k:
        return candidates
    anchored = {s["entry_id"] for c in context if c["clause_id"] == anchor for s in c.get("retrieved_statutes", [])}
    query = question + "".join(" " + c["text"] for c in context if c["clause_id"] == anchor)
    vectors = embed([query] + [f"{s['citation']} {s['excerpt_text']}" for s in candidates], cache=False)
    similarity = vectors[1:] @ vectors[0]
    ranked = sorted(range(len(candidates)),
                    key=lambda i: (candidates[i]["entry_id"] not in anchored, -similarity[i]))
    return [candidates[i] for i in ranked[:k]]


def _excerpt(text: str) -> str:
    if len(text) <= STATUTE_EXCERPT_CHARS:
        return text
    return text[:STATUTE_EXCERPT_CHARS].rsplit(" ", 1)[0] + " …"


def build_messages(question: str, context: list[dict], statutes: list[dict], jurisdiction: str | None,
                   history: list[dict]) -> list[dict]:
    lease = "\n\n".join(
        f"[{c['clause_id']}] ({RATING_WORDS.get(c['risk_label'], 'not assessed')})"
        f"{' ' + c['section_heading'] if c.get('section_heading') else ''}\n{c['text']}"
        for c in context
    )
    law = "\n\n".join(f"[{s['entry_id']}] {s['citation']}\n{_excerpt(s['excerpt_text'])}" for s in statutes) or "(none)"
    state = jurisdiction or "a state LeaseLens holds no rental law for"
    context_block = (
        f"This lease is from {state}.\n\nLEASE EXCERPTS:\n{lease}\n\nSTATUTE EXCERPTS:\n{law}"
    )
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "system", "content": context_block}]
    for turn in history[-MAX_HISTORY_TURNS:]:
        if turn.get("role") in ("user", "assistant") and turn.get("content"):
            messages.append({"role": turn["role"], "content": str(turn["content"])[:MAX_QUESTION_CHARS]})
    # Models drift from a layout stated only in the system prompt, most often on short
    # questions, so the reminder travels with every question.
    messages.append({"role": "user", "content": f"{question}\n\n{FORMAT_REMINDER}"})
    return messages


def parse(content: str) -> dict:
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        raise ValueError("no JSON in reply")
    data = json.loads(match.group(0))
    answer = str(data.get("answer", "")).strip()
    if not answer:
        raise ValueError("empty answer")
    return {
        "answer": answer,
        "cited_clauses": [str(x) for x in data.get("cited_clauses") or [] if x],
        "cited_statutes": [str(x) for x in data.get("cited_statutes") or [] if x],
        "out_of_scope": bool(data.get("out_of_scope", False)),
    }


def violations(reply: dict, question: str, context: list[dict], statutes: list[dict]) -> list[str]:
    """Why a reply cannot be shown as-is. Empty means it passed."""
    problems = []
    text = reply["answer"]
    if any(p.search(text) for p in VERDICTS):
        problems.append("verdict")

    citations = " ".join(s["citation"] for s in statutes).lower()
    smuggled = [m.group(0) for m in STATUTE_REFERENCE.finditer(text) if m.group(0).lower() not in citations]
    if smuggled:
        problems.append("uncited_law")

    allowed = set(NUMBER_PATTERN.findall(" ".join([question] + [c["text"] for c in context]
                                                  + [s["excerpt_text"] + " " + s["citation"] for s in statutes])))
    stated = set(NUMBER_PATTERN.findall(ID_TOKEN.sub(" ", LIST_MARKER.sub(" ", text))))
    if stated - allowed:
        problems.append("invented_number")
    return problems


CORRECTIONS = {
    "verdict": "Do not say whether anything is legal, illegal, valid or enforceable. Say a lawyer "
               "can answer that, and explain what the clause says with hedged wording.",
    "uncited_law": "Do not name any Act or Section that is not in the provided statute excerpts.",
    "layout": "Use the rule 7 layout: the direct answer with the key fact in bold, then 2-4 "
              "\"- **Label:** ...\" bullet points, then an **Example:** line using only this "
              "lease's figures.",
    "invented_number": "Only use amounts, dates and periods that appear in the provided excerpts, "
                       "including in the example.",
}


def answer(*, question: str, clauses: list[dict], jurisdiction: str | None, client,
           anchor: str | None = None, history: list[dict] | None = None) -> ChatAnswer:
    """`clauses`: the analysed clauses (with risk_label and retrieved_statutes)."""
    named = out_of_scope_state(question, jurisdiction)
    if named:
        held = f"{jurisdiction}'s" if jurisdiction else "no state's"
        return ChatAnswer(
            answer=(f"I can only discuss this lease, and it was checked against {held} rental law — "
                    f"not {named}'s. I can't answer questions about another state's law or another lease."),
            out_of_scope=True,
            guarded=True,
        )

    context = select_clauses(question, clauses, anchor)
    statutes = select_statutes(question, context, anchor)
    by_id = {statute["entry_id"]: statute for statute in statutes}

    messages = build_messages(question, context, statutes, jurisdiction, history or [])
    # A reply that passes every safety check is kept even if its layout is off; a layout
    # miss earns one rewrite but never replaces a safe answer with a fallback.
    reply, best, problems = None, None, []
    for _attempt in range(2):
        try:
            content = client.chat(messages)
        except Exception as exc:  # noqa: BLE001 - surfaced as a category by the caller
            raise ChatUnavailable(str(exc)) from exc
        try:
            reply = parse(content)
        except (ValueError, json.JSONDecodeError):
            reply, problems = None, ["unparseable"]
            continue
        problems = violations(reply, question, context, statutes)
        if not problems:
            best = reply
            if reply["out_of_scope"] or BULLET.search(reply["answer"]):
                break
            problems = ["layout"]
        messages = messages + [
            {"role": "assistant", "content": content},
            {"role": "user", "content": "Rewrite your answer. " + " ".join(
                CORRECTIONS[p] for p in problems if p in CORRECTIONS)},
        ]

    if best is None:
        fallback = VERDICT_FALLBACK if "verdict" in problems else UNRELIABLE_FALLBACK
        return ChatAnswer(answer=fallback, guarded=True)
    reply = best

    known_clauses = {c["clause_id"]: c for c in context}
    cited_clauses = [
        {"clause_id": cid, "section_heading": known_clauses[cid].get("section_heading"),
         "snippet": known_clauses[cid]["text"][:140]}
        for cid in dict.fromkeys(reply["cited_clauses"]) if cid in known_clauses
    ]
    # Rule 7 of the handoff: a citation shown to the reader must trace to a statute that was
    # actually retrieved for this lease. Anything else the model names is dropped.
    cited_statutes = [
        {key: by_id[sid].get(key) for key in ("entry_id", "citation", "source_url", "last_verified_date")}
        for sid in dict.fromkeys(reply["cited_statutes"]) if sid in by_id
    ]
    return ChatAnswer(
        answer=reply["answer"],
        cited_clauses=cited_clauses,
        cited_statutes=cited_statutes,
        out_of_scope=reply["out_of_scope"],
    )
