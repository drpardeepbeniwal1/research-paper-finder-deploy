import httpx
from services.anti_bot import api_headers
from services.sources.source_limiter import get_limiter

BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
_lim = get_limiter("europe_pmc")

async def search(term: str, max_results: int = 25, year_from: int = None, year_to: int = None) -> list[dict]:
    query = term
    if year_from or year_to:
        query += f" AND (PUB_YEAR:[{year_from or 1900} TO {year_to or 2100}])"

    params = {"query": query, "resultType": "core", "pageSize": min(max_results, 100), "format": "json"}

    for attempt in range(3):
        await _lim.acquire()
        try:
            async with httpx.AsyncClient(timeout=20, headers=api_headers("EuropePMC")) as c:
                r = await c.get(BASE, params=params)
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
    for item in data.get("resultList", {}).get("result", []):
        year = None
        yr = item.get("pubYear")
        if yr:
            try:
                year = int(yr)
            except Exception:
                pass
        pmid = item.get("pmid","")
        pmcid = item.get("pmcid","")
        doi = item.get("doi","") or None
        authors = [a.strip() for a in (item.get("authorString") or "").split(",") if a.strip()]
        papers.append({
            "id": f"epmc:{pmid or pmcid}", "title": item.get("title") or "",
            "authors": authors, "abstract": item.get("abstractText") or "",
            "year": year, "doi": doi,
            "url": f"https://europepmc.org/article/med/{pmid}" if pmid else None,
            "pdf_url": f"https://europepmc.org/articles/{pmcid}/pdf/render" if pmcid else None,
            "source": "Europe PMC",
        })
    return papers
