"""Per-visitor request limits for the expensive endpoints on a public host.

Uploads run OCR and segmentation, reviews and chat spend the LLM provider's free-tier
quota; one visitor looping on any of them would take the app down for everyone. Limits
are in-memory (one server process on the free tier) and off unless configured.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.config import get_settings

WINDOW_SECONDS = 3600


class RateLimiter:
    def __init__(self, limit: int, window: float = WINDOW_SECONDS):
        self.limit = limit
        self.window = window
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, now: float | None = None) -> bool:
        if self.limit <= 0:
            return True
        now = time.monotonic() if now is None else now
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            return True


def visitor(request: Request) -> str:
    # Behind the host's proxy the socket peer is the proxy; the first forwarded address is
    # the visitor. Spoofing it only moves a caller into a different bucket of the same size.
    forwarded = request.headers.get("x-forwarded-for", "")
    return forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")


def limited(name: str, limit_setting: str):
    """A dependency enforcing `settings.<limit_setting>` requests per hour per visitor."""
    limiter = RateLimiter(getattr(get_settings(), limit_setting))

    def dependency(request: Request) -> None:
        if not limiter.allow(visitor(request)):
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"Too many {name} from this connection. Please try again in an hour.",
            )

    dependency.limiter = limiter  # exposed for tests
    return dependency
