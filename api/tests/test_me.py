import uuid
from types import SimpleNamespace

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from receptenapp.core import security
from receptenapp.db.models import User
from receptenapp.db.session import async_session_factory
from receptenapp.main import app


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


def _make_token(private_pem: bytes, *, sub: str, email: str | None = "me@example.com") -> str:
    claims: dict[str, str] = {"sub": sub}
    if email is not None:
        claims["email"] = email
    return jwt.encode(claims, private_pem, algorithm="RS256")


async def _request(
    method: str, path: str, *, token: str | None = None, json: dict | None = None
) -> httpx.Response:
    headers = {"Authorization": f"Bearer {token}"} if token else None
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        return await ac.request(method, path, headers=headers, json=json)


async def _cleanup(clerk_user_id: str) -> None:
    async with async_session_factory() as db:
        await db.execute(User.__table__.delete().where(User.clerk_user_id == clerk_user_id))
        await db.commit()


async def test_get_me_happy_path(patched_jwk_client: None, rsa_keys: tuple[bytes, bytes]) -> None:
    private_pem, _ = rsa_keys
    clerk_user_id = f"user_test_{uuid.uuid4().hex}"
    token = _make_token(private_pem, sub=clerk_user_id)

    try:
        response = await _request("GET", "/v1/me", token=token)

        assert response.status_code == 200
        body = response.json()
        assert body["user"]["email"] == "me@example.com"
        assert body["user"]["household_size"] == 2
        assert body["preferences"]["default_servings"] == 2
        assert body["preferences"]["diets"] == []
        assert body["quota"] == {"used": 0, "limit": 10, "resets_at": None, "tier": "free"}
    finally:
        await _cleanup(clerk_user_id)


async def test_patch_me_updates_profile_and_persists(
    patched_jwk_client: None, rsa_keys: tuple[bytes, bytes]
) -> None:
    private_pem, _ = rsa_keys
    clerk_user_id = f"user_test_{uuid.uuid4().hex}"
    token = _make_token(private_pem, sub=clerk_user_id)

    try:
        await _request("GET", "/v1/me", token=token)  # JIT-create the user first

        patch_response = await _request(
            "PATCH",
            "/v1/me",
            token=token,
            json={"display_name": "Mourad", "household_size": 4},
        )
        assert patch_response.status_code == 200
        assert patch_response.json()["display_name"] == "Mourad"
        assert patch_response.json()["household_size"] == 4

        follow_up = await _request("GET", "/v1/me", token=token)
        assert follow_up.json()["user"]["display_name"] == "Mourad"
        assert follow_up.json()["user"]["household_size"] == 4
    finally:
        await _cleanup(clerk_user_id)


async def test_patch_preferences_updates_and_persists(
    patched_jwk_client: None, rsa_keys: tuple[bytes, bytes]
) -> None:
    private_pem, _ = rsa_keys
    clerk_user_id = f"user_test_{uuid.uuid4().hex}"
    token = _make_token(private_pem, sub=clerk_user_id)

    try:
        await _request("GET", "/v1/me", token=token)  # JIT-create the user first

        patch_response = await _request(
            "PATCH",
            "/v1/me/preferences",
            token=token,
            json={"diets": ["vegetarisch"], "notif_defrost": False},
        )
        assert patch_response.status_code == 200
        assert patch_response.json()["diets"] == ["vegetarisch"]
        assert patch_response.json()["notif_defrost"] is False

        follow_up = await _request("GET", "/v1/me", token=token)
        assert follow_up.json()["preferences"]["diets"] == ["vegetarisch"]
        assert follow_up.json()["preferences"]["notif_defrost"] is False
    finally:
        await _cleanup(clerk_user_id)


async def test_get_me_without_token_is_401() -> None:
    response = await _request("GET", "/v1/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
