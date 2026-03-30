import httpx
from services.anti_bot import api_headers
from services.sources.source_limiter import get_limiter

BASE = "https://api.semanticscholar.org/graph/v1/paper/search"
FIELDS = "paperId,title,authors,abstract,year,externalIds,openAccessPdf,url,venue,citationCount"
_lim = get_limiter("semantic_scholar")

async def search(term: str, max_results: int = 25, year_from: int = None, year_to: int = None) -> list[dict]:
    params: dict = {"query": term, "fields": FIELDS, "limit": min(max_results, 100)}
    if year_from or year_to:
        params["year"] = f"{year_from or 1900}-{year_to or 2100}"

    for attempt in range(3):
        await _lim.acquire()
        try:
            async with httpx.AsyncClient(timeout=20, headers=api_headers("SemanticScholar")) as client:
                r = await client.get(BASE, params=params)
            if r.status_code == 429:
                await _lim.on_429(int(r.headers.get("Retry-After", 60)))
                continue
            if r.status_code in (200, 201):
                _lim.on_success()
                data = r.json()
                break
            return []
        except Exception:
            if attempt == 2:
                return []
    else:
        return []

    papers = []
    for item in data.get("data", []):
        doi = (item.get("externalIds") or {}).get("DOI")
        pdf_url = (item.get("openAccessPdf") or {}).get("url")
        papers.append({
            "id": f"s2:{item.get('paperId','')}",
            "title": item.get("title") or "",
            "authors": [a.get("name","") for a in (item.get("authors") or [])],
            "abstract": item.get("abstract") or "",
            "year": item.get("year"),
            "doi": doi, "url": item.get("url") or f"https://www.semanticscholar.org/paper/{item.get('paperId','')}" ,
            "pdf_url": pdf_url, "source": "Semantic Scholar",
            "citation_count": item.get("citationCount") or 0,
        })
    return papers
