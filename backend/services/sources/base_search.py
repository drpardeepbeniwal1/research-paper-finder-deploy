import httpx
from services.anti_bot import api_headers
from services.sources.source_limiter import get_limiter

BASE_URL = "https://api.base-search.net/cgi-bin/BaseHttpSearchInterface.fcgi"
_lim = get_limiter("base")

async def search(term: str, max_results: int = 25, year_from: int = None, year_to: int = None) -> list[dict]:
    query = term
    if year_from or year_to:
        query += f" dcyear:[{year_from or 1900} TO {year_to or 2100}]"

    params = {"func": "PerformSearch", "query": query, "hits": min(max_results, 100), "format": "json", "boost": "oa"}

    for attempt in range(3):
        await _lim.acquire()
        try:
            async with httpx.AsyncClient(timeout=20, headers=api_headers("BASE")) as c:
                r = await c.get(BASE_URL, params=params)
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

    def first(v):
        return (v[0] if isinstance(v, list) and v else v) or ""

    papers = []
    for item in data.get("response", {}).get("docs", []):
        year = None
        yr = item.get("dcyear")
        if yr:
            try:
                year = int(str(first(yr))[:4])
                if not (1800 < year < 2100):
                    year = None
            except Exception:
                year = None
        doi = first(item.get("dcdoi","")) or None
        url = first(item.get("dclink","") or item.get("dcidentifier",""))
        authors_raw = item.get("dccreator") or []
        authors = authors_raw if isinstance(authors_raw, list) else [authors_raw]
        papers.append({
            "id": f"base:{len(papers)}_{year}",
            "title": first(item.get("dctitle","")),
            "authors": [a for a in authors if a],
            "abstract": first(item.get("dcdescription","")),
            "year": year, "doi": doi, "url": url or None,
            "pdf_url": url if url and ".pdf" in url.lower() else None,
            "source": "BASE",
        })
    return papers
