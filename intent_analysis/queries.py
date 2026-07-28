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


def build_ai_mode_query(
    evidence_type: EvidenceType, company_name: str, company_domain: str
) -> str:
    """ScrapingDog /google/ai_mode question for one evidence type.

    Asks the AI-mode search to find specific evidence for the company AND cite
    the source URLs, so the answer can be parsed into evidence items.
    """
    what = {
        EvidenceType.HIRING: "actively hiring, open job roles, or a hiring surge",
        EvidenceType.PR: "recent press releases, announcements, or awards",
        EvidenceType.FUNDING: "a recent funding round, investment, or acquisition",
        EvidenceType.TECH_STACK: "technologies it uses, adopted, or built with",
        EvidenceType.NEWS: "recent company news, a launch, expansion, or partnership",
        EvidenceType.SOCIAL_MEDIA: "recent notable social media posts or updates",
    }[evidence_type]
    return (
        f"Find evidence that {company_name} (website {company_domain}) has {what}. "
        f"For each piece of evidence, give the exact source URL followed by one "
        f"concise sentence describing it and its date if known. Only include "
        f"evidence specifically about {company_name}. If there is none, reply NONE."
    )


def all_types() -> List[EvidenceType]:
    return list(EvidenceType)
