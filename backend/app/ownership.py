"""Which browser an uploaded lease belongs to.

There are no accounts. The frontend creates a random id once per browser and sends it as
`X-Client-Id` on every request; uploads store a hash of it, and the lease, its review and
its chat are only ever served back to a request carrying the same id. Without this, a
shared host would list and serve every visitor's lease to every other visitor.

Documents uploaded without the header (tests, local scripts) have no owner and stay
reachable by their unguessable id, but are never listed.
"""

from __future__ import annotations

import hashlib
import uuid

from fastapi import Header, HTTPException, status
from sqlalchemy.orm import Session

from app.models import Document

CLIENT_HEADER = "X-Client-Id"


def client_key(x_client_id: str | None = Header(default=None, max_length=128)) -> str | None:
    """The stored form of the caller's client id: a hash, so the database alone cannot be
    used to impersonate a browser."""
    if not x_client_id or not x_client_id.strip():
        return None
    return hashlib.sha256(x_client_id.strip().encode("utf-8")).hexdigest()


def owned_document_or_404(session: Session, document_id: uuid.UUID, key: str | None) -> Document:
    document = session.get(Document, document_id)
    # Someone else's lease is reported exactly like a missing one, so ids cannot be probed.
    if document is None or (document.owner_key is not None and document.owner_key != key):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")
    return document
