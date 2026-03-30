"""
Human-like request behavior — rotating UAs, realistic headers, jittered delays.
Used by all scraped sources (especially Google Scholar) to avoid detection.
"""
import asyncio, random, time
from typing import Optional

try:
    from fake_useragent import UserAgent
    _ua = UserAgent(browsers=["chrome", "firefox", "edge"], os=["windows", "macos", "linux"])
    def get_ua() -> str:
        return _ua.random
except Exception:
    _FALLBACK_UAS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    ]
    def get_ua() -> str:
        return random.choice(_FALLBACK_UAS)

_ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9,en-US;q=0.8",
    "en-US,en;q=0.9,fr;q=0.8",
    "en-US,en;q=0.8",
]

_REFERERS = [
    "https://www.google.com/",
    "https://www.bing.com/",
    "https://duckduckgo.com/",
    "https://scholar.google.com/",
    None,
]

def stealth_headers(referer: Optional[str] = None) -> dict:
    """Generate realistic browser headers for a request."""
    ua = get_ua()
    is_chrome = "Chrome" in ua
    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": random.choice(_ACCEPT_LANGUAGES),
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
        "DNT": str(random.choice([0, 1])),
    }
    if is_chrome:
        headers.update({
            "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": random.choice(['"Windows"', '"macOS"', '"Linux"']),
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site" if referer else "none",
            "Sec-Fetch-User": "?1",
        })
    if referer:
        headers["Referer"] = referer
    elif random.random() < 0.3:
        headers["Referer"] = random.choice([r for r in _REFERERS if r])
    return headers

def api_headers(service: str = "") -> dict:
    """Lighter headers for API sources (JSON endpoints)."""
    return {
        "User-Agent": f"ResearchPaperFinder/2.0 (Academic Research Tool; {service}; mailto:research@tool.local)",
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
    }

async def human_delay(min_s: float = 1.5, max_s: float = 5.0):
    """Random delay mimicking human reading/thinking time."""
    base = random.uniform(min_s, max_s)
    jitter = random.gauss(0, 0.3)
    await asyncio.sleep(max(0.5, base + jitter))

async def scholar_delay():
    """Longer delays specifically for Scholar to avoid rate limiting."""
    await human_delay(3.0, 8.0)
    # Occasionally add a "reading pause"
    if random.random() < 0.2:
        await asyncio.sleep(random.uniform(5, 12))
