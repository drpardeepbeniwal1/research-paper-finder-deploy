import httpx
from services.anti_bot import api_headers
from services.sources.source_limiter import get_limiter

BASE = "https://api.openalex.org/works"
_lim = get_limiter("openalex")

async def search(term: str, max_results: int = 25, year_from: int = None, year_to: int = None) -> list[dict]:
    params: dict = {"search": term, "per-page": min(max_results, 50),
                    "sort": "relevance_score:desc",
                    "select": "id,title,authorships,abstract_inverted_index,publication_year,doi,primary_location,open_access,cited_by_count",
                    "mailto": "research@tool.local"}
    if year_from or year_to:
        params["filter"] = f"publication_year:{year_from or 1900}-{year_to or 2100}"

    for attempt in range(3):
        await _lim.acquire()
        try:
            async with httpx.AsyncClient(timeout=20, headers=api_headers("OpenAlex")) as client:
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
    for item in data.get("results", []):
        inv = item.get("abstract_inverted_index") or {}
        abstract = ""
        if inv:
            word_pos = [(pos, w) for w, positions in inv.items() for pos in positions]
            word_pos.sort()
            abstract = " ".join(w for _, w in word_pos)
        authors = [a.get("author",{}).get("display_name","") for a in (item.get("authorships") or [])]
        doi = item.get("doi","") or None
        pdf_url = (item.get("open_access") or {}).get("oa_url")
        oa_id = item.get("id","").replace("https://openalex.org/","")
        papers.append({
            "id": f"oa:{oa_id}", "title": item.get("title") or "",
            "authors": authors, "abstract": abstract,
            "year": item.get("publication_year"), "doi": doi,
            "url": item.get("id"), "pdf_url": pdf_url,
            "source": "OpenAlex", "citation_count": item.get("cited_by_count") or 0,
        })
    return papers
