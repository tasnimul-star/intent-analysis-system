# Intent Analysis System

Takes **company details** and returns **intent evidence** — buying/growth signals
discovered for that specific company, each with a source URL, a type, and details.

This repository is **separate from the sourcing model.**

## Input / Output

```
Input:   { name, domain, linkedin? }
Output:  { company, evidence: [ { evidence_url, evidence_type, details } ], analyzed_at }
```

- `schema/company_input.schema.json` — input contract (JSON Schema)
- `schema/intent_output.schema.json` — output contract (JSON Schema)
- `intent_analysis/models.py` — same contract as Python dataclasses

## Evidence types

`hiring` · `pr` · `funding` · `tech_stack` · `news` · `social_media`

## How it works (end to end)

**ScrapingDog-first** — SD does both discovery and extraction. For each evidence type:

1. **Discovery** — ScrapingDog **Google search** finds candidate evidence URLs.
   (Exa `/search` is an optional fallback: set `INTENT_DISCOVERY=exa`.)
2. **Extraction** — ScrapingDog **AI mode** (`ai_query`) reads each page and
   returns a one-sentence `details` string, or `NONE` when the page isn't
   evidence for this company.
3. **Verify (optional)** — an OpenRouter LLM second pass re-confirms the item is
   genuine evidence for *this* company (`INTENT_USE_OPENROUTER=1`).

Only confirmed items are returned.

```
company ─▶ SD Google search ─▶ SD AI extract ─▶ (opt) OpenRouter verify ─▶ evidence[]
```

## Usage

```bash
pip install -r requirements.txt

export EXA_API_KEY=...
export SCRAPINGDOG_API_KEY=...
export OPENROUTER_API_KEY=...

python cli.py --name "Acme Inc" --domain acme.com
# optional: restrict evidence types
python cli.py --name "Acme Inc" --domain acme.com --types hiring funding news
```

Or as a library:

```python
from intent_analysis import CompanyInput, analyze_intent

result = analyze_intent(CompanyInput(name="Acme Inc", domain="acme.com"))
print(result.to_dict())
```

## Configuration

| Env var | Purpose | Required |
|---------|---------|----------|
| `SCRAPINGDOG_API_KEY` | SD Google search + AI extraction (primary) | yes |
| `EXA_API_KEY` | Optional discovery fallback (`INTENT_DISCOVERY=exa`) | no |
| `OPENROUTER_API_KEY` | Optional LLM verify pass (`INTENT_USE_OPENROUTER=1`) | no |
| `INTENT_LLM_MODEL` | Model override (default `openai/gpt-4o-mini`) | no |

See `.env.example`. Only `SCRAPINGDOG_API_KEY` is needed for the default path.
