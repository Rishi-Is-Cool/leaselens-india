"""Shared low-level LLM chat-completion client for any OpenAI-compatible free-tier
provider (Groq, Gemini's OpenAI-compatible endpoint, OpenRouter free models).

Handles what every LLM-calling part of this project needs: throttling, retry-with-
backoff on transient errors, and detecting a free-tier daily-quota exhaustion (which
retrying cannot fix today). It does NOT handle response caching or prompt-specific
parsing - callers own that, since what's cacheable and how a reply is parsed differs
per use (Phase 2's classifier vs. Phase 4's explanation generator).

`app/classifier/llm.py` predates this module and has its own equivalent, self-contained
retry loop; it is deliberately left as-is (already tested and shipped) rather than
refactored onto this shared client under time pressure. Phase 4 (app/explain/) uses this
module directly.

    LLM_BASE_URL   e.g. https://api.groq.com/openai/v1
    LLM_API_KEY    the provider's key
    LLM_MODEL      e.g. qwen/qwen3.8-27b
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


class LLMNotConfiguredError(RuntimeError):
    pass


class DailyQuotaExceededError(RuntimeError):
    """The provider's free-tier daily token/request cap is hit; retrying won't help today."""


def settings() -> dict[str, str]:
    return {
        "base_url": os.environ.get("LLM_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/"),
        "api_key": os.environ.get("LLM_API_KEY", ""),
        "model": os.environ.get("LLM_MODEL", "llama-3.3-70b-versatile"),
        "min_interval": os.environ.get("LLM_MIN_INTERVAL_SECONDS", "2.5"),
    }


def is_configured() -> bool:
    return bool(settings()["api_key"])


class LLMClient:
    def __init__(self, *, max_retries: int = 6, max_tokens: int = 900, model: str | None = None):
        cfg = settings()
        if not cfg["api_key"]:
            raise LLMNotConfiguredError(
                "LLM_API_KEY is not set. Add a free-tier key to .env (see .env.example)."
            )
        self.cfg = cfg
        if model:
            self.cfg = {**cfg, "model": model}
        self.max_retries = max_retries
        self.max_tokens = max_tokens
        self._last_call = 0.0
        self.client = httpx.Client(timeout=60)
        self.api_calls = 0

    def _throttle(self) -> None:
        wait = float(self.cfg["min_interval"]) - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

    def chat(self, messages: list[dict], *, temperature: float = 0) -> str:
        """One chat-completion call. Raises DailyQuotaExceededError on a daily cap (not
        worth retrying today) or RuntimeError after exhausting max_retries on transient
        failures (empty replies, 5xx, per-minute rate limits)."""
        body = {
            "model": self.cfg["model"],
            "messages": messages,
            "temperature": temperature,
            # Reasoning models (e.g. Groq's gpt-oss) spend tokens on hidden reasoning
            # before the answer; too low a budget truncates the reply before it appears.
            "max_tokens": self.max_tokens,
        }
        headers = {"Authorization": f"Bearer {self.cfg['api_key']}"}
        for attempt in range(self.max_retries):
            self._throttle()
            response = self.client.post(f"{self.cfg['base_url']}/chat/completions", json=body, headers=headers)
            self.api_calls += 1
            if response.status_code == 429:
                body_text = response.text
                if "per day" in body_text.lower():
                    raise DailyQuotaExceededError(
                        f"{self.cfg['model']} hit its free-tier daily limit: {body_text[:200]}"
                    )
                if attempt == self.max_retries - 1:
                    break  # waiting out the limit only to give up afterwards helps nobody
                retry_after = response.headers.get("retry-after")
                time.sleep(float(retry_after) if retry_after and retry_after.replace(".", "").isdigit() else 5 * 2**attempt)
                continue
            if response.status_code >= 500:
                time.sleep(5 * 2**attempt)
                continue
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            if content:
                return content
        raise RuntimeError(
            "LLM provider kept returning empty/failed replies; try again later."
        )
