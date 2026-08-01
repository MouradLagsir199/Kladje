from typing import Any

import jwt
from fastapi import Depends, Request
from jwt import PyJWKClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from receptenapp.core.config import settings
from receptenapp.core.errors import UnauthorizedError
from receptenapp.db.models import User
from receptenapp.db.session import get_db

_jwk_client: PyJWKClient | None = None


def _get_jwk_client() -> PyJWKClient:
    """Lazily-built, module-level so the JWKS cache survives across requests."""
    global _jwk_client
    if _jwk_client is None:
        _jwk_client = PyJWKClient(settings.clerk_jwks_url, cache_keys=True, lifespan=3600)
    return _jwk_client


def decode_clerk_token(token: str) -> dict[str, Any]:
    """Verify a Clerk-issued JWT against Clerk's JWKS. Raises UnauthorizedError on any failure."""
    try:
        signing_key = _get_jwk_client().get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token, signing_key.key, algorithms=["RS256"], options={"verify_aud": False}
        )
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Ongeldig of verlopen token.") from exc
    return payload


async def get_or_create_user(db: AsyncSession, clerk_user_id: str, email: str | None) -> User:
    """JIT user creation. Never rely on Clerk webhooks for this — see docs/04-api.md."""
    result = await db.execute(select(User).where(User.clerk_user_id == clerk_user_id))
    user = result.scalar_one_or_none()
    if user is not None:
        return user

    user = User(clerk_user_id=clerk_user_id, email=email, email_verified=bool(email))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise UnauthorizedError("Ontbrekend of ongeldig token.")

    token = auth_header.removeprefix("Bearer ")
    claims = decode_clerk_token(token)

    clerk_user_id = claims.get("sub")
    if not clerk_user_id:
        raise UnauthorizedError("Ongeldig token.")

    email = claims.get("email")
    return await get_or_create_user(db, clerk_user_id, email)
