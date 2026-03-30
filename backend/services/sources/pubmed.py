import httpx, asyncio, xml.etree.ElementTree as ET
from config import get_settings
from services.anti_bot import api_headers
from services.sources.source_limiter import get_limiter

settings = get_settings()
BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_lim = get_limiter("pubmed")

def _ncbi_params(extra=None):
    p = {"retmode": "json", "tool": "ResearchPaperFinder", "email": "research@tool.local"}
    if settings.ncbi_api_key:
        p["api_key"] = settings.ncbi_api_key
    if extra:
        p.update(extra)
    return p

async def _fetch_xml(url, params):
    for attempt in range(3):
        await _lim.acquire()
        try:
            async with httpx.AsyncClient(timeout=20, headers=api_headers("PubMed")) as c:
                r = await c.get(url, params=params)
            if r.status_code == 429:
                await _lim.on_429(int(r.headers.get("Retry-After", 60)))
                continue
            r.raise_for_status()
            _lim.on_success()
            return r.text
        except Exception:
            if attempt == 2:
                return None
    return None

async def search(term: str, max_results: int = 25, year_from: int = None, year_to: int = None) -> list[dict]:
    query = term
    if year_from or year_to:
        query += f' AND ("{year_from or 1900}"[PDat] : "{year_to or 2100}"[PDat])'

    for attempt in range(3):
        await _lim.acquire()
        try:
            async with httpx.AsyncClient(timeout=20, headers=api_headers("PubMed")) as c:
                r = await c.get(f"{BASE}/esearch.fcgi",
                                params=_ncbi_params({"db":"pubmed","term":query,"retmax":min(max_results,100),"sort":"relevance"}))
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

    ids = data.get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []

    await asyncio.sleep(0.4)  # Polite spacing

    # Fetch abstracts
    abstracts = {}
    xml_text = await _fetch_xml(f"{BASE}/efetch.fcgi",
                                _ncbi_params({"db":"pubmed","id":",".join(ids),"rettype":"abstract","retmode":"xml"}))
    if xml_text:
        try:
            root = ET.fromstring(xml_text)
            for art in root.findall(".//PubmedArticle"):
                pmid_el = art.find(".//PMID")
                if pmid_el is None:
                    continue
                texts = [el.text or "" for el in art.findall(".//AbstractText") if el.text]
                abstracts[pmid_el.text] = " ".join(texts)
        except Exception:
            pass

    await asyncio.sleep(0.4)
    for attempt in range(3):
        await _lim.acquire()
        try:
            async with httpx.AsyncClient(timeout=20, headers=api_headers("PubMed")) as c:
                r = await c.get(f"{BASE}/esummary.fcgi",
                                params=_ncbi_params({"db":"pubmed","id":",".join(ids)}))
            if r.status_code == 429:
                await _lim.on_429(60)
                continue
            r.raise_for_status()
            _lim.on_success()
            sdata = r.json()
            break
        except Exception:
            if attempt == 2:
                return []
    else:
        return []

    papers = []
    for pmid in ids:
        info = sdata.get("result", {}).get(pmid, {})
        if not info or pmid == "uids":
            continue
        year = None
        pub_date = info.get("pubdate","")
        if pub_date:
            try:
                year = int(pub_date[:4])
            except Exception:
                pass
        authors = [a.get("name","") for a in (info.get("authors") or [])]
        doi = next((x["value"] for x in (info.get("articleids") or []) if x.get("idtype")=="doi"), None)
        papers.append({
            "id": f"pubmed:{pmid}", "title": info.get("title") or "",
            "authors": authors, "abstract": abstracts.get(pmid, ""),
            "year": year, "doi": doi,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "pdf_url": None, "source": "PubMed",
        })
    return papers
