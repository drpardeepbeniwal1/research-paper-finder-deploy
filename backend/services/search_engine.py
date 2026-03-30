"""
Search pipeline v2 — resource-efficient, domain-aware, zero-duplicate.

Efficiency optimizations:
  1. Domain-aware source selection (skip PubMed for CS queries, etc.)
  2. Pre-filter before LLM scoring (saves 30-50% of LLM calls)
  3. Deduplication before scoring
  4. Paper score caching (never re-score same paper+query)
  5. Parallel source fetch with bounded concurrency
"""
import asyncio, hashlib, json
from models.schemas import Paper, SearchResult, PDFReports
from services.nvidia_llm import (
    generate_search_terms, batch_score_papers,
    get_associated_queries, build_query_intent,
)
from services.deduplicator import deduplicate
from services.pre_filter import apply_pre_filter
from services.pdf_generator import generate_tiered_pdfs
from services.pdf_downloader import download_all_papers
from services.sources import (
    arxiv_source, semantic_scholar, openalex,
    google_scholar, pubmed, core_api, crossref,
    europe_pmc, base_search,
)
from db import get_cached_search, cache_search
from config import get_settings

settings = get_settings()

# ── Domain-aware source routing ──────────────────────────────────────────────
# (module, uses_arxiv_terms, uses_pubmed_terms)
_CS_SOURCES = [
    (arxiv_source,      True,  False),
    (semantic_scholar,  False, False),
    (openalex,          False, False),
    (google_scholar,    False, False),
    (crossref,          False, False),
    (core_api,          False, False),
    (base_search,       False, False),
]
_BIO_MED_SOURCES = [
    (pubmed,            False, True),
    (europe_pmc,        False, True),
    (semantic_scholar,  False, False),
    (openalex,          False, False),
    (crossref,          False, False),
    (google_scholar,    False, False),
    (core_api,          False, False),
]
_ALL_SOURCES = [
    (arxiv_source,      True,  False),
    (semantic_scholar,  False, False),
    (openalex,          False, False),
    (google_scholar,    False, False),
    (pubmed,            False, True),
    (core_api,          False, False),
    (crossref,          False, False),
    (europe_pmc,        False, True),
    (base_search,       False, False),
]

_DOMAIN_SOURCE_MAP = {
    "CS/AI": _CS_SOURCES,
    "Physics": _CS_SOURCES,
    "Mathematics": _CS_SOURCES,
    "Engineering": _CS_SOURCES,
    "Medicine/Clinical": _BIO_MED_SOURCES,
    "Biology": _BIO_MED_SOURCES,
    "Chemistry": _BIO_MED_SOURCES,
}

def _get_sources(domain: str):
    return _DOMAIN_SOURCE_MAP.get(domain, _ALL_SOURCES)

def _cache_key(query: str, yf, yt, assoc: bool) -> str:
    raw = json.dumps({"q": query, "yf": yf, "yt": yt, "a": assoc}, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()

_SOURCE_TIMEOUT = 25  # seconds per individual source request

async def _fetch_source(module, term: str, max_r: int, yf, yt) -> list[dict]:
    try:
        return await asyncio.wait_for(
            module.search(term, max_r, yf, yt),
            timeout=_SOURCE_TIMEOUT,
        )
    except asyncio.TimeoutError:
        return []
    except Exception:
        return []

async def _parallel_fetch(
    generated: dict,
    domain: str,
    max_per_source: int,
    year_from, year_to,
    on_progress=None,
) -> list[dict]:
    sources = _get_sources(domain)
    general = generated.get("terms_general", [])
    arxiv = generated.get("terms_arxiv", []) or general[:2]
    pubmed_terms = generated.get("terms_pubmed", []) or general[:2]

    sem = asyncio.Semaphore(4)
    source_counts: dict[str, int] = {}
    source_status: dict[str, str] = {}
    lock = asyncio.Lock()

    async def bounded(src_name: str, src, term: str):
        async with sem:
            try:
                result = await asyncio.wait_for(
                    src.search(term, max_per_source, year_from, year_to),
                    timeout=_SOURCE_TIMEOUT,
                )
                count = len(result) if isinstance(result, list) else 0
                async with lock:
                    source_counts[src_name] = source_counts.get(src_name, 0) + count
                    source_status[src_name] = "done"
                if on_progress:
                    done = sum(1 for s in source_status.values() if s in ("done", "timeout", "error"))
                    total_tasks = len(task_meta)
                    on_progress(
                        f"[{done}/{total_tasks}] {src_name}: {count} papers found (term: {term[:40]})",
                        25 + int(done / max(total_tasks, 1) * 20),
                    )
                return result if isinstance(result, list) else []
            except asyncio.TimeoutError:
                async with lock:
                    source_status[src_name] = "timeout"
                if on_progress:
                    done = sum(1 for s in source_status.values() if s in ("done", "timeout", "error"))
                    total_tasks = len(task_meta)
                    on_progress(
                        f"[{done}/{total_tasks}] {src_name}: timeout after {_SOURCE_TIMEOUT}s (skipped)",
                        25 + int(done / max(total_tasks, 1) * 20),
                    )
                return []
            except Exception as e:
                async with lock:
                    source_status[src_name] = "error"
                if on_progress:
                    done = sum(1 for s in source_status.values() if s in ("done", "timeout", "error"))
                    total_tasks = len(task_meta)
                    on_progress(
                        f"[{done}/{total_tasks}] {src_name}: error ({type(e).__name__})",
                        25 + int(done / max(total_tasks, 1) * 20),
                    )
                return []

    task_meta = []
    for src, uses_arxiv, uses_pubmed in sources:
        terms = arxiv if uses_arxiv else (pubmed_terms if uses_pubmed else general)
        src_name = src.__name__.split(".")[-1] if hasattr(src, "__name__") else str(src)
        for term in terms:
            task_meta.append((src_name, src, term))

    tasks = [bounded(src_name, src, term) for src_name, src, term in task_meta]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    papers = []
    for r in results:
        if isinstance(r, list):
            papers.extend(r)
    return papers

async def run_search(
    query: str,
    year_from: int = None,
    year_to: int = None,
    max_results: int = 10,
    include_associated: bool = False,
    on_progress=None,
) -> SearchResult:
    def _p(msg: str, pct: int):
        if on_progress:
            on_progress(msg, pct)

    # Cache check — return instantly if cached
    ck = _cache_key(query, year_from, year_to, include_associated)
    cached = await get_cached_search(ck)
    if cached:
        _p("Loaded from cache!", 100)
        return SearchResult(**cached)

    # Step 1: LLM generates domain-aware multi-source search terms (1 LLM call)
    _p("Asking NVIDIA LLM to generate domain-aware search terms...", 8)
    generated = await generate_search_terms(query)
    domain = generated.get("domain", "general")
    exclude_terms = generated.get("exclude_terms", [])
    all_terms = (
        generated.get("terms_general", []) +
        generated.get("terms_arxiv", []) +
        generated.get("terms_pubmed", [])
    )
    _p(f"Domain detected: {domain} — generated {len(all_terms)} search terms", 15)

    # Step 2: Build compact query intent for scoring (0 LLM calls — uses generated dict)
    _p("Building query intent for relevance scoring...", 20)
    intent = await build_query_intent(query, generated)

    # Step 3: Parallel fetch from domain-appropriate sources
    sources = _get_sources(domain)
    source_names = list({s[0].__name__.split(".")[-1] for s in sources})
    _p(f"Fetching papers from {len(sources)} sources: {', '.join(source_names[:4])}...", 25)
    raw_papers = await _parallel_fetch(
        generated, domain, settings.max_results_per_source, year_from, year_to,
        on_progress=on_progress,
    )
    _p(f"Fetched {len(raw_papers)} raw papers from all sources", 50)

    # Step 4: Deduplicate (DOI > arXiv ID > title fuzzy) — zero duplicates
    _p("Deduplicating papers (DOI → arXiv ID → title fuzzy match)...", 55)
    unique_papers = deduplicate(raw_papers)
    _p(f"{len(unique_papers)} unique papers after deduplication (removed {len(raw_papers) - len(unique_papers)} duplicates)", 58)

    # Step 5: Pre-filter — keyword-based, no LLM, eliminates obvious noise
    _p("Pre-filtering papers by keyword relevance (no LLM)...", 60)
    to_score, pre_rejected = apply_pre_filter(unique_papers, all_terms, exclude_terms)
    _p(f"{len(to_score)} papers passed pre-filter, {len(pre_rejected)} filtered out — sending to LLM scoring...", 65)

    # Step 6: LLM scores only the papers that passed pre-filter
    _p(f"NVIDIA LLM scoring {len(to_score)} papers for relevance (0-100)...", 70)
    obligatory = generated.get("obligatory_concepts", [])
    scored = await batch_score_papers(query, intent, to_score, obligatory, on_progress=on_progress)
    _p(f"Scoring complete — categorizing results...", 88)

    # Step 7: Merge and categorize all papers
    all_scored = scored + pre_rejected  # pre_rejected have score=5

    confirmed = sorted(
        [p for p in all_scored if p.get("relevance_score", 0) >= settings.confirmed_threshold],
        key=lambda p: p["relevance_score"], reverse=True,
    )
    suspicious = sorted(
        [p for p in all_scored if settings.suspicious_threshold <= p.get("relevance_score", 0) < settings.confirmed_threshold],
        key=lambda p: p["relevance_score"], reverse=True,
    )
    rejected = sorted(
        [p for p in all_scored if p.get("relevance_score", 0) < settings.suspicious_threshold],
        key=lambda p: p["relevance_score"], reverse=True,
    )

    # Step 8: Optional associated papers for top-3 confirmed
    if include_associated:
        _p(f"Finding associated papers for top {min(3, len(confirmed))} confirmed papers...", 90)
        for i, paper in enumerate(confirmed[:3]):
            _p(f"Fetching associated papers for: {paper.get('title', '')[:60]}...", 91 + i)
            assoc_queries = await get_associated_queries(
                query, paper.get("title", ""), paper.get("abstract", "")
            )
            assoc_raw: list[dict] = []
            mini_gen: dict[str, list] = {"terms_general": assoc_queries, "terms_arxiv": assoc_queries, "terms_pubmed": []}
            partial = await _parallel_fetch(mini_gen, domain, 5, year_from, year_to, on_progress=on_progress)
            assoc_raw.extend(partial)
            assoc_unique = deduplicate(assoc_raw)
            assoc_to_score, assoc_rejected = apply_pre_filter(assoc_unique, assoc_queries, exclude_terms)
            assoc_scored = await batch_score_papers(query, intent, assoc_to_score)
            all_assoc = (assoc_scored + assoc_rejected)
            all_assoc.sort(key=lambda p: p.get("relevance_score", 0), reverse=True)
            paper["associated_papers"] = all_assoc[:4]

    # Step 9: Generate 3 tiered summary PDFs
    _p(f"Generating PDF reports ({len(confirmed)} confirmed, {len(suspicious)} suspicious, {len(rejected)} rejected)...", 94)
    pdf_reports = await generate_tiered_pdfs(query, generated, confirmed, suspicious, rejected)

    # Step 10: Download actual paper PDFs into accepted/maybe/rejected folders
    _p("Downloading paper PDFs in background...", 97)
    downloaded = await download_all_papers(all_scored)

    # Build response (papers array = confirmed only, up to max_results)
    valid_fields = set(Paper.model_fields.keys())
    paper_objs = [
        Paper(**{k: v for k, v in p.items() if k in valid_fields})
        for p in confirmed[:max_results]
    ]

    result = SearchResult(
        query=query,
        generated_terms=all_terms[:12],
        papers=paper_objs,
        total_found=len(confirmed),
        total_suspicious=len(suspicious),
        total_rejected=len(rejected),
        pdf_reports=pdf_reports,
        downloaded_papers=downloaded,
    )

    await cache_search(ck, result.model_dump())
    return result
