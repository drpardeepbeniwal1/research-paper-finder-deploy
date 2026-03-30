import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import uvicorn, logging, secrets
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from starlette.middleware.base import BaseHTTPMiddleware

from config import get_settings
from db import init_db
from routers import search, auth
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "openclaw"))
from auth_router import router as openclaw_router

settings = get_settings()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("rpf")

# ── Access Token Middleware ────────────────────────────────────────────────────
class AccessTokenMiddleware(BaseHTTPMiddleware):
    """
    If ACCESS_TOKEN is set in .env, all requests must provide it via:
      - Header: X-Access-Token: <token>
      - OR query param: ?token=<token>
    Exemptions: /health (for Cloudflare health checks)
    """
    async def dispatch(self, request: Request, call_next):
        token = settings.access_token
        if not token:
            return await call_next(request)

        # Exemptions for frontend assets and health check
        path = request.url.path
        if (
            path == "/health"
            or path == "/"
            or path == "/index.html"
            or path.startswith("/assets/")
            or path == "/favicon.ico"
            or path == "/auth/keys"  # Allow creating API keys without access token
        ):
            return await call_next(request)

        provided = (
            request.headers.get("X-Access-Token")
            or request.query_params.get("token")
        )
        if not provided or not secrets.compare_digest(provided, token):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)

        return await call_next(request)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    for d in ["./data/pdfs", "./data/papers/accepted", "./data/papers/maybe", "./data/papers/rejected"]:
        os.makedirs(d, exist_ok=True)

    n = len(settings.nvidia_keys)
    if n == 0:
        log.warning("No NVIDIA API keys — set NVIDIA_KEY_1/2/3 in .env")
    else:
        log.info(f"NVIDIA: {n} key(s), model={settings.nvidia_model}, {n*settings.nvidia_rpm_per_key} RPM total")

    log.info(f"Listening: {settings.api_host}:{settings.api_port}")
    if settings.access_token:
        log.info(f"Access token ENABLED (length={len(settings.access_token)})")
    if settings.scihub_enabled:
        log.info("Sci-Hub: ENABLED as last-resort PDF source")
    yield

app = FastAPI(
    title="Research Paper Finder",
    version="3.0.0",
    lifespan=lifespan,
    docs_url="/docs",      # always enable for terminal VPS testing
    redoc_url=None,
    openapi_url="/openapi.json",
)

# Access token check (before anything else)
app.add_middleware(AccessTokenMiddleware)

# CORS — allow any origin when running via Cloudflare tunnel or local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Token middleware handles auth; CORS just enables browser requests
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["X-API-Key", "X-Access-Token", "Content-Type"],
)

# API routes (registered before static, so they take priority)
app.include_router(auth.router)
app.include_router(search.router)
app.include_router(openclaw_router)

@app.get("/health")
async def health():
    n = len(settings.nvidia_keys)
    return {
        "status": "ok",
        "model": settings.nvidia_model,
        "active_keys": n,
        "total_rpm": n * settings.nvidia_rpm_per_key,
        "scihub": settings.scihub_enabled,
        "sources": ["arXiv","Semantic Scholar","OpenAlex","Google Scholar",
                    "PubMed","CORE","CrossRef","Europe PMC","BASE"],
        "pdf_tiers": ["accepted≥70","maybe 40-69","rejected<40"],
    }

# Frontend static files (served after API routes — catch-all SPA)
_frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(_frontend_dist):
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")
    log.info(f"Serving frontend from {_frontend_dist}")
else:
    log.info("Frontend not built yet. Run: cd frontend && npm run build")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
        workers=1,   # Must be 1 — rate limiter scheduler is in-process state
        log_level="info",
    )
