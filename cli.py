#!/usr/bin/env python3
"""CLI for the intent analysis system.

Usage:
  export EXA_API_KEY=...
  export SCRAPINGDOG_API_KEY=...
  export OPENROUTER_API_KEY=...
  python cli.py --name "Acme Inc" --domain acme.com [--linkedin URL] \
      [--types hiring funding news]

Prints the IntentDetails result as JSON.
"""

from __future__ import annotations

import argparse
import json
import sys

from intent_analysis import CompanyInput, EvidenceType, analyze_intent


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Analyze company intent evidence.")
    parser.add_argument("--name", required=True, help="Company name")
    parser.add_argument("--domain", required=True, help="Company domain (e.g. acme.com)")
    parser.add_argument("--linkedin", default=None, help="Company LinkedIn URL (optional)")
    parser.add_argument(
        "--types",
        nargs="*",
        choices=[t.value for t in EvidenceType],
        default=None,
        help="Subset of evidence types to check (default: all)",
    )
    args = parser.parse_args(argv)

    company = CompanyInput(name=args.name, domain=args.domain, linkedin=args.linkedin)
    evidence_types = (
        [EvidenceType(t) for t in args.types] if args.types else None
    )

    result = analyze_intent(company, evidence_types=evidence_types)
    print(json.dumps(result.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
