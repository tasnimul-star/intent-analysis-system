"""OpenRouter provider — optional LLM structuring of the SD ai_mode answer.

Turns a free-text ScrapingDog /google/ai_mode answer into clean
[{"url", "details"}] evidence items for one company + evidence type. This is
optional (enabled with INTENT_USE_OPENROUTER=1); the engine regex-parses the
answer otherwise.

Reads OPENROUTER_API_KEY from the environment.
INTENT_LLM_MODEL selects the model (default: a small, cheap model).
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Tuple

import httpx

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-4o-mini"
DEFAULT_TIMEOUT = 60.0


class OpenRouterError(RuntimeError):
    pass


def _headers() -> Dict[str, str]:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise OpenRouterError("OPENROUTER_API_KEY is not set")
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def _model() -> str:
    return os.environ.get("INTENT_LLM_MODEL", DEFAULT_MODEL)


def structure_evidence(
    *,
    company_name: str,
    company_domain: str,
    evidence_type: str,
    answer: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> List[Tuple[str, str]]:
    """Return [(url, details)] extracted from an ai_mode answer.

    Keeps only evidence that is specifically about THIS company and matches the
    given evidence type.
    """
    prompt = (
        "You extract structured B2B intent evidence from a search answer.\n"
        f"Company: {company_name} (domain: {company_domain})\n"
        f"Evidence type: {evidence_type}\n\n"
        "From the answer below, extract every item that is genuine evidence of "
        "the given intent type FOR THIS COMPANY (ignore other companies, "
        "directories, or unrelated items). Each item needs a real source URL "
        "and a one-sentence detail.\n\n"
        f"Answer:\n{answer[:6000]}\n\n"
        "Respond with strict JSON only:\n"
        '{"items": [{"url": "https://...", "details": "one sentence"}]}\n'
        "If there is no valid evidence, return {\"items\": []}."
    )
    payload = {
        "model": _model(),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(OPENROUTER_URL, headers=_headers(), json=payload)
    if resp.status_code != 200:
        raise OpenRouterError(f"openrouter HTTP {resp.status_code}: {resp.text[:200]}")

    content = (
        resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
    )
    try:
        parsed = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return []

    out: List[Tuple[str, str]] = []
    for item in parsed.get("items", []) if isinstance(parsed, dict) else []:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        details = str(item.get("details") or "").strip()
        if url.startswith("http") and details:
            out.append((url, details))
    return out
