"""
NVIDIA NIM LLM service — 3-key rotation with per-key 20 RPM enforcement.
Total throughput: 60 RPM (3 accounts × 20 RPM free tier).
Model: nvidia/llama-3.1-nemotron-70b-instruct (best free-tier reasoning model)
"""
import asyncio, time, json, re, logging
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from config import get_settings
import aiofiles

settings = get_settings()
log = logging.getLogger("rpf")

# ── Per-key rate limiter (sliding 60s window) ────────────────────────────────

class _KeyLimiter:
    def __init__(self, key: str, rpm: int):
        self.key = key
        self.rpm = rpm
        self._ts: list[float] = []
        self._lock = asyncio.Lock()

    async def available_slots(self) -> int:
        async with self._lock:
            now = time.monotonic()
            self._ts = [t for t in self._ts if now - t < 60]
            return self.rpm - len(self._ts)

    async def acquire(self):
        while True:
            async with self._lock:
                now = time.monotonic()
                self._ts = [t for t in self._ts if now - t < 60]
                if len(self._ts) < self.rpm:
                    self._ts.append(now)
                    return
                wait_for = 60 - (now - self._ts[0]) + 0.2
            await asyncio.sleep(wait_for)


class KeyRotationScheduler:
    """Picks the key with the most remaining RPM capacity. Falls back to waiting."""
    def __init__(self, keys: list[str], rpm: int = 20):
        if not keys:
            raise RuntimeError("No NVIDIA API keys configured. Set NVIDIA_KEY_1/2/3 in .env")
        self._limiters = {k: _KeyLimiter(k, rpm) for k in keys}
        self._global_lock = asyncio.Lock()

    async def acquire(self) -> str:
        """Acquire a slot and return the key to use."""
        while True:
            # Check all keys, pick the one with most slots available
            slots = {k: await lim.available_slots() for k, lim in self._limiters.items()}
            best_key = max(slots, key=lambda k: slots[k])
            if slots[best_key] > 0:
                await self._limiters[best_key].acquire()
                return best_key
            # All at limit — wait the shortest time for any key to free up
            await asyncio.sleep(1.0)

# Singleton scheduler
_scheduler: KeyRotationScheduler | None = None

def get_scheduler() -> KeyRotationScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = KeyRotationScheduler(settings.nvidia_keys, settings.nvidia_rpm_per_key)
    return _scheduler


# ── LLM call ────────────────────────────────────────────────────────────────

async def _load_context() -> str:
    try:
        async with aiofiles.open(settings.context_path, "r") as f:
            return await f.read()
    except FileNotFoundError:
        return ""

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=3, max=15),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
async def _chat(system: str, user: str, max_tokens: int = 600) -> str:
    key = await get_scheduler().acquire()
    client = AsyncOpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=key,
    )
    
    try:
        stream = await client.chat.completions.create(
            model=settings.nvidia_model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.7,
            top_p=0.9,
            max_tokens=max_tokens,
            stream=True
        )
        
        full_content = []

        async for chunk in stream:
            if not chunk.choices:
                continue

            content = chunk.choices[0].delta.content
            if content:
                full_content.append(content)

        final_text = "".join(full_content).strip()
        if not final_text:
            log.error(f"Empty response from model {settings.nvidia_model}")
            
        return final_text
    except Exception as e:
        log.error(f"LLM Error ({settings.nvidia_model}): {e}")
        raise e

def _parse_json(text: str):
    text = text.strip()
    # Strip markdown code fences
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    match = re.search(r"(\[[\s\S]*?\]|\{[\s\S]*?\})", text)
    if match:
        return json.loads(match.group(1))
    return json.loads(text)


# ── Public API ───────────────────────────────────────────────────────────────

async def generate_search_terms(query: str) -> dict:
    """
    Returns dict with:
      terms_general: list[str]  — generic terms for Scholar/CrossRef/OpenAlex
      terms_arxiv: list[str]    — arXiv-optimized (with category hints)
      terms_pubmed: list[str]   — PubMed/MeSH-aware terms
      domain: str               — detected domain
      exclude_terms: list[str]  — terms to filter noise
    """
    ctx = await _load_context()
    system = (
        f"{ctx}\n\n"
        "You are in ROLE 1: Advanced Query Architect.\n"
        'Output ONLY valid JSON with keys: terms_general (list[str], 6 items), '
        'terms_arxiv (list[str], 4 items), terms_pubmed (list[str], 4 items), '
        'domain (str), exclude_terms (list[str], 3 common noise terms to avoid).'
    )
    raw = await _chat(system, f"Query: {query}", max_tokens=500)
    try:
        data = _parse_json(raw)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    # Fallback: return basic terms
    return {
        "terms_general": [query],
        "terms_arxiv": [query],
        "terms_pubmed": [query],
        "domain": "general",
        "exclude_terms": [],
    }

async def score_paper(
    query: str,
    model_query_context: str,
    title: str,
    abstract: str,
    obligatory_concepts: list[str] | None = None,
) -> tuple[float, str]:
    """Score a paper 0-100. Obligatory concepts passed to enforce strict multi-concept matching."""
    ctx = await _load_context()
    concepts_line = ""
    if obligatory_concepts:
        concepts_line = f"\nObligatory concepts (ALL must be present for score ≥ 70): {', '.join(obligatory_concepts)}"
    system = (
        f"{ctx}\n\n"
        "You are in ROLE 2: Strict Multi-Concept Relevance Scorer.\n"
        'Output ONLY JSON: {"score": <int 0-100>, "reasoning": "<1-2 sentences: which concepts found/missing>", "concepts_found": ["list"]}'
    )
    truncated = abstract[:700] if abstract else "No abstract available."
    user = (
        f"Query: {query}{concepts_line}\n"
        f"Expanded intent: {model_query_context}\n"
        f"Title: {title}\n"
        f"Abstract: {truncated}"
    )
    raw = await _chat(system, user, max_tokens=200)
    try:
        data = _parse_json(raw)
        return float(data.get("score", 0)), str(data.get("reasoning", ""))
    except Exception:
        return 0.0, "Score unavailable"

async def get_associated_queries(query: str, title: str, abstract: str) -> list[str]:
    ctx = await _load_context()
    system = (
        f"{ctx}\n\n"
        "You are in ROLE 3: Associated Research Navigator.\n"
        "Output ONLY a JSON array of 3 precise search query strings for finding associated papers."
    )
    raw = await _chat(system, f"Query: {query}\nPaper: {title}\nAbstract: {abstract[:400]}", max_tokens=220)
    try:
        res = _parse_json(raw)
        if isinstance(res, list):
            return [str(t) for t in res[:3]]
    except Exception:
        pass
    return []

async def build_query_intent(query: str, generated: dict) -> str:
    """Build a compact description of what the query really seeks — used in scoring."""
    domain = generated.get("domain", "")
    all_terms = generated.get("terms_general", [])
    return f"Domain: {domain}. Core intent: {query}. Key concepts: {', '.join(all_terms[:4])}."

async def batch_score_papers(
    query: str,
    query_intent: str,
    papers: list[dict],
    obligatory_concepts: list[str] | None = None,
) -> list[dict]:
    """Score all papers with DB caching. Passes obligatory_concepts for strict multi-concept enforcement."""
    from db import get_paper_score, cache_paper_score
    results = []
    for paper in papers:
        pid = paper.get("id", "")
        cached = await get_paper_score(pid, query) if pid else None
        if cached:
            paper["relevance_score"], paper["relevance_reasoning"] = cached
        else:
            score, reason = await score_paper(
                query, query_intent,
                paper.get("title", ""), paper.get("abstract", ""),
                obligatory_concepts,
            )
            paper["relevance_score"] = score
            paper["relevance_reasoning"] = reason
            if pid:
                await cache_paper_score(pid, query, score, reason)
        results.append(paper)
    return results
