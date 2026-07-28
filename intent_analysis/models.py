"""Intent Analysis System — data contract.

Mirrors:
  - schema/company_input.schema.json
  - schema/intent_output.schema.json
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional


class EvidenceType(str, Enum):
    """Categories of intent evidence."""

    HIRING = "hiring"
    PR = "pr"
    FUNDING = "funding"
    TECH_STACK = "tech_stack"
    NEWS = "news"
    SOCIAL_MEDIA = "social_media"


@dataclass
class CompanyInput:
    """Company identity supplied to the engine."""

    name: str
    domain: str
    linkedin: Optional[str] = None


@dataclass
class EvidenceItem:
    """One piece of discovered intent evidence."""

    evidence_url: str
    evidence_type: EvidenceType
    details: str

    def to_dict(self) -> dict:
        d = asdict(self)
        d["evidence_type"] = self.evidence_type.value
        return d


@dataclass
class IntentDetails:
    """Intent evidence returned by the engine for one company."""

    company: CompanyInput
    evidence: List[EvidenceItem] = field(default_factory=list)
    analyzed_at: Optional[str] = None  # ISO 8601 date-time

    def to_dict(self) -> dict:
        return {
            "company": asdict(self.company),
            "evidence": [e.to_dict() for e in self.evidence],
            "analyzed_at": self.analyzed_at,
        }
