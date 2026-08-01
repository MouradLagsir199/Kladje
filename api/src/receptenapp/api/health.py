from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness — no dependency checks, per docs/04-api.md."""
    return {"status": "ok"}


@router.get("/readyz")
async def readyz() -> dict[str, str]:
    """Readiness. DB and Clerk JWKS checks land here in tasks 0.8/0.9."""
    return {"status": "ok"}
