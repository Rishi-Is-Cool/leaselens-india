"""Deletion of uploaded documents once their retention window has passed.

Uploaded leases are personal data, so the handoff's rule 8 requires them to be
deleted after a bounded window rather than kept indefinitely. The full policy —
where a user may opt in to saving a document to an account — is Phase 7 work. Until
then nothing is retained: every upload is deleted unconditionally once it expires.

Purging runs on each upload rather than on a scheduler, so the guarantee holds on a
free-tier host that sleeps and has no cron.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Document


def expiry_for_new_upload() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=get_settings().retention_hours)


def purge_expired_documents(session: Session) -> int:
    """Delete every document past its retention deadline. Clauses cascade."""
    now = datetime.now(timezone.utc)
    expired = session.scalars(
        select(Document.id).where(Document.expires_at.is_not(None), Document.expires_at <= now)
    ).all()
    if not expired:
        return 0
    session.execute(delete(Document).where(Document.id.in_(expired)))
    session.commit()
    return len(expired)
