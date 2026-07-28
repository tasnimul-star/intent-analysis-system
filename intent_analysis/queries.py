"""Per-evidence-type query templates.

- build_query: the Google/Exa discovery query (find candidate pages).
- build_ai_query: the ScrapingDog AI-mode extraction question (pull details).
"""

from __future__ import annotations

from typing import List

from .models import EvidenceType


def build_query(evidence_type: EvidenceType, company_name: str) -> str:
    """Discovery query for one evidence type and company."""
    templates = {
        EvidenceType.HIRING: (
            f'{company_name} hiring OR "we are hiring" OR careers OR open roles OR job openings'
        ),
        EvidenceType.PR: (
            f'{company_name} press release OR announcement OR "announces" OR award'
        ),
        EvidenceType.FUNDING: (
            f'{company_name} funding OR raised OR "Series A" OR "Series B" OR investment OR acquisition'
        ),
        EvidenceType.TECH_STACK: (
            f'{company_name} technology stack OR "built with" OR engineering blog OR integrations OR API'
        ),
        EvidenceType.NEWS: (
            f'{company_name} news OR launch OR expansion OR partnership'
        ),
        EvidenceType.SOCIAL_MEDIA: (
            f'{company_name} LinkedIn post OR announcement OR update'
        ),
    }
    return templates[evidence_type]


def build_ai_query(evidence_type: EvidenceType, company_name: str) -> str:
    """ScrapingDog AI-mode extraction question for one evidence type.

    Instructs the AI to confirm the page is about THIS company and the given
    intent type, then summarize; otherwise return NONE.
    """
    what = {
        EvidenceType.HIRING: "actively hiring, open roles, or a hiring surge",
        EvidenceType.PR: "a press release, announcement, or award",
        EvidenceType.FUNDING: "a funding round, investment, or acquisition",
        EvidenceType.TECH_STACK: "technologies it uses, adopted, or built with",
        EvidenceType.NEWS: "recent company news, a launch, expansion, or partnership",
        EvidenceType.SOCIAL_MEDIA: "a notable social media post or update",
    }[evidence_type]
    return (
        f"Does this page show that {company_name} has {what}? "
        f"If and only if the page is about {company_name}, answer in one concise "
        f"sentence describing the specific evidence and its date if shown. "
        f"If the page is not about {company_name} or shows no such evidence, "
        f"answer exactly: NONE"
    )


def all_types() -> List[EvidenceType]:
    return list(EvidenceType)
