"""Exa provider — neural search for intent evidence URLs.

Uses the Exa /search endpoint to discover candidate evidence pages for a
company, and /contents to pull page text when a scrape is not needed.

Reads EXA_API_KEY from the environment.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx

EXA_SEARCH_URL = "https://api.exa.ai/search"
EXA_CONTENTS_URL = "https://api.exa.ai/contents"
DEFAULT_TIMEOUT = 30.0


class ExaError(RuntimeError):
    pass


def _headers() -> Dict[str, str]:
    api_key = os.environ.get("EXA_API_KEY")
    if not api_key:
        raise ExaError("EXA_API_KEY is not set")
    return {"x-api-key": api_key, "Content-Type": "application/json"}


def search(
    query: str,
    *,
    num_results: int = 5,
    include_domains: Optional[List[str]] = None,
    start_published_date: Optional[str] = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> List[Dict[str, Any]]:
    """Return a list of {url, title, text, published_date} for a query.

    ``include_domains`` restricts results (e.g. to the company domain).
    ``start_published_date`` (ISO 8601) restricts to recent evidence.
    """
    payload: Dict[str, Any] = {
        "query": query,
        "numResults": num_results,
        "contents": {"text": {"maxCharacters": 2000}},
    }
    if include_domains:
        payload["includeDomains"] = include_domains
    if start_published_date:
        payload["startPublishedDate"] = start_published_date

    with httpx.Client(timeout=timeout) as client:
        resp = client.post(EXA_SEARCH_URL, headers=_headers(), json=payload)
    if resp.status_code != 200:
        raise ExaError(f"exa search HTTP {resp.status_code}: {resp.text[:200]}")

    results = resp.json().get("results") or []
    out: List[Dict[str, Any]] = []
    for r in results:
        out.append(
            {
                "url": r.get("url", ""),
                "title": r.get("title", ""),
                "text": r.get("text", "") or "",
                "published_date": r.get("publishedDate", ""),
            }
        )
    return out


def contents(url: str, *, max_chars: int = 4000, timeout: float = DEFAULT_TIMEOUT) -> str:
    """Return the extracted text for a single URL via Exa /contents."""
    payload = {"ids": [url], "text": {"maxCharacters": max_chars}}
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(EXA_CONTENTS_URL, headers=_headers(), json=payload)
    if resp.status_code != 200:
        raise ExaError(f"exa contents HTTP {resp.status_code}: {resp.text[:200]}")
    results = resp.json().get("results") or []
    if not results:
        return ""
    return results[0].get("text", "") or ""
