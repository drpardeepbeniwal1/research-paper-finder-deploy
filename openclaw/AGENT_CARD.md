# Research Paper Finder — OpenClaw Agent Card

> This file is the authoritative definition for attaching the Research Paper Finder as a tool/skill inside OpenClaw.
> Place this file in your OpenClaw agent's `tools/` or `skills/` directory.

---

## Agent Identity

```yaml
agent_id: research-paper-finder
agent_name: Research Paper Finder
version: 2.0.0
type: tool
category: academic-research
description: |
  AI-powered deep research paper discovery. Searches 9 academic databases in parallel
  (arXiv, Semantic Scholar, OpenAlex, Google Scholar, PubMed, CORE, CrossRef, Europe PMC, BASE),
  uses NVIDIA Nemotron-70B LLM to analyze and score every paper for relevance,
  and produces three categorized PDF reports. Zero duplicate papers.
auth: api_key
```

---

## Capabilities

| Capability | Description |
|---|---|
| Deep paper search | Multi-source search across 9 free databases |
| AI query expansion | LLM generates 14 targeted search terms per query |
| Relevance scoring | LLM scores each paper 0–100 with reasoning |
| Year filtering | Strict year range filtering at source level |
| Associated papers | Finds papers related to each top result |
| Three-tier output | Confirmed / Suspicious / Rejected categories |
| PDF reports | Auto-generated PDF per category with full metadata |
| Deduplication | Zero duplicate papers across all sources |

---

## Connection Config

```yaml
connection:
  base_url: "${RPF_BASE_URL}"    # default: http://localhost:8000
  auth:
    type: api_key
    header: X-API-Key
    value: "${RPF_API_KEY}"
  timeout: 300                    # searches take 60-180s — do not reduce
  retry:
    attempts: 2
    backoff: 10
```

---

## Tool Actions

### action: `search`
**Trigger phrases** (OpenClaw should route these to this tool):
- "find papers about..."
- "search research on..."
- "what papers exist about..."
- "recent studies on..."
- "literature on..."
- "academic papers..."
- "find me research about..."
- "papers from [year]..."

**HTTP call:**
```
POST /search
Header: X-API-Key: <key>
Content-Type: application/json
```

**Input:**
```json
{
  "query": "<natural language research question>",
  "year_from": 2020,
  "year_to": 2024,
  "max_results": 10,
  "include_associated": false
}
```

**Output:** See OUTPUT SCHEMA below.

---

### action: `download_pdf`
```
GET /search/pdf/{filename}
Header: X-API-Key: <key>
```
Returns `application/pdf`.

---

### action: `health`
```
GET /health
```
No auth required. Returns model info and source list.

---

## Output Schema

```json
{
  "query": "string",
  "generated_terms": ["list of AI-generated search terms"],
  "papers": [
    {
      "id": "string",
      "title": "string",
      "authors": ["list"],
      "abstract": "string",
      "year": 2024,
      "doi": "string | null",
      "url": "string | null",
      "pdf_url": "string | null",
      "source": "arXiv | Semantic Scholar | ...",
      "citation_count": 42,
      "relevance_score": 87.5,
      "relevance_reasoning": "One-sentence LLM explanation",
      "associated_papers": []
    }
  ],
  "total_found": 28,
  "total_suspicious": 15,
  "total_rejected": 44,
  "pdf_reports": {
    "confirmed":  "confirmed_<slug>_<timestamp>.pdf",
    "suspicious": "suspicious_<slug>_<timestamp>.pdf",
    "rejected":   "rejected_<slug>_<timestamp>.pdf"
  }
}
```

**Score interpretation:**
- `relevance_score >= 70` → Confirmed (high relevance — papers array contains these)
- `relevance_score 40-69` → Suspicious (possible relevance — in suspicious PDF)
- `relevance_score < 40` → Rejected (not relevant — in rejected PDF)

---

## OpenClaw Response Template

When Research Paper Finder returns results, OpenClaw should format responses like:

```
Found {total_found} confirmed papers on "{query}".

Top results:
{for each paper in papers[:3]}
  {rank}. [{relevance_score}/100] {title} ({year}) — {source}
     {relevance_reasoning}
     {url or pdf_url}

📄 PDF Reports available:
  • Confirmed papers: /search/pdf/{pdf_reports.confirmed}
  • Suspicious papers: /search/pdf/{pdf_reports.suspicious}
  • Rejected papers: /search/pdf/{pdf_reports.rejected}
```

---

## Environment Variables (add to OpenClaw .env)

```bash
RPF_API_KEY=rpf_your_key_here
RPF_BASE_URL=http://localhost:8000
```

---

## Rate Limits & Timing

- Searches take **60–180 seconds** (LLM scoring 20-100+ papers at 60 RPM total)
- Results are **cached** — identical queries return instantly
- Maximum 50 papers per request
- Do NOT retry within 30s — the search is likely still running
