"""Baseline #2: an LLM classifying clauses, through any OpenAI-compatible chat endpoint.

Built for free-tier providers (Groq, Google Gemini's OpenAI-compatible endpoint,
OpenRouter free models): every setting comes from `.env`, requests are throttled, 429s
are retried with back-off, and each answer is cached on disk so an interrupted run resumes
and a repeat run costs nothing.

    LLM_BASE_URL   e.g. https://api.groq.com/openai/v1
    LLM_API_KEY    the provider's key
    LLM_MODEL      e.g. llama-3.3-70b-versatile
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

from app.classifier.dataset import LABELS

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")

CACHE_PATH = ROOT / "data" / ".llm_cache.jsonl"
PROMPT_VERSION = "v1"

SYSTEM_PROMPT = """You assess residential lease clauses for a tenant-protection tool.
Rate ONE clause's risk to the tenant using exactly these criteria:

GREEN  - Standard, balanced, low-risk term. Describes ordinary obligations, definitions,
         recitals, or mutual/fair arrangements. Nothing a tenant needs to worry about.
YELLOW - Worth attention. Enforceable-looking but one-sided or burdensome: fees and late
         charges, strict deadlines, broad tenant duties or landlord discretion, ambiguity,
         costs shifted to the tenant. A careful tenant should read and possibly negotiate it.
RED    - Potentially serious concern. The tenant gives up important rights or takes on
         severe or open-ended liability: waivers of legal remedies or habitability,
         self-help eviction, forfeiture, penalties out of proportion to harm, or terms that
         may not be enforceable.

You flag potential concerns only; you do not give legal conclusions.
Reply with ONLY a JSON object, no other text:
{"label": "GREEN|YELLOW|RED", "probabilities": {"GREEN": p, "YELLOW": p, "RED": p}}
The three probabilities must be your honest confidence for each class and sum to 1."""


class LLMNotConfiguredError(RuntimeError):
    pass


class DailyQuotaExceededError(RuntimeError):
    """The provider's free-tier daily token/request cap is hit; retrying won't help today."""


def settings() -> dict[str, str]:
    values = {
        "base_url": os.environ.get("LLM_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/"),
        "api_key": os.environ.get("LLM_API_KEY", ""),
        "model": os.environ.get("LLM_MODEL", "llama-3.3-70b-versatile"),
        "min_interval": os.environ.get("LLM_MIN_INTERVAL_SECONDS", "2.5"),
    }
    return values


def is_configured() -> bool:
    return bool(settings()["api_key"])


def _cache_key(model: str, shots: list[tuple[str, str]], text: str) -> str:
    payload = json.dumps([PROMPT_VERSION, model, shots, text], ensure_ascii=False)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def _load_cache() -> dict[str, dict]:
    if not CACHE_PATH.exists():
        return {}
    cache: dict[str, dict] = {}
    for line in CACHE_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            cache[row["key"]] = row["value"]
    return cache


def _append_cache(key: str, value: dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CACHE_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"key": key, "value": value}, ensure_ascii=False) + "\n")


def _messages(text: str, shots: list[tuple[str, str]]) -> list[dict]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for shot_text, shot_label in shots:
        messages.append({"role": "user", "content": f"Clause: {shot_text}"})
        answer = {"label": shot_label, "probabilities": {k: (0.9 if k == shot_label else 0.05) for k in LABELS}}
        messages.append({"role": "assistant", "content": json.dumps(answer)})
    messages.append({"role": "user", "content": f"Clause: {text}"})
    return messages


def parse_answer(content: str) -> dict[str, float]:
    """Return normalised probabilities from the model's reply; raises ValueError if unusable."""
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        raise ValueError(f"no JSON in reply: {content[:120]!r}")
    data = json.loads(match.group(0))
    label = str(data.get("label", "")).strip().upper()
    raw = data.get("probabilities") or {}
    probs = {k: max(float(raw.get(k, 0.0)), 0.0) for k in LABELS}
    if label not in LABELS:
        raise ValueError(f"bad label in reply: {label!r}")
    total = sum(probs.values())
    if total <= 0:
        probs = {k: (0.8 if k == label else 0.1) for k in LABELS}
    else:
        probs = {k: v / total for k, v in probs.items()}
    # The stated label wins ties; if it disagrees with the argmax, trust the stated label.
    if max(probs, key=probs.get) != label:
        top = max(probs.values())
        probs[label] = max(probs[label], top)
        total = sum(probs.values())
        probs = {k: v / total for k, v in probs.items()}
    return probs


class LLMClassifier:
    def __init__(self, shots: list[tuple[str, str]] | None = None, *, max_retries: int = 6):
        cfg = settings()
        if not cfg["api_key"]:
            raise LLMNotConfiguredError(
                "LLM_API_KEY is not set. Add a free-tier key to .env (see .env.example)."
            )
        self.cfg = cfg
        self.shots = shots or []
        self.max_retries = max_retries
        self.cache = _load_cache()
        self._last_call = 0.0
        self.client = httpx.Client(timeout=60)
        self.api_calls = 0

    def _throttle(self) -> None:
        wait = float(self.cfg["min_interval"]) - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

    def _call(self, text: str) -> str:
        body = {
            "model": self.cfg["model"],
            "messages": _messages(text, self.shots),
            "temperature": 0,
            # Reasoning models (e.g. Groq's gpt-oss) spend tokens on hidden reasoning
            # before the JSON answer; a low budget truncates the reply mid-JSON.
            "max_tokens": 500,
        }
        headers = {"Authorization": f"Bearer {self.cfg['api_key']}"}
        for attempt in range(self.max_retries):
            self._throttle()
            response = self.client.post(f"{self.cfg['base_url']}/chat/completions", json=body, headers=headers)
            self.api_calls += 1
            if response.status_code == 429:
                body_text = response.text
                # A per-day cap won't clear within this run; every other 429 is a
                # per-minute/second burst limit and is worth waiting out.
                if "per day" in body_text.lower() or "tokens per day" in body_text.lower():
                    raise DailyQuotaExceededError(
                        f"{self.cfg['model']} hit its free-tier daily limit: {body_text[:200]}"
                    )
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
            # Empty content with finish_reason "length": a reasoning model spent the
            # whole token budget on hidden reasoning and never reached the answer.
        raise RuntimeError(
            "LLM provider kept returning empty/failed replies; try again later (results so far are cached)."
        )

    def predict_proba_one(self, text: str) -> dict[str, float]:
        key = _cache_key(self.cfg["model"], self.shots, text)
        if key in self.cache:
            return self.cache[key]["probs"]
        content = self._call(text)
        try:
            probs = parse_answer(content)
        except (ValueError, json.JSONDecodeError):
            content = self._call(text)  # one retry on a malformed reply
            probs = parse_answer(content)
        self.cache[key] = {"probs": probs}
        _append_cache(key, {"probs": probs})
        return probs
