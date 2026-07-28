"""OpenRouter provider — LLM extraction/verification of intent evidence.

Given a company and scraped page text, ask a model whether the page is genuine
intent evidence of a given type and, if so, produce a concise ``details`` string.

Reads OPENROUTER_API_KEY from the environment.
INTENT_LLM_MODEL selects the model (default: a small, cheap model).
"""

from __future__ import annotations

import json
import os
from typing import Dict, Optional

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


def verify_evidence(
    *,
    company_name: str,
    company_domain: str,
    evidence_type: str,
    url: str,
    page_text: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> Optional[str]:
    """Return a ``details`` string if the page is genuine intent evidence, else None.

    The model must confirm the page is about *this* company and matches the
    requested evidence type before details are returned.
    """
    prompt = (
        "You verify B2B intent evidence. Given a company and a web page, decide "
        "whether the page is genuine evidence of the specified intent type for "
        "THIS company (not a different company, directory, or unrelated page).\n\n"
        f"Company: {company_name} (domain: {company_domain})\n"
        f"Intent type: {evidence_type}\n"
        f"Page URL: {url}\n"
        f"Page text (truncated):\n{page_text[:4000]}\n\n"
        "Respond with strict JSON only:\n"
        '{"is_evidence": true|false, "details": "one concise sentence describing '
        'the evidence and why it signals intent, or empty if not evidence"}'
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
        return None
    if not parsed.get("is_evidence"):
        return None
    details = str(parsed.get("details") or "").strip()
    return details or None
