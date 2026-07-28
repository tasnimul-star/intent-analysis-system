"""ScrapingDog provider — the primary engine for discovery and extraction.

Three capabilities, all off the ScrapingDog API:
  - google_search(query)        -> discover candidate evidence URLs (SERP)
  - scrape_ai(url, ai_query)    -> AI-mode extraction of structured details
  - scrape_text(url)            -> raw page text (fallback / for LLM verify)

Reads SCRAPINGDOG_API_KEY from the environment.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

import httpx

SCRAPINGDOG_SCRAPE_URL = "https://api.scrapingdog.com/scrape"
SCRAPINGDOG_GOOGLE_URL = "https://api.scrapingdog.com/google"
DEFAULT_TIMEOUT = 40.0
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


def scrape_ai(
    url: str, ai_query: str, *, dynamic: bool = False, timeout: float = DEFAULT_TIMEOUT
) -> str:
    """AI-mode extraction: ask ScrapingDog to pull an answer from the page.

    Uses the ``ai_query`` parameter so ScrapingDog's AI extraction returns a
    focused answer rather than raw HTML.
    """
    params = {
        "api_key": _api_key(),
        "url": url,
        "ai_query": ai_query,
        "dynamic": "true" if dynamic else "false",
    }
    with httpx.Client(timeout=timeout) as client:
        resp = client.get(SCRAPINGDOG_SCRAPE_URL, params=params)
    if resp.status_code != 200:
        raise ScrapingDogError(
            f"scrapingdog ai HTTP {resp.status_code}: {resp.text[:150]}"
        )
    # AI mode may return JSON ({"ai_response": ...}) or plain text.
    ctype = resp.headers.get("content-type", "")
    if ctype.startswith("application/json"):
        try:
            data = resp.json()
        except ValueError:
            return resp.text.strip()
        for key in ("ai_response", "ai_result", "answer", "data", "result"):
            val = data.get(key) if isinstance(data, dict) else None
            if val:
                return val if isinstance(val, str) else str(val)
        return str(data)
    return _strip_html(resp.text) if "<" in resp.text else resp.text.strip()


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
