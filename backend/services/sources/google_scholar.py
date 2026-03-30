"""
Google Scholar source via `scholarly` library.
Implements Tor proxy fallback + graceful degradation if blocked.
Adds human-like delays between requests.
"""
import asyncio, time, random
from datetime import datetime
from config import get_settings
from services.anti_bot import scholar_delay

settings = get_settings()
_scholar_available = True
_last_failure: float = 0
_COOLDOWN_S = 300  # 5 min cooldown after block

def _setup_scholarly():
    """Configure scholarly with best available proxy."""
    from scholarly import scholarly, ProxyGenerator
    tor = settings.tor_proxy
    if tor:
        pg = ProxyGenerator()
        proxy_url = tor.replace("socks5://", "")
        host, _, port = proxy_url.partition(":")
        try:
            pg.Tor_Internal(tor_sock_port=int(port) if port else 9050)
            scholarly.use_proxy(pg)
            return scholarly
        except Exception:
            pass
    # No proxy — direct connection with scholarly's built-in retry
    return scholarly

def _sync_scholar_search(term: str, max_results: int, year_from: int | None, year_to: int | None) -> list[dict]:
    global _scholar_available, _last_failure
    try:
        scholarly_mod = _setup_scholarly()
        papers = []
        query = scholarly_mod.search_pubs(term)
        for i, pub in enumerate(query):
            if i >= max_results:
                break
            bib = pub.get("bib", {})
            year = None
            yr_str = str(bib.get("pub_year") or "")
            if yr_str.isdigit():
                year = int(yr_str)
            if year_from and year and year < year_from:
                continue
            if year_to and year and year > year_to:
                continue

            abstract = bib.get("abstract") or ""
            url = pub.get("pub_url") or pub.get("eprint_url") or ""
            pdf_url = pub.get("eprint_url") if pub.get("eprint_url") else None

            papers.append({
                "id": f"scholar:{pub.get('author_pub_id','')}{i}",
                "title": bib.get("title") or "",
                "authors": bib.get("author") if isinstance(bib.get("author"), list) else
                           ([bib["author"]] if bib.get("author") else []),
                "abstract": abstract,
                "year": year,
                "doi": None,
                "url": url,
                "pdf_url": pdf_url,
                "source": "Google Scholar",
            })
            time.sleep(random.uniform(2.5, 6.0))  # Human delay between Scholar hits

        _scholar_available = True
        return papers

    except Exception as e:
        err = str(e).lower()
        if "captcha" in err or "blocked" in err or "429" in err or "robot" in err:
            _scholar_available = False
            _last_failure = time.monotonic()
        return []

async def search(term: str, max_results: int = 20, year_from: int = None, year_to: int = None) -> list[dict]:
    global _scholar_available, _last_failure

    # Respect cooldown after block
    if not _scholar_available:
        if time.monotonic() - _last_failure < _COOLDOWN_S:
            return []
        _scholar_available = True

    await scholar_delay()  # Human-like pause before Scholar request

    loop = asyncio.get_event_loop()
    try:
        results = await asyncio.wait_for(
            loop.run_in_executor(None, _sync_scholar_search, term, max_results, year_from, year_to),
            timeout=60,
        )
        return results
    except asyncio.TimeoutError:
        return []
    except Exception:
        return []
