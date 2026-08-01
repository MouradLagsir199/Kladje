import httpx
from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from receptenapp.core.config import settings
from receptenapp.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness — no dependency checks, per docs/04-api.md."""
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(response: Response, db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    checks: dict[str, str] = {}

    try:
        await db.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception:
        checks["db"] = "unreachable"

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            jwks_response = await client.get(settings.clerk_jwks_url)
        checks["clerk_jwks"] = "ok" if jwks_response.status_code == 200 else "unreachable"
    except Exception:
        checks["clerk_jwks"] = "unreachable"

    ready = all(value == "ok" for value in checks.values())
    response.status_code = 200 if ready else 503
    return {"status": "ok" if ready else "not_ready", "checks": checks}
