"""
OpenClaw-specific auth endpoints.
Provides a pairing flow so OpenClaw can self-register and get an API key.
Mount this router in backend/main.py: app.include_router(openclaw_router)
"""
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from datetime import datetime, timedelta
import secrets, hashlib, json
from pathlib import Path
from db import create_api_key, verify_api_key

router = APIRouter(prefix="/openclaw", tags=["openclaw"])

# Pending pairings stored in data/openclaw_pairings.json
PAIRINGS_FILE = Path("./data/openclaw_pairings.json")

def _load_pairings() -> dict:
    if PAIRINGS_FILE.exists():
        return json.loads(PAIRINGS_FILE.read_text())
    return {}

def _save_pairings(p: dict):
    PAIRINGS_FILE.parent.mkdir(exist_ok=True)
    PAIRINGS_FILE.write_text(json.dumps(p, indent=2))

class PairRequest(BaseModel):
    agent_name: str        # e.g. "openclaw-main"
    agent_version: str = "1.0.0"
    description: str = ""

class PairResponse(BaseModel):
    pairing_code: str      # User confirms this in their terminal
    expires_in: int        # seconds

class ConfirmRequest(BaseModel):
    pairing_code: str

class AttachResponse(BaseModel):
    api_key: str
    message: str

# Step 1 — OpenClaw calls this to request attachment
@router.post("/pair", response_model=PairResponse)
async def request_pairing(body: PairRequest):
    code = secrets.token_hex(4).upper()  # e.g. "A3F9"
    pairings = _load_pairings()
    pairings[code] = {
        "agent_name": body.agent_name,
        "agent_version": body.agent_version,
        "description": body.description,
        "requested_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(minutes=10)).isoformat(),
        "approved": False,
    }
    _save_pairings(pairings)
    return PairResponse(pairing_code=code, expires_in=600)

# Step 2 — User approves in terminal (or via CLI: rpf openclaw approve <code>)
@router.post("/approve/{code}")
async def approve_pairing(code: str):
    pairings = _load_pairings()
    if code not in pairings:
        raise HTTPException(404, "Pairing code not found")
    p = pairings[code]
    if datetime.utcnow().isoformat() > p["expires_at"]:
        del pairings[code]
        _save_pairings(pairings)
        raise HTTPException(410, "Pairing code expired")
    pairings[code]["approved"] = True
    _save_pairings(pairings)
    return {"message": f"Pairing {code} approved for {p['agent_name']}"}

# Step 3 — OpenClaw polls this to get its API key after approval
@router.post("/attach", response_model=AttachResponse)
async def complete_pairing(body: ConfirmRequest):
    pairings = _load_pairings()
    code = body.pairing_code
    if code not in pairings:
        raise HTTPException(404, "Pairing code not found or already used")
    p = pairings[code]
    if not p.get("approved"):
        raise HTTPException(202, "Awaiting user approval — poll again")
    if datetime.utcnow().isoformat() > p["expires_at"]:
        del pairings[code]
        _save_pairings(pairings)
        raise HTTPException(410, "Pairing code expired")

    # Create API key for this OpenClaw instance
    key = await create_api_key(p["agent_name"])
    del pairings[code]  # One-time use
    _save_pairings(pairings)
    return AttachResponse(
        api_key=key,
        message=f"OpenClaw '{p['agent_name']}' v{p['agent_version']} successfully attached."
    )

# Verify an existing key (OpenClaw health check)
@router.get("/verify")
async def verify_key(x_api_key: str = Header(None)):
    if not x_api_key or not await verify_api_key(x_api_key):
        raise HTTPException(401, "Invalid API key")
    return {"status": "valid", "service": "research-paper-finder"}

# List pending pairings (for user's terminal use)
@router.get("/pending")
async def list_pending():
    pairings = _load_pairings()
    now = datetime.utcnow().isoformat()
    pending = [
        {"code": code, "agent": p["agent_name"], "approved": p["approved"],
         "expires_at": p["expires_at"]}
        for code, p in pairings.items()
        if p["expires_at"] > now
    ]
    return pending
