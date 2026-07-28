# Intent Analysis System

Standalone service that takes **company details** and returns **intent details** —
structured buying/growth signals discovered for that specific company.

This repository is **separate from the sourcing model**. It defines the contract
(input/output schema) for the intent analysis system. It intentionally contains
**no working implementation yet** — this is the schema/interface first.

## What it does

```
Input:  company identity  (name, website, linkedin, …)
            │
            ▼
   Intent Analysis Engine
   (requests signal types → checks each for the company → attaches evidence)
            │
            ▼
Output: intent details  (list of verified intent signals with evidence)
```

Given a company, the engine requests a set of **signal types** and checks each one
for that company, then returns the discovered signals with supporting evidence.

## Signal types

| Type | Meaning |
|------|---------|
| `hiring` | Active job postings / hiring surges relevant to buying intent |
| `pr` | Press releases, announcements, awards |
| `funding` | Funding rounds, investments, M&A |
| `tech_stack` | Technologies adopted, added, or removed |
| `news` | General company news and market events |
| `social_media` | Social posts, engagement, executive activity |

## Use cases

1. **Enrichment** — after a company is selected, run this to discover *additional*
   intent signals beyond whatever first surfaced it.
2. **Refresh** — re-run for existing companies/leads to keep intent signals current.

## Contract

- `schema/company_input.schema.json` — the input company object (JSON Schema).
- `schema/intent_output.schema.json` — the output intent details object (JSON Schema).
- `intent_analysis/models.py` — the same contract as Python dataclasses.

## Status

Schema only. No provider integrations, scoring, or incentive logic yet — those are
deliberately out of scope for this first push.
