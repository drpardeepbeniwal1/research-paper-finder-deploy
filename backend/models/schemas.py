from pydantic import BaseModel, Field
from typing import Optional

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500)
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    max_results: int = Field(default=50, ge=1, le=9999)
    include_associated: bool = False
    email: Optional[str] = None  # Optional email for completion notification

class Paper(BaseModel):
    id: str = ""
    title: str = ""
    authors: list[str] = []
    abstract: str = ""
    year: Optional[int] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    pdf_url: Optional[str] = None
    source: str = ""
    citation_count: int = 0
    relevance_score: float = 0.0
    relevance_reasoning: str = ""
    associated_papers: list["Paper"] = []

class PDFReports(BaseModel):
    confirmed: Optional[str] = None
    suspicious: Optional[str] = None
    rejected: Optional[str] = None

class DownloadedPapers(BaseModel):
    accepted: list[str] = []
    maybe: list[str] = []
    rejected: list[str] = []

class SearchResult(BaseModel):
    query: str
    generated_terms: list[str]
    papers: list[Paper]
    total_found: int
    total_suspicious: int = 0
    total_rejected: int = 0
    pdf_reports: PDFReports = PDFReports()
    downloaded_papers: DownloadedPapers = DownloadedPapers()

class SearchTaskResponse(BaseModel):
    task_id: str
    status: str = "pending"

class SearchStatusResponse(BaseModel):
    status: str # "pending", "running", "completed", "failed"
    result: Optional[SearchResult] = None
    error: Optional[str] = None
    progress: Optional[str] = None  # Live activity message
    progress_percent: int = 0  # 0-100

class APIKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)

class APIKeyResponse(BaseModel):
    key: str
    name: str
    created_at: str
