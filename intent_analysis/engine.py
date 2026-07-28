"""Intent analysis engine — end to end, ScrapingDog-first.

For a company, for each requested evidence type:
  1. SD /google/ai_mode  — AI-mode search finds evidence + cites source URLs.
                           The answer is parsed into (url, details) pairs.
  2. SD /google (SERP)   — fallback discovery when ai_mode yields no URLs;
                           snippet becomes the details.
  3. OpenRouter (opt)    — INTENT_USE_OPENROUTER=1 structures the raw ai_mode
                           answer into clean {url, details} items instead of the
                           regex parser.

ScrapingDog does the heavy lifting (both AI-mode analysis and SERP discovery).
"""

from __future__ import annotations

import datetime as _dt
import os
import re
from typing import List, Optional, Tuple

from .models import CompanyInput, EvidenceItem, EvidenceType, IntentDetails
from .providers import scrapingdog
from .queries import all_types, build_ai_mode_query, build_query

SERP_RESULTS_PER_TYPE = 4
_URL_RE = re.compile(r"https?://[^\s)>\]\"'}]+")
_TRAIL_PUNCT = ".,;:!?)\"'"


def _utc_now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def _is_none_answer(text: str) -> bool:
    t = (text or "").strip().lower()
    return not t or t.startswith("none") or len(t) < 12


def _parse_evidence_from_answer(answer: str) -> List[Tuple[str, str]]:
    """Extract (url, details) pairs from a free-text AI-mode answer.

    For each URL found, the details are the surrounding line (URL removed),
    falling back to a snippet of the answer.
    """
    if _is_none_answer(answer):
        return []
    pairs: List[Tuple[str, str]] = []
    seen = set()
    for line in re.split(r"[\n\r]+", answer):
        urls = _URL_RE.findall(line)
        if not urls:
            continue
        # Details = the line with URLs stripped out, cleaned.
        detail = _URL_RE.sub("", line).strip(" -•\t").strip()
        for raw_url in urls:
            url = raw_url.rstrip(_TRAIL_PUNCT)
            if url in seen:
                continue
            seen.add(url)
            pairs.append((url, detail or answer.strip()[:200]))
    return pairs


def _discover_serp(company: CompanyInput, evidence_type: EvidenceType) -> List[Tuple[str, str]]:
    """SERP fallback: return (url, details) from ScrapingDog Google results."""
    query = build_query(evidence_type, company.name)
    try:
        hits = scrapingdog.google_search(query, results=SERP_RESULTS_PER_TYPE)
    except scrapingdog.ScrapingDogError as e:
        print(f"  [{evidence_type.value}] SERP fallback failed: {e}")
        return []
    out: List[Tuple[str, str]] = []
    for hit in hits:
        url = hit.get("url") or ""
        if not url:
            continue
        details = (hit.get("snippet") or hit.get("title") or "").strip()
        if details:
            out.append((url, details))
    return out


def _discover_exa(company: CompanyInput, evidence_type: EvidenceType) -> List[Tuple[str, str]]:
    """Last-resort discovery via Exa. Best-effort; needs EXA_API_KEY."""
    query = build_query(evidence_type, company.name)
    try:
        from .providers import exa

        return [
            (r["url"], (r.get("text") or r.get("title") or "").strip())
            for r in exa.search(query, num_results=SERP_RESULTS_PER_TYPE)
            if r.get("url") and (r.get("text") or r.get("title"))
        ]
    except Exception as e:  # noqa: BLE001 - Exa is an optional last resort
        print(f"  [{evidence_type.value}] exa fallback unavailable: {e}")
        return []


def _structure_with_openrouter(
    company: CompanyInput, evidence_type: EvidenceType, answer: str
) -> Optional[List[Tuple[str, str]]]:
    """Optional: use OpenRouter to structure the ai_mode answer. None on failure."""
    if os.environ.get("INTENT_USE_OPENROUTER", "0") != "1":
        return None
    try:
        from .providers import openrouter

        return openrouter.structure_evidence(
            company_name=company.name,
            company_domain=company.domain,
            evidence_type=evidence_type.value,
            answer=answer,
        )
    except Exception as e:  # noqa: BLE001 - optional refinement
        print(f"  [{evidence_type.value}] openrouter structuring skipped: {e}")
        return None


def _analyze_one_type(
    company: CompanyInput, evidence_type: EvidenceType
) -> List[EvidenceItem]:
    ai_query = build_ai_mode_query(evidence_type, company.name, company.domain)
    answer = ""
    try:
        answer = scrapingdog.google_ai_mode(ai_query)
    except scrapingdog.ScrapingDogError as e:
        print(f"  [{evidence_type.value}] ai_mode failed: {e}")

    pairs: List[Tuple[str, str]] = []
    if answer:
        structured = _structure_with_openrouter(company, evidence_type, answer)
        pairs = structured if structured is not None else _parse_evidence_from_answer(answer)

    # Fallback to SERP discovery when ai_mode produced no usable URLs.
    if not pairs:
        pairs = _discover_serp(company, evidence_type)

    # Last-resort discovery via Exa (only if configured; SD stays primary).
    if not pairs:
        pairs = _discover_exa(company, evidence_type)

    return [
        EvidenceItem(evidence_url=url, evidence_type=evidence_type, details=details)
        for url, details in pairs
        if url and details
    ]


def analyze_intent(
    company: CompanyInput,
    *,
    evidence_types: Optional[List[EvidenceType]] = None,
) -> IntentDetails:
    """Run the full intent analysis for a company across evidence types."""
    types = evidence_types or all_types()
    all_items: List[EvidenceItem] = []
    for evidence_type in types:
        print(f"Analyzing {evidence_type.value} for {company.name}...")
        all_items.extend(_analyze_one_type(company, evidence_type))

    return IntentDetails(
        company=company, evidence=all_items, analyzed_at=_utc_now_iso()
    )
