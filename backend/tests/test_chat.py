"""Phase 5 chat: scoped to one lease and its state's law, no verdicts, no invented citations.

A fake model client stands in for the provider, so each guardrail is exercised
deterministically and the suite spends no LLM quota.
"""

import json
import uuid

import pytest
from fastapi.testclient import TestClient

from app.chat import service as chat
from app.db import SessionLocal, create_tables
from app.llm_client import DailyQuotaExceededError, LLMNotConfiguredError
from app.main import app
from app.models import Analysis, Clause, Document
from app.routers import chat as chat_router

pytestmark = pytest.mark.skipif(SessionLocal is None, reason="DATABASE_URL not configured")
client = TestClient(app)

DEPOSIT = {
    "entry_id": "MH_SEC_001",
    "citation": "Section 56(ii), Maharashtra Rent Control Act, 1999",
    "excerpt_text": "it shall be lawful for the landlord to receive any deposit in respect of the grant of a lease",
    "source_url": "https://www.indiacode.nic.in/example.pdf",
    "last_verified_date": "2026-09-26",
    "jurisdiction": "Maharashtra",
}
CLAUSES = [
    {"clause_id": "c001", "section_heading": None, "risk_label": "GREEN", "retrieved_statutes": [],
     "text": "This agreement is made at Mumbai between the Licensor and the Licensee."},
    {"clause_id": "c002", "section_heading": "SECURITY DEPOSIT", "risk_label": "YELLOW",
     "retrieved_statutes": [DEPOSIT],
     "text": "The Licensee has paid a refundable security deposit of Rs. 2,00,000 to be refunded within 15 days of vacating."},
    {"clause_id": "c003", "section_heading": "TERMINATION", "risk_label": "RED", "retrieved_statutes": [],
     "text": "The Licensor may terminate this agreement at any time without notice and re-enter the premises."},
]


class FakeClient:
    """Returns scripted replies in order and records what it was sent."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.sent = []

    def chat(self, messages):
        self.sent.append(messages)
        if not self.replies:
            raise AssertionError("the model was called more times than scripted")
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return json.dumps(reply)


def reply(answer, clauses=(), statutes=(), out_of_scope=False):
    return {"answer": answer, "cited_clauses": list(clauses), "cited_statutes": list(statutes),
            "out_of_scope": out_of_scope}


@pytest.fixture(scope="module", autouse=True)
def _tables():
    create_tables()


@pytest.fixture
def lease():
    """An uploaded document with a finished Maharashtra analysis."""
    session = SessionLocal()
    document = Document(
        filename="chat_test.pdf", content_type="application/pdf", byte_size=1, page_count=1,
        extraction_method="text",
        clauses=[Clause(clause_id=c["clause_id"], section_heading=c["section_heading"], text=c["text"],
                        order_index=i) for i, c in enumerate(CLAUSES)],
    )
    session.add(document)
    session.commit()
    session.add(Analysis(document_id=document.id, status="done", jurisdiction="Maharashtra",
                         explanations_available=True, progress_done=3, progress_total=3,
                         result={"clauses": CLAUSES, "cross_clause": []}))
    session.commit()
    document_id = document.id
    session.close()
    yield str(document_id)
    session = SessionLocal()
    session.delete(session.get(Document, document_id))
    session.commit()
    session.close()


@pytest.fixture
def model(monkeypatch):
    def install(*replies):
        fake = FakeClient(*replies)
        monkeypatch.setattr(chat_router, "get_chat_client", lambda: fake)
        return fake
    return install


def ask(document_id, **body):
    return client.post(f"/documents/{document_id}/chat", json=body)


def test_a_grounded_answer_keeps_only_citations_that_were_retrieved(lease, model):
    model(reply("Your deposit of Rs. 2,00,000 should come back within 15 days of moving out.",
                clauses=["c002"], statutes=["MH_SEC_001", "MH_FAKE_999"]))
    body = ask(lease, question="When do I get my deposit back?").json()
    assert "15 days" in body["answer"]
    assert [c["clause_id"] for c in body["cited_clauses"]] == ["c002"]
    assert [s["entry_id"] for s in body["cited_statutes"]] == ["MH_SEC_001"], "invented id must be dropped"
    assert body["cited_statutes"][0]["source_url"].startswith("https://")
    assert body["guarded"] is False and body["disclaimer"]


def test_a_question_about_another_state_is_refused_without_calling_the_model(lease, model):
    fake = model()  # any call would raise
    body = ask(lease, question="Would this deposit be allowed under Karnataka law?").json()
    assert body["out_of_scope"] is True and body["guarded"] is True
    assert "Karnataka" in body["answer"] and "Maharashtra" in body["answer"]
    assert fake.sent == []


def test_a_verdict_is_retried_and_the_hedged_rewrite_is_used(lease, model):
    fake = model(
        reply("This termination clause is illegal and void.", clauses=["c003"]),
        reply("I can't say whether this is enforceable; a lawyer can. It may let the Licensor end the "
              "agreement without notice, which could be worth questioning.", clauses=["c003"]),
    )
    body = ask(lease, question="Is clause c003 legal?").json()
    assert "illegal" not in body["answer"] and "lawyer" in body["answer"]
    assert len(fake.sent) == 2, "the first, unhedged answer must be sent back for a rewrite"


def test_a_persistent_verdict_is_replaced_with_a_safe_answer(lease, model):
    model(reply("Yes, this clause is perfectly legal."), reply("It is enforceable."))
    body = ask(lease, question="Is this lease legal?").json()
    assert body["answer"] == chat.VERDICT_FALLBACK
    assert body["guarded"] is True
    assert body["cited_statutes"] == []


def test_a_law_the_model_was_not_given_is_never_shown(lease, model):
    model(reply("Under Section 108 of the Transfer of Property Act, 1882 you must be given notice."),
          reply("Section 108 of the Transfer of Property Act, 1882 applies here."))
    body = ask(lease, question="Do I get notice before being evicted?").json()
    assert "108" not in body["answer"]
    assert body["guarded"] is True


def test_an_invented_amount_is_never_shown(lease, model):
    model(reply("Your deposit is Rs. 5,00,000.", clauses=["c002"]),
          reply("Your deposit is Rs. 5,00,000.", clauses=["c002"]))
    body = ask(lease, question="How much is my deposit?").json()
    assert "5,00,000" not in body["answer"]


def test_quick_action_anchors_the_clause_and_uses_its_plain_rating(lease, model):
    fake = model(reply("The landlord can end the deal at any time with no warning.", clauses=["c003"]))
    body = ask(lease, action="why_flagged", clause_id="c003").json()
    assert "Needs attention" in body["question"] and "c003" in body["question"]
    sent = " ".join(m["content"] for m in fake.sent[0])
    assert "terminate this agreement at any time" in sent


def test_chat_waits_for_the_review(model):
    session = SessionLocal()
    document = Document(filename="unreviewed.pdf", content_type="application/pdf", byte_size=1,
                        page_count=1, extraction_method="text")
    session.add(document)
    session.commit()
    try:
        assert ask(document.id, question="What is my rent?").status_code == 409
    finally:
        session.delete(document)
        session.commit()
        session.close()


def test_no_provider_is_a_clear_503(lease, monkeypatch):
    def unconfigured():
        raise LLMNotConfiguredError("no key")
    monkeypatch.setattr(chat_router, "get_chat_client", unconfigured)
    response = ask(lease, question="What is my rent?")
    assert response.status_code == 503
    assert "AI provider" in response.json()["detail"]


def test_a_daily_limit_never_leaks_the_provider_message(lease, model):
    model(DailyQuotaExceededError("Rate limit reached in organization `org_01exampleexampleexample00`"))
    response = ask(lease, question="What is my rent?")
    assert response.status_code == 503
    assert "org_" not in response.text and "daily limit" in response.json()["detail"]


@pytest.mark.parametrize(
    "body",
    [{"action": "why_flagged"}, {"question": "   "}, {}, {"question": "x" * 1001}],
)
def test_malformed_requests_are_rejected(lease, body):
    assert ask(lease, **body).status_code == 422


def test_unknown_document_is_a_404():
    assert ask(uuid.uuid4(), question="hi").status_code == 404


def test_only_the_most_relevant_statutes_are_sent_and_the_anchor_keeps_its_own():
    def statute(i, topic):
        return {**DEPOSIT, "entry_id": f"MH_SEC_{i:03d}", "citation": f"Section {i}",
                "excerpt_text": f"{topic} " * 400}
    context = [
        {**CLAUSES[1], "retrieved_statutes": [statute(1, "security deposit refund")]},
        {**CLAUSES[2], "retrieved_statutes": [statute(i, "eviction notice") for i in range(2, 9)]},
    ]
    chosen = chat.select_statutes("When is my deposit refunded?", context, anchor="c002")
    assert len(chosen) == chat.CONTEXT_STATUTES
    assert chosen[0]["entry_id"] == "MH_SEC_001"
    sent = chat.build_messages("q", context, chosen, "Maharashtra", [])[1]["content"]
    assert len(sent) < 6000, "statute excerpts must be trimmed"


@pytest.mark.parametrize(
    "question, jurisdiction, expected",
    [
        ("Is this fine under Delhi law?", "Maharashtra", "Delhi"),
        ("Can my Mumbai landlord keep the deposit?", "Maharashtra", None),
        ("Is Bangalore rent usually higher?", None, "Karnataka"),
        ("Can they raise the rent?", "Delhi", None),
    ],
)
def test_state_scope(question, jurisdiction, expected):
    assert chat.out_of_scope_state(question, jurisdiction) == expected
