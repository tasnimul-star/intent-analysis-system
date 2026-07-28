"""Intent Analysis System — data contract.

Schema only: these types define the input/output contract for the intent
analysis engine. No provider integrations or scoring logic yet.

Mirrors:
  - schema/company_input.schema.json
  - schema/intent_output.schema.json
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class SignalType(str, Enum):
    """Supported intent signal categories."""

    HIRING = "hiring"
    PR = "pr"
    FUNDING = "funding"
    TECH_STACK = "tech_stack"
    NEWS = "news"
    SOCIAL_MEDIA = "social_media"


@dataclass
class CompanyInput:
    """Company identity supplied to the engine.

    At least one of ``website``, ``domain``, or ``linkedin`` should be provided
    in addition to ``name`` so the company can be resolved unambiguously.
    """

    name: str
    website: Optional[str] = None
    domain: Optional[str] = None
    linkedin: Optional[str] = None
    location: Optional[str] = None
    industry: Optional[str] = None
    # Optional subset of signal types to check. Empty/None => check all.
    requested_signal_types: Optional[List[SignalType]] = None


@dataclass
class Evidence:
    """Supporting evidence for a single intent signal."""

    url: str
    source: Optional[str] = None
    snippet: Optional[str] = None
    published_at: Optional[str] = None  # ISO 8601 date-time


@dataclass
class IntentSignal:
    """One discovered intent signal for a company."""

    type: SignalType
    found: bool
    summary: Optional[str] = None
    confidence: Optional[float] = None  # 0.0 - 1.0
    observed_at: Optional[str] = None  # ISO 8601 date-time
    evidence: List[Evidence] = field(default_factory=list)


@dataclass
class IntentDetails:
    """Intent details returned by the engine for one company."""

    company: CompanyInput
    signals: List[IntentSignal] = field(default_factory=list)
    analyzed_at: Optional[str] = None  # ISO 8601 date-time


def analyze_intent(company: CompanyInput) -> IntentDetails:
    """Analyze a company and return its intent details.

    Not implemented yet — this repository defines the contract only. A future
    implementation will fan out one checker per requested signal type, gather
    evidence, and assemble the IntentDetails result.
    """
    raise NotImplementedError("intent analysis engine is not implemented yet")
