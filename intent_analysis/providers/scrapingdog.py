"""ScrapingDog provider — the primary engine for discovery and extraction.

Capabilities (all off the ScrapingDog API):
  - google_ai_mode(query) -> AI answer text (GET /google/ai_mode). A query->answer
    AI search (like Google's AI Overview) that summarizes and cites sources.
  - google_search(query)   -> SERP results [{url, title, snippet}] (GET /google).
  - scrape_text(url)       -> cleaned page text (GET /scrape), fallback for LLM use.

Reads SCRAPINGDOG_API_KEY from the environment.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List

import httpx

SCRAPINGDOG_SCRAPE_URL = "https://api.scrapingdog.com/scrape"
SCRAPINGDOG_GOOGLE_URL = "https://api.scrapingdog.com/google"
SCRAPINGDOG_AI_MODE_URL = "https://api.scrapingdog.com/google/ai_mode"
DEFAULT_TIMEOUT = 45.0
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


class ScrapingDogError(RuntimeError):
    pass


def _api_key() -> str:
    api_key = os.environ.get("SCRAPINGDOG_API_KEY")
    if not api_key:
        raise ScrapingDogError("SCRAPINGDOG_API_KEY is not set")
    return api_key


def _strip_html(html: str, *, max_chars: int = 6000) -> str:
    text = _TAG_RE.sub(" ", html or "")
    text = _WS_RE.sub(" ", text).strip()
    return text[:max_chars]


def google_ai_mode(query: str, *, timeout: float = DEFAULT_TIMEOUT) -> str:
    """Google AI-mode answer for a natural-language query (GET /google/ai_mode).

    Returns the AI answer as text. The query should ask for specific evidence
    plus source URLs so the answer can be parsed into evidence items.
    """
    params = {"api_key": _api_key(), "query": query, "country": "us"}
    with httpx.Client(timeout=timeout) as client:
        resp = client.get(SCRAPINGDOG_AI_MODE_URL, params=params)
    if resp.status_code != 200:
        raise ScrapingDogError(
            f"scrapingdog ai_mode HTTP {resp.status_code}: {resp.text[:150]}"
        )
    # Response may be JSON ({text|markdown|body|message|answer|ai_response: ...})
    # or plain text.
    ctype = resp.headers.get("content-type", "")
    if ctype.startswith("application/json"):
        try:
            data = resp.json()
        except ValueError:
            return resp.text.strip()
        if isinstance(data, dict):
            for key in ("ai_response", "answer", "text", "markdown", "body", "message"):
                val = data.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()
            return str(data)
        return str(data)
    body = resp.text or ""
    return _strip_html(body) if "<" in body else body.strip()


def google_search(
    query: str, *, results: int = 5, timeout: float = DEFAULT_TIMEOUT
) -> List[Dict[str, Any]]:
    """Discover candidate URLs via the ScrapingDog Google SERP endpoint.

    Returns a list of {url, title, snippet}.
    """
    params = {
        "api_key": _api_key(),
        "query": query,
        "results": str(results),
        "country": "us",
    }
    with httpx.Client(timeout=timeout) as client:
        resp = client.get(SCRAPINGDOG_GOOGLE_URL, params=params)
    if resp.status_code != 200:
        raise ScrapingDogError(
            f"scrapingdog google HTTP {resp.status_code}: {resp.text[:150]}"
        )
    try:
        data = resp.json()
    except ValueError:
        raise ScrapingDogError("scrapingdog google returned non-JSON")

    organic = data.get("organic_results") or data.get("organic_data") or []
    out: List[Dict[str, Any]] = []
    for r in organic:
        link = r.get("link") or r.get("url") or ""
        if not link:
            continue
        out.append(
            {
                "url": link,
                "title": r.get("title", ""),
                "snippet": r.get("snippet", "") or r.get("description", ""),
            }
        )
    return out


def scrape_text(url: str, *, max_chars: int = 6000, timeout: float = DEFAULT_TIMEOUT) -> str:
    """Return cleaned page text, escalating to dynamic render when the body is thin."""

    def _fetch(dynamic: bool) -> str:
        params = {
            "api_key": _api_key(),
            "url": url,
            "dynamic": "true" if dynamic else "false",
        }
        if dynamic:
            params["wait"] = "5000"
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(SCRAPINGDOG_SCRAPE_URL, params=params)
        if resp.status_code != 200:
            raise ScrapingDogError(
                f"scrapingdog HTTP {resp.status_code}: {resp.text[:150]}"
            )
        return resp.text or ""

    try:
        text = _strip_html(_fetch(False), max_chars=max_chars)
    except ScrapingDogError:
        text = ""
    if len(text) < 200:
        try:
            text = _strip_html(_fetch(True), max_chars=max_chars)
        except ScrapingDogError:
            pass
    return text
