import httpx
from services.anti_bot import api_headers
from services.sources.source_limiter import get_limiter

BASE = "https://api.crossref.org/works"
_lim = get_limiter("crossref")
_VALID_TYPES = {"journal-article","proceedings-article","book-chapter","preprint","posted-content"}

async def search(term: str, max_results: int = 25, year_from: int = None, year_to: int = None) -> list[dict]:
    params: dict = {"query": term, "rows": min(max_results, 100),
                    "select": "DOI,title,author,abstract,published,container-title,URL,type",
                    "sort": "relevance", "mailto": "research@tool.local"}
    filters = []
    if year_from:
        filters.append(f"from-pub-date:{year_from}")
    if year_to:
        filters.append(f"until-pub-date:{year_to}")
    if filters:
        params["filter"] = ",".join(filters)

    for attempt in range(3):
        await _lim.acquire()
        try:
            async with httpx.AsyncClient(timeout=20, headers=api_headers("CrossRef")) as client:
                r = await client.get(BASE, params=params)
            if r.status_code == 429:
                await _lim.on_429(int(r.headers.get("Retry-After", 60)))
                continue
            r.raise_for_status()
            _lim.on_success()
            data = r.json()
            break
        except Exception:
            if attempt == 2:
                return []
    else:
        return []

    papers = []
    for item in data.get("message", {}).get("items", []):
        if item.get("type") not in _VALID_TYPES:
            continue
        titles = item.get("title") or []
        title = titles[0] if titles else ""
        authors = [f"{a.get('given','')} {a.get('family','')}".strip()
                   for a in (item.get("author") or []) if a.get("family")]
        year = None
        pub = item.get("published") or item.get("published-print") or {}
        dp = pub.get("date-parts", [[]])[0] if pub else []
        if dp:
            year = dp[0]
        doi = item.get("DOI","")
        abstract = (item.get("abstract") or "").replace("<jats:p>","").replace("</jats:p>","").strip()
        papers.append({
            "id": f"crossref:{doi}", "title": title, "authors": authors,
            "abstract": abstract, "year": year, "doi": doi,
            "url": item.get("URL") or (f"https://doi.org/{doi}" if doi else None),
            "pdf_url": None, "source": "CrossRef",
        })
    return papers
