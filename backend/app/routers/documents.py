from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import OperationalError
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.analysis import service as analysis_service
from app.db import get_session
from app.ingestion.extract import OcrUnavailableError, extract
from app.ingestion.segment import segment_document
from app.models import Analysis, Clause, Document
from app.retention import expiry_for_new_upload, purge_expired_documents

router = APIRouter(prefix="/documents", tags=["documents"])

SUPPORTED_CONTENT_TYPES = {"application/pdf", "image/jpeg", "image/png"}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


class ClauseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    clause_id: str
    clause_number: str | None = None
    section_heading: str | None
    text: str
    # Stored as order_index because "order" is a reserved SQL word.
    order: int = Field(validation_alias="order_index")


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    content_type: str
    page_count: int
    extraction_method: str
    clause_count: int
    clauses: list[ClauseOut]
    title_block: list[str]
    section_headings: list[str]
    signature_block: list[str]


class DocumentSummary(BaseModel):
    id: uuid.UUID
    filename: str
    page_count: int
    extraction_method: str
    clause_count: int


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> DocumentOut:
    # Enforce the retention window on every upload: a free-tier host has no cron.
    purge_expired_documents(session)

    if file.content_type not in SUPPORTED_CONTENT_TYPES:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Unsupported file type {file.content_type!r}. Accepted: PDF, JPEG, PNG.",
        )

    data = await file.read()
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Uploaded file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)}MB limit.",
        )

    try:
        extracted = extract(data, file.content_type)
    except OcrUnavailableError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, str(exc)) from exc

    parsed = segment_document(extracted.paragraphs)
    clauses = parsed.clauses
    if not clauses:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "No readable text could be extracted from this file.",
        )

    document = Document(
        filename=file.filename or "untitled",
        content_type=file.content_type,
        byte_size=len(data),
        page_count=extracted.page_count,
        extraction_method=extracted.method,
        expires_at=expiry_for_new_upload(),
        title_block=parsed.title_block,
        section_headings=parsed.section_headings,
        signature_block=parsed.signature_block,
        clauses=[
            Clause(
                clause_id=c.clause_id,
                clause_number=c.clause_number,
                section_heading=c.section_heading,
                text=c.text,
                order_index=c.order,
            )
            for c in clauses
        ],
    )
    try:
        session.add(document)
        session.commit()
        session.refresh(document)
    except OperationalError as exc:
        session.rollback()
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "The database is unreachable, so the parsed clauses could not be saved.",
        ) from exc

    return _to_out(document)


@router.get("", response_model=list[DocumentSummary])
def list_documents(session: Session = Depends(get_session)) -> list[DocumentSummary]:
    """Return the latest temporary uploads for the local review screen."""
    purge_expired_documents(session)
    documents = session.scalars(
        select(Document)
        .options(selectinload(Document.clauses))
        .order_by(Document.created_at.desc())
        .limit(12)
    ).all()
    return [
        DocumentSummary(
            id=document.id,
            filename=document.filename,
            page_count=document.page_count,
            extraction_method=document.extraction_method,
            clause_count=len(document.clauses),
        )
        for document in documents
    ]


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: uuid.UUID, session: Session = Depends(get_session)) -> DocumentOut:
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")
    return _to_out(document)


class AnalysisRequest(BaseModel):
    # None means "a state we hold no law for": risk levels still run, statutes are skipped.
    jurisdiction: str | None = None


def _document_or_404(session: Session, document_id: uuid.UUID) -> Document:
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")
    return document


@router.get("/{document_id}/analysis")
def get_analysis(document_id: uuid.UUID, session: Session = Depends(get_session)) -> dict:
    """Status, progress and (once done) the result. Before any run it also returns the
    jurisdiction inferred from the lease, which the user confirms before starting."""
    document = _document_or_404(session, document_id)
    return analysis_service.describe(document, session.get(Analysis, document_id))


@router.post("/{document_id}/analysis", status_code=status.HTTP_202_ACCEPTED)
def start_analysis(
    document_id: uuid.UUID,
    background: BackgroundTasks,
    request: AnalysisRequest = Body(default_factory=AnalysisRequest),
    session: Session = Depends(get_session),
) -> dict:
    document = _document_or_404(session, document_id)
    try:
        analysis = analysis_service.start(session, document, request.jurisdiction)
    except analysis_service.AnalysisAlreadyRunning as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    # Runs after the response is sent, so the request returns immediately and the UI polls.
    background.add_task(analysis_service.run, document.id)
    return analysis_service.describe(document, analysis)


def _to_out(document: Document) -> DocumentOut:
    return DocumentOut(
        id=document.id,
        filename=document.filename,
        content_type=document.content_type,
        page_count=document.page_count,
        extraction_method=document.extraction_method,
        clause_count=len(document.clauses),
        title_block=document.title_block or [],
        section_headings=document.section_headings or [],
        signature_block=document.signature_block or [],
        clauses=[ClauseOut.model_validate(c) for c in document.clauses],
    )
