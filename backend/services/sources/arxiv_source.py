import httpx, feedparser
from datetime import datetime
from services.anti_bot import api_headers
from services.sources.source_limiter import get_limiter

BASE = "http://export.arxiv.org/api/query"
_lim = get_limiter("arxiv")

async def search(term: str, max_results: int = 25, year_from: int = None, year_to: int = None) -> list[dict]:
    search_query = term if term.startswith("cat:") else f"all:{term}"
    params = {"search_query": search_query, "start": 0,
               "max_results": min(max_results, 200), "sortBy": "relevance", "sortOrder": "descending"}

    for attempt in range(3):
        await _lim.acquire()
        try:
            async with httpx.AsyncClient(timeout=25, headers=api_headers("arXiv")) as client:
                r = await client.get(BASE, params=params)
            if r.status_code == 429:
                await _lim.on_429(int(r.headers.get("Retry-After", 60)))
                continue
            r.raise_for_status()
            _lim.on_success()
            break
        except Exception:
            if attempt == 2:
                return []
            continue
    else:
        return []

    feed = feedparser.parse(r.text)
    papers = []
    for entry in feed.entries:
        year = None
        pub = entry.get("published", "")
        if pub:
            try:
                year = datetime.fromisoformat(pub[:10]).year
            except Exception:
                pass
        if year_from and year and year < year_from:
            continue
        if year_to and year and year > year_to:
            continue
        arxiv_id = entry.get("id", "").split("/abs/")[-1].split("v")[0]
        papers.append({
            "id": f"arxiv:{arxiv_id}",
            "title": (entry.get("title") or "").replace("\n", " ").strip(),
            "authors": [a.get("name", "") for a in entry.get("authors", [])],
            "abstract": (entry.get("summary") or "").replace("\n", " ").strip(),
            "year": year,
            "doi": None, "url": entry.get("id", ""),
            "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else None,
            "source": "arXiv",
            "categories": [t.get("term", "") for t in entry.get("tags", [])],
        })
    return papers
