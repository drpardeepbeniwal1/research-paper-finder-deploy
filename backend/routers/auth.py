from fastapi import APIRouter, HTTPException, Security
from fastapi.security import APIKeyHeader
from models.schemas import APIKeyCreate, APIKeyResponse
from db import create_api_key, verify_api_key, list_api_keys
from datetime import datetime

router = APIRouter(prefix="/auth", tags=["auth"])
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def require_api_key(key: str = Security(api_key_header)):
    if not key or not await verify_api_key(key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return key

@router.post("/keys", response_model=APIKeyResponse)
async def create_key(body: APIKeyCreate):
    key = await create_api_key(body.name)
    return APIKeyResponse(key=key, name=body.name, created_at=datetime.utcnow().isoformat())

@router.get("/keys")
async def get_keys():
    return await list_api_keys()
