"""Intent analysis engine — end to end, ScrapingDog-first.

For a company, for each requested evidence type:
  1. DISCOVERY  — ScrapingDog Google search finds candidate evidence URLs.
                  (Exa /search is an optional fallback when SD discovery yields
                  nothing or INTENT_DISCOVERY=exa.)
  2. EXTRACTION — ScrapingDog AI mode (ai_query) reads each page and returns a
                  one-sentence details string, or NONE if not evidence.
  3. VERIFY     — optional OpenRouter second pass (INTENT_USE_OPENROUTER=1) to
                  re-confirm the item is genuine evidence for THIS company.

Only confirmed items become EvidenceItem results. ScrapingDog does the heavy
lifting (both discovery and extraction).
"""

from __future__ import annotations

import datetime as _dt
import os
from typing import List, Optional

from .models import CompanyInput, EvidenceItem, EvidenceType, IntentDetails
from .providers import scrapingdog
from .queries import all_types, build_ai_query, build_query

RESULTS_PER_TYPE = 5
_NONE_MARKERS = ("none", "no evidence", "not about", "n/a")


def _utc_now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def _is_none_answer(text: str) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return True
    # Treat a leading NONE (or very short non-answers) as no evidence.
    return t.startswith("none") or t in _NONE_MARKERS or len(t) < 12


def _discover(company: CompanyInput, evidence_type: EvidenceType) -> List[dict]:
    """Find candidate URLs. ScrapingDog Google first, optional Exa fallback."""
    query = build_query(evidence_type, company.name)
    use_exa = os.environ.get("INTENT_DISCOVERY", "sd").lower() == "exa"
    if not use_exa:
        try:
            hits = scrapingdog.google_search(query, results=RESULTS_PER_TYPE)
            if hits:
                return hits
        except scrapingdog.ScrapingDogError as e:
            print(f"  [{evidence_type.value}] SD google failed: {e}")
    # Optional Exa fallback (only imported if used, so Exa key isn't required).
    try:
        from .providers import exa

        return [
            {"url": r["url"], "title": r.get("title", ""), "snippet": r.get("text", "")}
            for r in exa.search(query, num_results=RESULTS_PER_TYPE)
        ]
    except Exception as e:  # noqa: BLE001 - discovery fallback is best-effort
        print(f"  [{evidence_type.value}] exa fallback unavailable: {e}")
        return []


def _maybe_openrouter_confirm(
    company: CompanyInput, evidence_type: EvidenceType, url: str, details: str
) -> Optional[str]:
    """Optional OpenRouter second-pass confirmation. Returns details or None."""
    if os.environ.get("INTENT_USE_OPENROUTER", "0") != "1":
        return details
    try:
        from .providers import openrouter

        return openrouter.verify_evidence(
            company_name=company.name,
            company_domain=company.domain,
            evidence_type=evidence_type.value,
            url=url,
            page_text=details,
        )
    except Exception as e:  # noqa: BLE001 - verify is best-effort
        print(f"  [{evidence_type.value}] openrouter confirm skipped: {e}")
        return details


def _analyze_one_type(
    company: CompanyInput, evidence_type: EvidenceType
) -> List[EvidenceItem]:
    hits = _discover(company, evidence_type)
    ai_query = build_ai_query(evidence_type, company.name)

    items: List[EvidenceItem] = []
    for hit in hits:
        url = hit.get("url") or ""
        if not url:
            continue
        try:
            answer = scrapingdog.scrape_ai(url, ai_query)
        except scrapingdog.ScrapingDogError as e:
            print(f"  [{evidence_type.value}] SD ai scrape failed for {url}: {e}")
            continue
        if _is_none_answer(answer):
            continue

        details = _maybe_openrouter_confirm(company, evidence_type, url, answer.strip())
        if details:
            items.append(
                EvidenceItem(
                    evidence_url=url,
                    evidence_type=evidence_type,
                    details=details,
                )
            )
    return items


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
