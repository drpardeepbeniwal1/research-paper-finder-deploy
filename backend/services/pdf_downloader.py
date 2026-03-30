"""
Actual paper PDF downloader.
Resolution chain per paper:
  1. Direct pdf_url (arXiv, CORE, Europe PMC, Semantic Scholar open access)
  2. arXiv ID pattern extraction
  3. Unpaywall DOI resolution (legal free PDFs)
  4. Sci-Hub (last resort, if SCIHUB_ENABLED=true)

Files saved as: {YYYY}_{sanitized_title}.pdf
  → alphabetical descending = newest first (2026 before 2025 before 2024...)

Folders:
  data/papers/accepted/   score >= CONFIRMED_THRESHOLD
  data/papers/maybe/      score >= SUSPICIOUS_THRESHOLD
  data/papers/rejected/   score < SUSPICIOUS_THRESHOLD
"""
import asyncio, re, os, logging
import httpx
from services.anti_bot import stealth_headers, human_delay
from services.sources.source_limiter import get_limiter
from config import get_settings

log = logging.getLogger("rpf.downloader")
settings = get_settings()

PAPERS_DIR = "./data/papers"
_up_lim = get_limiter("unpaywall")

def _score_to_tier(score: float) -> str:
    if score >= settings.confirmed_threshold:
        return "accepted"
    if score >= settings.suspicious_threshold:
        return "maybe"
    return "rejected"

def _safe_filename(title: str, year) -> str:
    year_prefix = str(year) if year else "0000"
    title_clean = re.sub(r"[^\w\s-]", "", (title or "untitled"))
    title_clean = re.sub(r"\s+", "_", title_clean.strip())[:80]
    return f"{year_prefix}_{title_clean}.pdf"

def _extract_arxiv_pdf(paper: dict) -> str | None:
    url = paper.get("url") or ""
    m = re.search(r"arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]+)", url)
    if m:
        return f"https://arxiv.org/pdf/{m.group(1)}"
    pid = paper.get("id","")
    if pid.startswith("arxiv:"):
        return f"https://arxiv.org/pdf/{pid.split(':')[1].split('v')[0]}"
    return None

async def _resolve_unpaywall(doi: str) -> str | None:
    doi_clean = re.sub(r"^https?://doi\.org/", "", (doi or "").strip())
    if not doi_clean:
        return None
    await _up_lim.acquire()
    try:
        async with httpx.AsyncClient(timeout=12) as c:
            r = await c.get(f"https://api.unpaywall.org/v2/{doi_clean}?email=research@tool.local")
        if r.status_code == 429:
            await _up_lim.on_429(60)
            return None
        if r.status_code != 200:
            return None
        data = r.json()
        _up_lim.on_success()
        best = data.get("best_oa_location") or {}
        return best.get("url_for_pdf") or best.get("url")
    except Exception:
        return None

async def _stream_to_disk(url: str, filepath: str) -> bool:
    """Stream download with PDF verification."""
    try:
        async with httpx.AsyncClient(timeout=45, follow_redirects=True,
                                      headers=stealth_headers()) as c:
            async with c.stream("GET", url) as r:
                if r.status_code != 200:
                    return False
                ctype = r.headers.get("content-type","").lower()
                if "pdf" not in ctype and "octet-stream" not in ctype:
                    if not url.lower().split("?")[0].endswith(".pdf"):
                        return False
                size, chunks = 0, []
                async for chunk in r.aiter_bytes(16384):
                    size += len(chunk)
                    if size > settings.max_pdf_bytes:
                        return False
                    chunks.append(chunk)
                if size < 2048:
                    return False
                # PDF magic bytes check
                if not (chunks[0][:4] == b"%PDF"):
                    return False
                with open(filepath, "wb") as f:
                    for c_ in chunks:
                        f.write(c_)
                return True
    except Exception:
        return False

async def download_paper(paper: dict) -> str | None:
    score = paper.get("relevance_score", 0)
    tier = _score_to_tier(score)
    folder = os.path.join(PAPERS_DIR, tier)
    os.makedirs(folder, exist_ok=True)

    filename = _safe_filename(paper.get("title"), paper.get("year"))
    filepath = os.path.join(folder, filename)

    if os.path.exists(filepath) and os.path.getsize(filepath) > 2048:
        return f"papers/{tier}/{filename}"

    # Build candidate PDF URLs in priority order
    candidates: list[str] = []
    if paper.get("pdf_url"):
        candidates.append(paper["pdf_url"])
    arxiv_url = _extract_arxiv_pdf(paper)
    if arxiv_url and arxiv_url not in candidates:
        candidates.append(arxiv_url)

    # Try direct candidates first
    for url in candidates:
        if await _stream_to_disk(url, filepath):
            log.info(f"Downloaded [{tier}]: {filename[:60]}")
            return f"papers/{tier}/{filename}"

    # Unpaywall (DOI-based free PDF finder)
    doi = paper.get("doi")
    if doi:
        resolved = await _resolve_unpaywall(doi)
        if resolved and await _stream_to_disk(resolved, filepath):
            log.info(f"Unpaywall [{tier}]: {filename[:60]}")
            return f"papers/{tier}/{filename}"

    # Sci-Hub — last resort (only if enabled)
    if settings.scihub_enabled and doi:
        from services.sources.scihub import resolve_pdf
        sh_url = await resolve_pdf(doi, settings.tor_proxy)
        if sh_url and await _stream_to_disk(sh_url, filepath):
            log.info(f"Sci-Hub [{tier}]: {filename[:60]}")
            return f"papers/{tier}/{filename}"

    return None

async def download_all_papers(all_papers: list[dict]) -> dict:
    if not settings.download_actual_pdfs:
        return {"accepted": [], "maybe": [], "rejected": []}

    sem = asyncio.Semaphore(settings.pdf_download_concurrency)

    async def bounded(paper: dict):
        async with sem:
            await human_delay(0.5, 2.0)
            path = await download_paper(paper)
            tier = _score_to_tier(paper.get("relevance_score", 0))
            return tier, path

    results = await asyncio.gather(*[bounded(p) for p in all_papers if p.get("title")],
                                   return_exceptions=True)
    tier_paths: dict[str, list[str]] = {"accepted": [], "maybe": [], "rejected": []}
    for res in results:
        if isinstance(res, tuple):
            tier, path = res
            if path:
                tier_paths[tier].append(path)

    total = sum(len(v) for v in tier_paths.values())
    log.info(f"PDF downloads: {total} total | accepted:{len(tier_paths['accepted'])} maybe:{len(tier_paths['maybe'])} rejected:{len(tier_paths['rejected'])}")
    return tier_paths
