from functools import lru_cache
import os

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")
DATA_DIR = os.path.join(BASE_DIR, "data")
PAPERS_DIR = os.path.join(DATA_DIR, "papers")
PDFS_DIR = os.path.join(DATA_DIR, "pdfs")
CONTEXT_FILE = os.path.join(BASE_DIR, "context", "research_context.md")

class Settings(BaseSettings):
    # NVIDIA NIM — 3 accounts × 20 RPM = 60 RPM total
    nvidia_key_1: str = ""
    nvidia_key_2: str = ""
    nvidia_key_3: str = ""
    nvidia_model: str = "nvidia/llama-3.1-nemotron-70b-instruct"
    nvidia_rpm_per_key: int = 20

    # Server
    secret_key: str = "change-on-vps"
    api_host: str = "127.0.0.1"   # 127.0.0.1 = localhost only; change to 0.0.0.0 for VPS/tunnel
    api_port: int = 8000
    debug: bool = False
    db_path: str = os.path.join(DATA_DIR, "papers.db")
    context_path: str = CONTEXT_FILE

    # Secure access token (random string; set in .env for production)
    access_token: str = ""   # If set, all requests must include X-Access-Token header

    # Search
    max_results_per_source: int = 30
    confirmed_threshold: int = 70
    suspicious_threshold: int = 40

    # PDF downloads
    download_actual_pdfs: bool = True
    max_pdf_size_mb: int = 30
    pdf_download_concurrency: int = 3
    scihub_enabled: bool = False   # Set true to enable Sci-Hub as last resort

    # Optional API keys / proxy
    core_api_key: str = ""
    ncbi_api_key: str = ""
    tor_proxy: str = ""

    # Email notification (optional)
    smtp_server: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@research-paper-finder.com"

    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    @field_validator("debug", mode="before")
    @classmethod
    def normalize_debug(cls, value):
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"release", "prod", "production"}:
                return False
            if lowered in {"debug", "dev", "development"}:
                return True
        return value

    @property
    def nvidia_keys(self) -> list[str]:
        return [k for k in [self.nvidia_key_1, self.nvidia_key_2, self.nvidia_key_3] if k.strip()]

    @property
    def max_pdf_bytes(self) -> int:
        return self.max_pdf_size_mb * 1024 * 1024

@lru_cache
def get_settings() -> Settings:
    for d in [
        PDFS_DIR,
        os.path.join(PAPERS_DIR, "accepted"),
        os.path.join(PAPERS_DIR, "maybe"),
        os.path.join(PAPERS_DIR, "rejected"),
    ]:
        os.makedirs(d, exist_ok=True)
    return Settings()
