import uuid
from types import SimpleNamespace

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends, FastAPI

from receptenapp.core import security
from receptenapp.core.errors import register_exception_handlers
from receptenapp.db.models import User
from receptenapp.db.session import async_session_factory


def _pem_pair() -> tuple[bytes, bytes]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


@pytest.fixture(scope="module")
def rsa_keys() -> tuple[bytes, bytes]:
    return _pem_pair()


@pytest.fixture
def patched_jwk_client(monkeypatch: pytest.MonkeyPatch, rsa_keys: tuple[bytes, bytes]) -> None:
    _, public_pem = rsa_keys
    fake_client = SimpleNamespace(
        get_signing_key_from_jwt=lambda token: SimpleNamespace(key=public_pem)
    )
    monkeypatch.setattr(security, "_get_jwk_client", lambda: fake_client)


def _make_token(private_pem: bytes, *, sub: str, email: str | None = "test@example.com") -> str:
    claims: dict[str, str] = {"sub": sub}
    if email is not None:
        claims["email"] = email
    return jwt.encode(claims, private_pem, algorithm="RS256")


def _test_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/whoami")
    async def whoami(user: security.User = Depends(security.get_current_user)) -> dict[str, str]:
        return {"id": str(user.id), "clerk_user_id": user.clerk_user_id}

    return app


app = _test_app()


async def _get(headers: dict[str, str] | None = None) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        return await ac.get("/whoami", headers=headers)


async def test_valid_token_resolves_and_jit_creates_user(
    patched_jwk_client: None, rsa_keys: tuple[bytes, bytes]
) -> None:
    private_pem, _ = rsa_keys
    clerk_user_id = f"user_test_{uuid.uuid4().hex}"
    token = _make_token(private_pem, sub=clerk_user_id)

    try:
        first = await _get({"Authorization": f"Bearer {token}"})
        assert first.status_code == 200
        assert first.json()["clerk_user_id"] == clerk_user_id

        # second call resolves the same row rather than creating another
        second = await _get({"Authorization": f"Bearer {token}"})
        assert second.status_code == 200
        assert second.json()["id"] == first.json()["id"]
    finally:
        async with async_session_factory() as db:
            await db.execute(User.__table__.delete().where(User.clerk_user_id == clerk_user_id))
            await db.commit()


async def test_missing_token_is_401() -> None:
    response = await _get()
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


async def test_invalid_signature_is_401(patched_jwk_client: None) -> None:
    wrong_private_pem, _ = _pem_pair()
    token = _make_token(wrong_private_pem, sub="user_someone")

    response = await _get({"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
