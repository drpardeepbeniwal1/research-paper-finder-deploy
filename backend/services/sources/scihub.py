"""
Sci-Hub PDF resolver — last resort when no open-access version exists.
Tries multiple Sci-Hub domains with stealth headers.
Only activated when SCIHUB_ENABLED=true in config.
VPS usage: your VPS IP is not India-banned, so direct access works.
"""
import re, logging
import httpx
from services.anti_bot import stealth_headers, human_delay
from services.sources.source_limiter import get_limiter

log = logging.getLogger("rpf.scihub")
_lim = get_limiter("scihub")

# Domains change — listed by reliability. Script tries all until one works.
SCIHUB_DOMAINS = [
    "https://sci-hub.se",
    "https://sci-hub.st",
    "https://sci-hub.ru",
    "https://sci-hub.mksa.top",
    "https://sci-hub.hkvisa.net",
    "https://www.sci-hub.wf",
]

_PDF_PATTERNS = [
    r'<iframe[^>]+src=["\']([^"\']+)["\'][^>]*>',
    r'<embed[^>]+src=["\']([^"\']+)["\']',
    r'"url"\s*:\s*"([^"]+\.pdf[^"]*)"',
    r"location\.href\s*=\s*['\"]([^'\"]+\.pdf[^'\"]*)['\"]",
    r'<a[^>]+href=["\']([^"\']+\.pdf)["\']',
    r'src=["\'](\S+\.pdf\S*)["\']',
]

def _extract_pdf_url(html: str, base_domain: str) -> str | None:
    for pattern in _PDF_PATTERNS:
        m = re.search(pattern, html, re.IGNORECASE)
        if m:
            url = m.group(1).strip()
            if url.startswith("//"):
                return "https:" + url
            if url.startswith("/"):
                return base_domain + url
            if url.startswith("http"):
                return url
    return None

async def resolve_pdf(doi: str, tor_proxy: str = "") -> str | None:
    """Return a direct PDF URL from Sci-Hub for the given DOI, or None."""
    doi_clean = re.sub(r"^https?://doi\.org/", "", (doi or "").strip())
    if not doi_clean:
        return None

    proxies = {"all://": tor_proxy} if tor_proxy else None

    for domain in SCIHUB_DOMAINS:
        await _lim.acquire()
        await human_delay(1.5, 4.0)
        url = f"{domain}/{doi_clean}"
        try:
            kwargs: dict = dict(
                timeout=25,
                follow_redirects=True,
                headers=stealth_headers(referer="https://www.google.com/"),
            )
            if proxies:
                kwargs["proxies"] = proxies

            async with httpx.AsyncClient(**kwargs) as client:
                r = await client.get(url)

            if r.status_code == 429:
                await _lim.on_429(60)
                continue
            if r.status_code not in (200, 302):
                continue

            # Check if Sci-Hub returned the paper page (not a CAPTCHA page)
            html = r.text
            if "captcha" in html.lower() and len(html) < 5000:
                log.debug(f"{domain}: CAPTCHA encountered, trying next domain")
                continue

            pdf_url = _extract_pdf_url(html, domain)
            if pdf_url:
                log.info(f"Sci-Hub resolved: {doi_clean} → {pdf_url[:60]}")
                _lim.on_success()
                return pdf_url

        except Exception as e:
            log.debug(f"Sci-Hub {domain} error: {e}")
            continue

    return None
