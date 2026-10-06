from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename: Mapped[str] = mapped_column(String(512))
    content_type: Mapped[str] = mapped_column(String(128))
    byte_size: Mapped[int] = mapped_column(Integer)
    page_count: Mapped[int] = mapped_column(Integer)
    extraction_method: Mapped[str] = mapped_column(String(16))
    # Kept so that every paragraph of the source survives somewhere: the masthead and
    # the signing lines are not clauses, but discarding them would lose source text.
    title_block: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    section_headings: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    signature_block: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Hard deletion deadline; see purge_expired_documents.
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    clauses: Mapped[list[Clause]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="Clause.order_index",
    )


class Clause(Base):
    __tablename__ = "clauses"

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    # Stable identifier within its document; distinct from the surrogate primary key.
    clause_id: Mapped[str] = mapped_column(String(32))
    # The number printed in the source ("4", "2.1", "IV"); None for unnumbered clauses.
    clause_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    section_heading: Mapped[str | None] = mapped_column(String(256), nullable=True)
    text: Mapped[str] = mapped_column(Text)
    # "order" is reserved in SQL; the API still exposes this field as `order`.
    order_index: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document: Mapped[Document] = relationship(back_populates="clauses")

    __table_args__ = (Index("ix_clauses_document_order", "document_id", "order_index"),)


class StatuteEntry(Base):
    """Phase 3 statute knowledge base, its own table separate from lease-clause data.

    The JSON files under data/statute_kb/ (loaded via app.statute_kb.retrieval) remain
    the source of truth used by retrieval and Phase 4; this table exists for optional
    Postgres persistence, e.g. for future admin tooling. `id` is the human-assigned
    entry id (e.g. "MH_SEC_001"), not a surrogate key, so it can be referenced directly
    from generated explanations for citation traceability.
    """

    __tablename__ = "statute_entries"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    citation: Mapped[str] = mapped_column(Text)
    excerpt_text: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text)
    jurisdiction: Mapped[str] = mapped_column(String(32))
    topic_tags: Mapped[list[str]] = mapped_column(ARRAY(Text))
    last_verified_date: Mapped[str] = mapped_column(Date)

    __table_args__ = (
        CheckConstraint(
            "jurisdiction IN ('Maharashtra', 'Delhi', 'Central')", name="ck_statute_entries_jurisdiction"
        ),
        Index("ix_statute_entries_jurisdiction", "jurisdiction"),
    )


class Analysis(Base):
    """Risk, statute and explanation review of one uploaded document.

    One row per document. It is written by a background job that can take minutes when an
    LLM provider is configured, so it carries a status and progress the UI polls. It cascades
    with its document, so the upload retention window removes it too.
    """

    __tablename__ = "analyses"

    document_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    )
    status: Mapped[str] = mapped_column(String(16))  # running | done | failed
    jurisdiction: Mapped[str | None] = mapped_column(String(32), nullable=True)
    explanations_available: Mapped[bool] = mapped_column(default=False)
    progress_done: Mapped[int] = mapped_column(Integer, default=0)
    progress_total: Mapped[int] = mapped_column(Integer, default=0)
    # {"clauses": [...], "cross_clause": [...]}, shaped like the saved Phase 4 results so the
    # same UI renders both.
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
