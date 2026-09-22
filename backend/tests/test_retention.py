"""Uploaded leases are personal data; the retention window must actually delete them."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import Clause, Document
from app.retention import expiry_for_new_upload, purge_expired_documents

pytestmark = pytest.mark.skipif(SessionLocal is None, reason="DATABASE_URL not configured")


def _document(expires_at):
    return Document(
        filename="retention_test.pdf",
        content_type="application/pdf",
        byte_size=1,
        page_count=1,
        extraction_method="text",
        expires_at=expires_at,
        clauses=[Clause(clause_id="c001", section_heading=None, text="probe", order_index=0)],
    )


def test_expired_document_and_its_clauses_are_deleted():
    session = SessionLocal()
    try:
        stale = _document(datetime.now(timezone.utc) - timedelta(hours=1))
        session.add(stale)
        session.commit()
        stale_id = stale.id

        purge_expired_documents(session)

        assert session.get(Document, stale_id) is None
        orphans = session.scalar(
            select(func.count()).select_from(Clause).where(Clause.document_id == stale_id)
        )
        assert orphans == 0
    finally:
        session.close()


def test_unexpired_document_is_kept():
    session = SessionLocal()
    try:
        fresh = _document(datetime.now(timezone.utc) + timedelta(hours=6))
        session.add(fresh)
        session.commit()
        fresh_id = fresh.id

        purge_expired_documents(session)

        assert session.get(Document, fresh_id) is not None
        session.delete(session.get(Document, fresh_id))
        session.commit()
    finally:
        session.close()


def test_new_uploads_get_a_deadline_in_the_future():
    assert expiry_for_new_upload() > datetime.now(timezone.utc)
