# Research Paper Finder — OpenClaw Conversation Guide

> This file teaches OpenClaw how to handle user research requests conversationally.
> Load this as a system-level instruction or skill definition.

---

## System Instruction Block (inject into OpenClaw system prompt)

```
You have access to the Research Paper Finder tool (RPF). This tool performs deep academic
paper searches using AI across 9 databases. It scores every paper for relevance and
produces categorized PDF reports.

When a user asks about research, papers, studies, or academic literature on any topic,
use the RPF search action. Do not try to answer from memory — use the tool.

After receiving results:
1. Present the top 3-5 confirmed papers with their scores and one-line reasoning
2. Mention how many additional papers were found (total_found, total_suspicious)
3. Offer to download PDF reports for full lists
4. If include_associated=true was used, present associated papers grouped by parent paper
```

---

## Intent → Action Mapping

| User says | RPF action | Parameters |
|---|---|---|
| "Find papers on X" | search | query=X |
| "Recent papers on X" | search | query=X, year_from=current_year-2 |
| "Papers from 2020 to 2023 on X" | search | query=X, year_from=2020, year_to=2023 |
| "Find and also show related papers on X" | search | query=X, include_associated=true |
| "Give me 20 papers on X" | search | query=X, max_results=20 |
| "Download the confirmed papers" | download_pdf | pdf_reports.confirmed filename |
| "Is the finder working?" | health | — |

---

## Example Conversations

### Simple research query
```
User: Find me papers on transformer attention for long sequences

OpenClaw: [calls RPF: query="transformer attention for long sequences"]
          [waits ~90 seconds for LLM scoring]

Response:
Found 23 confirmed papers on "transformer attention for long sequences".

Top results:
1. [94/100] Longformer: The Long-Document Transformer (2020) — arXiv
   Directly introduces efficient attention for long sequences using sliding window attention.
   🔗 https://arxiv.org/abs/2004.05150

2. [91/100] BigBird: Transformers for Longer Sequences (2020) — Semantic Scholar
   Proposes sparse attention achieving linear complexity for long-context transformers.
   🔗 https://arxiv.org/abs/2007.14062

3. [88/100] FlashAttention: Fast and Memory-Efficient Exact Attention (2022) — arXiv
   Exact attention with IO-awareness, enabling longer sequences without approximation.
   🔗 https://arxiv.org/abs/2205.14135

Also found 11 suspicious papers (possible relevance) and 31 rejected papers.

📄 PDF Reports:
  • Confirmed (23 papers): download with "download confirmed pdf"
  • Suspicious (11 papers): download with "download suspicious pdf"
```

### With year filter
```
User: Find CRISPR gene editing papers from 2022 to 2024

OpenClaw: [calls RPF: query="CRISPR gene editing", year_from=2022, year_to=2024]

Response: Found 18 confirmed papers on CRISPR from 2022-2024...
```

### With associated papers
```
User: Find papers on federated learning privacy and show me related papers too

OpenClaw: [calls RPF: query="federated learning privacy", include_associated=true]

Response:
Top paper: [92/100] Communication-Efficient Learning of Deep Networks (2017)
  Associated papers found:
  · [88/100] Differentially Private Federated Learning (2021)
  · [85/100] SecureBoost: Privacy-Preserving Gradient Boosting (2019)
  · [79/100] FATE: An Industrial Grade Platform for Collaborative Learning (2021)
```

---

## Error Handling

| Error | OpenClaw response |
|---|---|
| 401 Unauthorized | "API key invalid. Run: rpf keys create openclaw" |
| 422 Validation | Re-check query format, ensure it's 3+ characters |
| 504 Timeout | "Search is taking longer than expected. The results will be cached — retry in 30s." |
| 503 Service | "Research Paper Finder is offline. Start it with: tmux attach -t research-paper-finder" |

---

## OpenClaw YAML Tool Definition

```yaml
# Add to openclaw/tools/research_paper_finder.yaml

name: research_paper_finder
display_name: Research Paper Finder
description: Deep AI-powered academic paper search across 9 databases with LLM relevance scoring
icon: 📄
auth_env: RPF_API_KEY
auth_header: X-API-Key

actions:
  - id: search
    method: POST
    path: /search
    description: Search for academic papers on a topic
    parameters:
      - name: query
        type: string
        required: true
        description: Research topic or question
      - name: year_from
        type: integer
        required: false
      - name: year_to
        type: integer
        required: false
      - name: max_results
        type: integer
        required: false
        default: 10
      - name: include_associated
        type: boolean
        required: false
        default: false

  - id: download_pdf
    method: GET
    path: /search/pdf/{filename}
    description: Download a PDF report

  - id: health
    method: GET
    path: /health
    auth_required: false
    description: Check service status
```
