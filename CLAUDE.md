# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Research Paper Finder v2 — AI-powered deep academic paper discovery. Uses 3 NVIDIA NIM keys in rotation (`nvidia/llama-3.1-nemotron-70b-instruct`, 60 RPM total) to analyze and score papers from 9 free sources. Produces 3 tiered PDF reports (Confirmed/Suspicious/Rejected). Designed for Hostinger VPS deployment with OpenClaw agent integration.

## Commands

### Setup (first time)
```bash
./scripts/setup.sh
# Then edit .env — set NVIDIA_KEY_1, NVIDIA_KEY_2, NVIDIA_KEY_3
```

### Run (tmux)
```bash
./scripts/start.sh                               # launches in tmux "research-paper-finder"
tmux attach -t research-paper-finder             # attach
tmux kill-session -t research-paper-finder       # stop
```

### Backend
```bash
cd backend && source ../.venv/bin/activate && python main.py
# API: http://localhost:8000 · Docs: http://localhost:8000/docs
```

### Frontend
```bash
cd frontend && npm run dev          # dev server http://localhost:5173
npm run build                       # production → dist/
```

### CLI
```bash
pip install -e cli/
rpf status                          # health check (shows keys + RPM)
rpf search "transformer attention" --associated --download-pdfs
rpf search "CRISPR 2023" --year-from 2023 --year-to 2024
rpf --json-output search "federated learning"   # machine-readable
rpf openclaw approve A3F9           # approve an OpenClaw pairing
rpf openclaw pending                # list pending pairings
rpf keys create openclaw-main       # create a key for OpenClaw
```

### Hostinger production deploy
```bash
sudo bash scripts/deploy_hostinger.sh your-domain.com
# Sets up nginx + SSL + systemd service
```

## Architecture

```
User Query
    │
    ▼
FastAPI (backend/main.py)
    │
    ├── Auth: X-API-Key → SQLite hash check
    │
    └── POST /search → services/search_engine.py
            │
            ├── 1. nvidia_llm.generate_search_terms()
            │      → KeyRotationScheduler picks least-loaded key (of 3)
            │      → Returns: {terms_general[6], terms_arxiv[4], terms_pubmed[4], domain, exclude_terms}
            │
            ├── 2. _fetch_all_sources() — asyncio.Semaphore(5) concurrent
            │      ├── arxiv_source      (terms_arxiv)
            │      ├── semantic_scholar  (terms_general)
            │      ├── openalex          (terms_general)
            │      ├── google_scholar    (terms_general — with anti-bot delays + Tor fallback)
            │      ├── pubmed            (terms_pubmed)
            │      ├── core_api          (terms_general)
            │      ├── crossref          (terms_general)
            │      ├── europe_pmc        (terms_pubmed)
            │      └── base_search       (terms_general)
            │
            ├── 3. deduplicator.deduplicate()
            │      Priority: DOI exact → arXiv ID exact → title fuzzy >92% → title+year fuzzy >82%
            │
            ├── 4. nvidia_llm.batch_score_papers()
            │      Score 0-100 per paper · Cached in SQLite (never re-score same paper+query)
            │
            ├── 5. Three-tier sort:
            │      confirmed  (≥70) → papers[] in response
            │      suspicious (40-69) → suspicious PDF only
            │      rejected   (<40)  → rejected PDF only
            │
            ├── 6. [Optional] Associated papers per top-3 confirmed
            │
            └── 7. pdf_generator.generate_tiered_pdfs()
                   → confirmed_<slug>_<ts>.pdf
                   → suspicious_<slug>_<ts>.pdf
                   → rejected_<slug>_<ts>.pdf
```

**OpenClaw Auth Flow**: `POST /openclaw/pair` → `rpf openclaw approve <code>` → `POST /openclaw/attach` → returns API key.

**Rate limiting**: `KeyRotationScheduler` in `nvidia_llm.py` — picks key with most available slots in 60s window. Never exceeds 20 RPM per key. Total: 3 keys × 20 = 60 RPM.

**Google Scholar**: Uses `scholarly` library with anti-bot delays (3-8s per request). Falls back gracefully if blocked. Configure Tor via `TOR_PROXY=socks5://localhost:9050` in `.env`.

**Deduplication**: `services/deduplicator.py` — stateful Deduplicator class, zero duplicates guaranteed across all 9 sources.

## Key Config (`.env`)

| Variable | Description |
|---|---|
| `NVIDIA_KEY_1/2/3` | 3 NVIDIA NIM keys (decode agri / prdeepbeni / agrisearcher accounts) |
| `NVIDIA_MODEL` | `nvidia/llama-3.1-nemotron-70b-instruct` — do not change unless testing |
| `NVIDIA_RPM_PER_KEY` | 20 (free tier limit per key) |
| `CONFIRMED_THRESHOLD` | 70 (score cutoff for Confirmed vs Suspicious) |
| `SUSPICIOUS_THRESHOLD` | 40 (score cutoff for Suspicious vs Rejected) |
| `TOR_PROXY` | Optional: `socks5://localhost:9050` for Scholar stealth |
| `CORE_API_KEY` | Optional: free key from core.ac.uk for higher limits |
| `NCBI_API_KEY` | Optional: free key from ncbi.nlm.nih.gov for 10/s PubMed |

## Key Files

| File | Purpose |
|---|---|
| `backend/context/research_context.md` | LLM master prompt — tune to change ALL search/scoring behavior |
| `backend/services/nvidia_llm.py` | 3-key rotation scheduler + all LLM calls |
| `backend/services/deduplicator.py` | Zero-duplicate engine |
| `backend/services/anti_bot.py` | Human-like headers, delays, rotating UAs |
| `backend/services/search_engine.py` | Full pipeline orchestrator |
| `backend/services/pdf_generator.py` | 3-tier PDF generator |
| `openclaw/AGENT_CARD.md` | OpenClaw tool definition |
| `openclaw/CONVERSATION_GUIDE.md` | OpenClaw conversation routing |
| `openclaw/auth_router.py` | Pairing handshake endpoint |
| `tool.md` | API reference for developers |

## Adding a New Paper Source

1. Create `backend/services/sources/new_source.py` with `async def search(term, max_results, year_from, year_to) -> list[dict]`
2. Each dict: `id`, `title`, `authors`, `abstract`, `year`, `doi`, `url`, `pdf_url`, `source`
3. Use `api_headers()` from `services/anti_bot.py` for all HTTP requests
4. Add to `_SOURCES` list in `search_engine.py` with `(module, uses_arxiv, uses_pubmed)` tuple

## Hostinger Deployment Notes

- Use `scripts/deploy_hostinger.sh <domain>` for full setup (nginx + SSL + systemd)
- Backend runs as systemd service (`rpf-backend`) — auto-restarts on crash
- 1 uvicorn worker only (rate limiter is shared in-process state)
- Frontend served as static files via nginx (Vite build)
- Update `VITE_API_BASE_URL=https://your-domain.com` in `.env` before `npm run build`
