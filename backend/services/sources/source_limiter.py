"""
Per-source rate limiter with 429 exponential backoff and circuit breaker.
Each source gets its own limiter tuned to its actual API limits.
"""
import asyncio, time, logging

log = logging.getLogger("rpf.limiter")

class SourceRateLimiter:
    def __init__(self, name: str, rpm: int, max_backoff: int = 300):
        self.name = name
        self.rpm = rpm
        self.max_backoff = max_backoff
        self._ts: list[float] = []
        self._backoff_until: float = 0.0
        self._consecutive_429: int = 0
        self._lock = asyncio.Lock()
        self._circuit_open_until: float = 0.0  # Circuit breaker

    async def acquire(self):
        async with self._lock:
            now = time.monotonic()

            # Circuit breaker — source is completely down
            if now < self._circuit_open_until:
                wait = self._circuit_open_until - now
                log.debug(f"{self.name}: circuit open, sleeping {wait:.1f}s")
                await asyncio.sleep(wait)
                now = time.monotonic()

            # Exponential backoff from 429
            if now < self._backoff_until:
                wait = self._backoff_until - now + 0.1
                await asyncio.sleep(wait)
                now = time.monotonic()

            # Sliding window rate limit
            self._ts = [t for t in self._ts if now - t < 60]
            if len(self._ts) >= self.rpm:
                wait = 60 - (now - self._ts[0]) + 0.5
                await asyncio.sleep(wait)
                now = time.monotonic()
                self._ts = [t for t in self._ts if now - t < 60]

            self._ts.append(time.monotonic())

    async def on_429(self, retry_after: int = 0):
        async with self._lock:
            self._consecutive_429 += 1
            # Exponential backoff: 30s, 60s, 120s, 240s... capped at max_backoff
            base = retry_after if retry_after > 0 else 30
            backoff = min(base * (2 ** (self._consecutive_429 - 1)), self.max_backoff)
            self._backoff_until = time.monotonic() + backoff
            log.warning(f"{self.name}: 429 (attempt {self._consecutive_429}), backoff {backoff:.0f}s")
            # Open circuit after 4 consecutive 429s (source is abusing us)
            if self._consecutive_429 >= 4:
                self._circuit_open_until = time.monotonic() + 600  # 10 min
                log.warning(f"{self.name}: circuit breaker OPEN for 10 min")

    def on_success(self):
        if self._consecutive_429 > 0:
            log.info(f"{self.name}: recovered after {self._consecutive_429} 429s")
        self._consecutive_429 = 0
        self._circuit_open_until = 0.0

# Per-source limits (tuned conservatively to avoid 429s)
_LIMITERS: dict[str, SourceRateLimiter] = {
    "arxiv":           SourceRateLimiter("arxiv",           rpm=12),
    "semantic_scholar": SourceRateLimiter("semantic_scholar", rpm=10),
    "openalex":        SourceRateLimiter("openalex",        rpm=18),
    "google_scholar":  SourceRateLimiter("google_scholar",  rpm=4),
    "pubmed":          SourceRateLimiter("pubmed",          rpm=8),
    "core":            SourceRateLimiter("core",            rpm=8),
    "crossref":        SourceRateLimiter("crossref",        rpm=18),
    "europe_pmc":      SourceRateLimiter("europe_pmc",      rpm=12),
    "base":            SourceRateLimiter("base",            rpm=8),
    "unpaywall":       SourceRateLimiter("unpaywall",       rpm=10),
    "scihub":          SourceRateLimiter("scihub",          rpm=6),
}

def get_limiter(name: str) -> SourceRateLimiter:
    return _LIMITERS.get(name, SourceRateLimiter(name, rpm=8))

async def with_retry(name: str, coro_factory, max_attempts: int = 3):
    """
    Execute coro_factory() with rate limiting + 429 retry.
    coro_factory is called fresh each attempt (new coroutine).
    Returns result or None on failure.
    """
    limiter = get_limiter(name)
    for attempt in range(max_attempts):
        await limiter.acquire()
        try:
            result = await coro_factory()
            limiter.on_success()
            return result
        except Exception as e:
            msg = str(e).lower()
            if "429" in msg or "too many" in msg or "rate limit" in msg:
                retry_after = 60
                await limiter.on_429(retry_after)
                if attempt < max_attempts - 1:
                    continue
            # Non-429 error — return empty, don't retry
            return None
    return None
