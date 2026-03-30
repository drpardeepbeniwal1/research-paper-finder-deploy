import httpx
from config import get_settings
from services.anti_bot import api_headers
from services.sources.source_limiter import get_limiter

settings = get_settings()
BASE = "https://api.core.ac.uk/v3"
_lim = get_limiter("core")

async def search(term: str, max_results: int = 25, year_from: int = None, year_to: int = None) -> list[dict]:
    filters = []
    if year_from:
        filters.append(f"yearPublished>={year_from}")
    if year_to:
        filters.append(f"yearPublished<={year_to}")

    payload: dict = {"q": term, "limit": min(max_results, 100),
                     "fields": ["title","authors","abstract","yearPublished","doi","downloadUrl","id"]}
    if filters:
        payload["filters"] = " AND ".join(filters)

    headers = api_headers("CORE")
    if settings.core_api_key:
        headers["Authorization"] = f"Bearer {settings.core_api_key}"

    for attempt in range(3):
        await _lim.acquire()
        try:
            async with httpx.AsyncClient(timeout=20, headers=headers) as client:
                r = await client.post(f"{BASE}/search/works", json=payload)
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
        authors = []
        for a in (item.get("authors") or []):
            name = a.get("name") or f"{a.get('firstName','')} {a.get('lastName','')}".strip()
            if name:
                authors.append(name)
        papers.append({
            "id": f"core:{item.get('id','')}",
            "title": item.get("title") or "",
            "authors": authors, "abstract": item.get("abstract") or "",
            "year": item.get("yearPublished"), "doi": item.get("doi"),
            "url": f"https://core.ac.uk/works/{item.get('id')}" if item.get("id") else None,
            "pdf_url": item.get("downloadUrl"), "source": "CORE",
        })
    return papers
