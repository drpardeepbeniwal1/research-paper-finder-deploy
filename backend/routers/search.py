import os, uuid, asyncio, logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from models.schemas import SearchRequest, SearchResult, SearchTaskResponse, SearchStatusResponse
from services.search_engine import run_search
from services.email_service import send_completion_email
from routers.auth import require_api_key

log = logging.getLogger("rpf")

router = APIRouter(prefix="/search", tags=["search"])

# In-memory storage for search tasks
# In a production app, this would be Redis/DB
_tasks: dict[str, dict] = {}

async def _job_run_search(task_id: str, req: SearchRequest):
    try:
        _tasks[task_id] = {"status": "running", "progress": "Initializing search pipeline...", "progress_percent": 3}

        def on_progress(msg: str, pct: int):
            _tasks[task_id] = {"status": "running", "progress": msg, "progress_percent": pct}

        result = await run_search(
            query=req.query,
            year_from=req.year_from,
            year_to=req.year_to,
            max_results=req.max_results,
            include_associated=req.include_associated,
            on_progress=on_progress,
        )

        _tasks[task_id] = {
            "status": "completed",
            "result": result,
            "progress": "Search completed",
            "progress_percent": 100
        }

        # Send email if provided
        if req.email:
            asyncio.create_task(send_completion_email(req.email, req.query, result))

    except Exception as e:
        log.error(f"Background search error: {e}", exc_info=True)
        _tasks[task_id] = {
            "status": "failed",
            "error": str(e),
            "progress": f"Error: {str(e)}",
            "progress_percent": 0
        }

@router.post("", response_model=SearchTaskResponse)
async def search_papers(
    req: SearchRequest, 
    background_tasks: BackgroundTasks,
    _: str = Depends(require_api_key)
):
    if not req.query.strip():
        raise HTTPException(400, "Query cannot be empty")
    
    task_id = str(uuid.uuid4())
    _tasks[task_id] = {"status": "pending"}
    
    background_tasks.add_task(_job_run_search, task_id, req)
    
    return SearchTaskResponse(task_id=task_id)

@router.get("/status/{task_id}", response_model=SearchStatusResponse)
async def get_search_status(task_id: str, _: str = Depends(require_api_key)):
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(404, "Task not found")

    return SearchStatusResponse(
        status=task["status"],
        result=task.get("result"),
        error=task.get("error"),
        progress=task.get("progress"),
        progress_percent=task.get("progress_percent", 0)
    )

# ── Summary PDF reports (the 3-tier generated reports) ──────────────────────
@router.get("/pdf/{filename}")
async def download_summary_pdf(filename: str, _: str = Depends(require_api_key)):
    path = _safe_path("./data/pdfs", filename)
    if not os.path.exists(path):
        raise HTTPException(404, "PDF not found")
    return FileResponse(path, media_type="application/pdf", filename=filename)

# ── Actual downloaded paper PDFs ──────────────────────────────────────────────
@router.get("/papers/{tier}/{filename}")
async def download_paper(tier: str, filename: str, _: str = Depends(require_api_key)):
    if tier not in ("accepted", "maybe", "rejected"):
        raise HTTPException(400, "Tier must be accepted, maybe, or rejected")
    path = _safe_path("./data/papers", tier, filename)
    if not os.path.exists(path):
        raise HTTPException(404, "Paper PDF not found")
    return FileResponse(path, media_type="application/pdf", filename=filename)

@router.get("/papers/{tier}")
async def list_papers_in_tier(tier: str, _: str = Depends(require_api_key)):
    if tier not in ("accepted", "maybe", "rejected"):
        raise HTTPException(400, "Invalid tier")
    folder = os.path.join("./data/papers", tier)
    if not os.path.exists(folder):
        return []
    # Sorted descending by filename = 2026_... before 2025_... before 2024_...
    files = sorted(
        (f for f in os.listdir(folder) if f.endswith(".pdf")),
        reverse=True
    )
    return [
        {"filename": f, "size_kb": round(os.path.getsize(os.path.join(folder, f)) / 1024, 1),
         "year": f[:4] if f[:4].isdigit() else "?"}
        for f in files
    ]


# ── Utility ──────────────────────────────────────────────────────────────────
def _safe_path(*parts: str) -> str:
    """Safely join path parts and prevent directory traversal."""
    base = os.path.abspath(parts[0])
    path = os.path.abspath(os.path.join(*parts))
    if not path.startswith(base):
        raise HTTPException(400, "Invalid path")
    return path
