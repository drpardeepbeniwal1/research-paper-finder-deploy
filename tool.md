# Research Paper Finder — OpenClaw Tool Definition

> Drop this file into your OpenClaw agent's tool registry.

## Tool: `research_paper_finder`

**Description**: Deep-searches academic databases (arXiv, Semantic Scholar, OpenAlex) using AI-powered query expansion and LLM relevance scoring. Returns structured paper metadata with relevance scores, generates PDF summary reports for top results.

---

## Endpoint

```
POST http://localhost:8000/search
Header: X-API-Key: <your_rpf_key>
```

## Input Schema

```json
{
  "query": "string (3–500 chars) — natural language research question",
  "year_from": "integer | null — filter papers published from this year",
  "year_to":   "integer | null — filter papers published to this year",
  "max_results": "integer 1–50, default 10",
  "include_associated": "boolean — if true, returns 3 associated papers per top result"
}
```

## Output Schema

```json
{
  "query": "original query string",
  "generated_terms": ["array of 7 AI-generated search terms used"],
  "papers": [
    {
      "id": "source:id string",
      "title": "string",
      "authors": ["list of author names"],
      "abstract": "string",
      "year": "integer | null",
      "doi": "string | null",
      "url": "string | null",
      "pdf_url": "string | null — direct PDF link if available",
      "source": "arXiv | Semantic Scholar | OpenAlex",
      "relevance_score": "float 0–100 (LLM-assigned)",
      "relevance_reasoning": "string — one-sentence LLM explanation",
      "associated_papers": ["array of Paper objects (only if include_associated=true)"]
    }
  ],
  "total_found": "integer — total papers above relevance threshold",
  "top_pdfs": ["list of filename strings — download via /search/pdf/{filename}"]
}
```

## PDF Download

```
GET /search/pdf/{filename}
Header: X-API-Key: <your_rpf_key>
```

Returns `application/pdf`. Each PDF contains: title, authors, year, source, DOI, URL, abstract, LLM relevance score and reasoning.

---

## CLI Usage (OpenClaw Agent)

```bash
# Configure once
rpf config set-url http://localhost:8000
rpf config set-key rpf_your_key_here

# Basic search
rpf search "quantum computing error correction"

# With year filter and associated papers
rpf search "CRISPR base editing" --year-from 2021 --year-to 2024 --associated

# Machine-readable JSON output (for agent parsing)
rpf --json-output search "diffusion models image generation" -n 20

# Download top 3 summary PDFs
rpf search "attention mechanisms" --download-pdfs

# Save results to file
rpf search "federated learning privacy" --save results.json

# Check backend health
rpf status
```

## Environment Variables (OpenClaw integration)

```bash
export RPF_API_KEY=rpf_your_key_here
export RPF_BASE_URL=http://localhost:8000

# Then: rpf search "your query" (no --key needed)
```

---

## OpenClaw Agent Tool Config (YAML example)

```yaml
tools:
  - name: research_paper_finder
    type: http
    base_url: "${RPF_BASE_URL}"
    auth:
      type: header
      header: X-API-Key
      value: "${RPF_API_KEY}"
    endpoints:
      search:
        method: POST
        path: /search
        timeout: 300
      download_pdf:
        method: GET
        path: /search/pdf/{filename}
      health:
        method: GET
        path: /health
```

---

## Behavior Notes for Agent

- **Rate limit**: Internally rate-limited to 20 RPM against NVIDIA NIM. Searches with `include_associated=true` take longer (additional LLM calls). Expect 60–120s for large queries.
- **Caching**: Identical queries are cached in SQLite. Repeat queries return instantly.
- **Relevance threshold**: Papers below score 40 are filtered out. If 0 results return, broaden the query.
- **Year strict**: Year filters are enforced at the source level, not post-filter. Results are guaranteed within range.
- **Score meaning**: 70+ = directly relevant. 50–69 = related. Below 50 = tangential (still included if above 40).

---

## Auth Key Management

```bash
# Create a named key (no auth needed for creation)
rpf keys create openclaw-agent

# List all keys
rpf keys list
```
