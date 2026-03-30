import aiosqlite
import hashlib, secrets, json
from datetime import datetime
from config import get_settings

DB = get_settings().db_path

async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_hash TEXT UNIQUE NOT NULL,
                key_prefix TEXT NOT NULL,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_used TEXT
            );
            CREATE TABLE IF NOT EXISTS search_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cache_key TEXT UNIQUE NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS paper_scores (
                paper_id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                score REAL NOT NULL,
                reasoning TEXT,
                scored_at TEXT NOT NULL
            );
        """)
        await db.commit()

def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()

async def create_api_key(name: str) -> str:
    key = f"rpf_{secrets.token_urlsafe(32)}"
    key_hash = _hash_key(key)
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO api_keys (key_hash, key_prefix, name, created_at) VALUES (?,?,?,?)",
            (key_hash, key[:12], name, now)
        )
        await db.commit()
    return key

async def verify_api_key(key: str) -> bool:
    key_hash = _hash_key(key)
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT id FROM api_keys WHERE key_hash=?", (key_hash,))
        row = await cur.fetchone()
        if row:
            await db.execute("UPDATE api_keys SET last_used=? WHERE key_hash=?",
                             (datetime.utcnow().isoformat(), key_hash))
            await db.commit()
            return True
    return False

async def list_api_keys() -> list[dict]:
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT key_prefix, name, created_at, last_used FROM api_keys")
        rows = await cur.fetchall()
    return [{"key_prefix": r[0], "name": r[1], "created_at": r[2], "last_used": r[3]} for r in rows]

async def get_cached_search(cache_key: str) -> dict | None:
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT result_json FROM search_cache WHERE cache_key=?", (cache_key,))
        row = await cur.fetchone()
    return json.loads(row[0]) if row else None

async def cache_search(cache_key: str, result: dict):
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT OR REPLACE INTO search_cache (cache_key, result_json, created_at) VALUES (?,?,?)",
            (cache_key, json.dumps(result), now)
        )
        await db.commit()

async def get_paper_score(paper_id: str, query: str) -> tuple[float, str] | None:
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute(
            "SELECT score, reasoning FROM paper_scores WHERE paper_id=? AND query=?",
            (paper_id, query)
        )
        row = await cur.fetchone()
    return (row[0], row[1]) if row else None

async def cache_paper_score(paper_id: str, query: str, score: float, reasoning: str):
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT OR REPLACE INTO paper_scores (paper_id, query, score, reasoning, scored_at) VALUES (?,?,?,?,?)",
            (paper_id, query, score, reasoning, now)
        )
        await db.commit()
