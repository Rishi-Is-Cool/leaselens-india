from __future__ import annotations

import uuid
from dataclasses import asdict
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.analysis.service import public_error
from app.chat import service as chat
from app.db import get_session
from app.llm_client import DailyQuotaExceededError, LLMClient, LLMNotConfiguredError
from app.models import Analysis
from app.ownership import client_key, owned_document_or_404
from app.ratelimit import limited

router = APIRouter(prefix="/documents", tags=["chat"])


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=chat.MAX_QUESTION_CHARS * 2)


class ChatRequest(BaseModel):
    question: str | None = Field(default=None, max_length=chat.MAX_QUESTION_CHARS)
    action: Literal["explain_simply", "why_flagged", "what_to_check"] | None = None
    clause_id: str | None = None
    history: list[Turn] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def _question_or_action(self) -> ChatRequest:
        if self.action and not self.clause_id:
            raise ValueError("A quick action needs the clause it refers to.")
        if not self.action and not (self.question and self.question.strip()):
            raise ValueError("Ask a question, or choose a quick action on a clause.")
        return self


def get_chat_client() -> LLMClient:
    # Few retries: the client's default backoff suits batch runs and would leave a person
    # waiting minutes on a per-minute rate limit.
    return LLMClient(max_retries=2)


@router.post("/{document_id}/chat", dependencies=[Depends(limited("questions", "chat_limit_per_hour"))])
def ask(
    document_id: uuid.UUID,
    request: ChatRequest,
    session: Session = Depends(get_session),
    owner: str | None = Depends(client_key),
) -> dict:
    owned_document_or_404(session, document_id, owner)
    analysis = session.get(Analysis, document_id)
    if analysis is None or analysis.status != "done" or not analysis.result:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Run the review of this lease first — chat answers from that review.",
        )

    clauses = analysis.result["clauses"]
    question = request.question.strip() if request.question else ""
    if request.action:
        clause = next((c for c in clauses if c["clause_id"] == request.clause_id), None)
        if clause is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "That clause is not in this lease.")
        question = chat.question_for(request.action, clause)

    try:
        client = get_chat_client()
    except LLMNotConfiguredError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Chat needs an AI provider, which isn't set up on this server yet.",
        ) from exc

    try:
        result = chat.answer(
            question=question,
            clauses=clauses,
            jurisdiction=analysis.jurisdiction,
            client=client,
            anchor=request.clause_id,
            history=[turn.model_dump() for turn in request.history],
        )
    except chat.ChatUnavailable as exc:
        daily = isinstance(exc.__cause__, DailyQuotaExceededError)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE if daily else status.HTTP_502_BAD_GATEWAY,
            public_error(f"explanation generation failed: {exc}")
            if daily
            else "The AI provider didn't respond. Please try again in a moment.",
        ) from exc

    return {"question": question, **asdict(result)}
