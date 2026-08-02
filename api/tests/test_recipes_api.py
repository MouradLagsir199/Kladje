"""M13 — the two endpoints the library and detail screens read from."""

import uuid
from types import SimpleNamespace

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import select

from receptenapp.core import security
from receptenapp.db.models import (
    Provenance,
    Recipe,
    RecipeIngredient,
    RecipeStep,
    SourcePlatform,
    Unit,
    User,
)
from receptenapp.db.session import async_session_factory
from receptenapp.main import app


def _pem_pair() -> tuple[bytes, bytes]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return (
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ),
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ),
    )


@pytest.fixture(scope="module")
def rsa_keys() -> tuple[bytes, bytes]:
    return _pem_pair()


@pytest.fixture
def patched_jwk_client(monkeypatch: pytest.MonkeyPatch, rsa_keys: tuple[bytes, bytes]) -> None:
    _, public_pem = rsa_keys
    monkeypatch.setattr(
        security,
        "_get_jwk_client",
        lambda: SimpleNamespace(
            get_signing_key_from_jwt=lambda token: SimpleNamespace(key=public_pem)
        ),
    )


def _token(private_pem: bytes, clerk_user_id: str) -> str:
    return jwt.encode({"sub": clerk_user_id}, private_pem, algorithm="RS256")


async def _request(method: str, path: str, *, token: str | None = None) -> httpx.Response:
    headers = {"Authorization": f"Bearer {token}"} if token else None
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        return await ac.request(method, path, headers=headers)


async def _user_id(clerk_user_id: str) -> uuid.UUID:
    async with async_session_factory() as db:
        result = await db.execute(select(User).where(User.clerk_user_id == clerk_user_id))
        return result.scalar_one().id


async def _seed_recipe(user_id: uuid.UUID) -> uuid.UUID:
    """A carbonara with one converted ingredient and two steps, written straight to the database.

    Deliberately not via the import pipeline: this test is about the read endpoints, and going
    through synthesis would make it depend on a paid API.
    """
    async with async_session_factory() as db:
        recipe = Recipe(
            user_id=user_id,
            title="Pasta carbonara",
            servings=2,
            prep_minutes=10,
            cook_minutes=15,
            source_platform=SourcePlatform.tiktok,
            source_author="chefkoen",
            source_url="https://www.tiktok.com/@chefkoen/video/123",
        )
        db.add(recipe)
        await db.flush()

        db.add_all(
            [
                RecipeIngredient(
                    recipe_id=recipe.id,
                    position=1,
                    amount=200,
                    unit=Unit.g,
                    name_nl="spaghetti",
                    raw_text="200 g spaghetti",
                    provenance=Provenance.explicit,
                ),
                RecipeIngredient(
                    recipe_id=recipe.id,
                    position=0,
                    amount=125,
                    unit=Unit.g,
                    name_nl="bloem",
                    raw_text="1 cup flour",
                    original_amount=1,
                    original_unit="cup",
                    provenance=Provenance.derived,
                ),
            ]
        )
        db.add_all(
            [
                RecipeStep(recipe_id=recipe.id, position=1, text_="Bak de spek uit."),
                RecipeStep(
                    recipe_id=recipe.id, position=0, text_="Kook de pasta.", timer_seconds=600
                ),
            ]
        )
        await db.commit()
        return recipe.id


async def _cleanup(clerk_user_id: str) -> None:
    async with async_session_factory() as db:
        await db.execute(User.__table__.delete().where(User.clerk_user_id == clerk_user_id))
        await db.commit()


async def test_list_returns_only_your_own_recipes(
    patched_jwk_client: None, rsa_keys: tuple[bytes, bytes]
) -> None:
    private_pem, _ = rsa_keys
    mine = f"user_test_{uuid.uuid4().hex}"
    theirs = f"user_test_{uuid.uuid4().hex}"

    try:
        await _request("GET", "/v1/me", token=_token(private_pem, mine))
        await _request("GET", "/v1/me", token=_token(private_pem, theirs))
        await _seed_recipe(await _user_id(mine))
        await _seed_recipe(await _user_id(theirs))

        response = await _request("GET", "/v1/recipes", token=_token(private_pem, mine))

        assert response.status_code == 200
        # Two recipes exist; exactly one of them is this caller's.
        assert len(response.json()["items"]) == 1
    finally:
        await _cleanup(mine)
        await _cleanup(theirs)


async def test_detail_returns_children_in_position_order(
    patched_jwk_client: None, rsa_keys: tuple[bytes, bytes]
) -> None:
    private_pem, _ = rsa_keys
    clerk_user_id = f"user_test_{uuid.uuid4().hex}"
    token = _token(private_pem, clerk_user_id)

    try:
        await _request("GET", "/v1/me", token=token)
        recipe_id = await _seed_recipe(await _user_id(clerk_user_id))

        response = await _request("GET", f"/v1/recipes/{recipe_id}", token=token)

        assert response.status_code == 200
        body = response.json()
        assert body["title"] == "Pasta carbonara"
        assert body["source_author"] == "chefkoen"
        # Both were inserted with position 1 first; the endpoint must not return insertion order.
        assert [i["name_nl"] for i in body["ingredients"]] == ["bloem", "spaghetti"]
        assert [s["text"] for s in body["steps"]] == ["Kook de pasta.", "Bak de spek uit."]
    finally:
        await _cleanup(clerk_user_id)


async def test_detail_carries_provenance_and_the_original_unit(
    patched_jwk_client: None, rsa_keys: tuple[bytes, bytes]
) -> None:
    private_pem, _ = rsa_keys
    clerk_user_id = f"user_test_{uuid.uuid4().hex}"
    token = _token(private_pem, clerk_user_id)

    try:
        await _request("GET", "/v1/me", token=token)
        recipe_id = await _seed_recipe(await _user_id(clerk_user_id))

        body = (await _request("GET", f"/v1/recipes/{recipe_id}", token=token)).json()
        converted = body["ingredients"][0]

        # A converted value is `derived`, never `explicit` — the dot and the "1 cup" caption on the
        # detail screen both come from these two fields.
        assert converted["provenance"] == "derived"
        assert converted["original_unit"] == "cup"
    finally:
        await _cleanup(clerk_user_id)


async def test_someone_elses_recipe_is_404_not_403(
    patched_jwk_client: None, rsa_keys: tuple[bytes, bytes]
) -> None:
    private_pem, _ = rsa_keys
    mine = f"user_test_{uuid.uuid4().hex}"
    theirs = f"user_test_{uuid.uuid4().hex}"

    try:
        await _request("GET", "/v1/me", token=_token(private_pem, mine))
        await _request("GET", "/v1/me", token=_token(private_pem, theirs))
        their_recipe = await _seed_recipe(await _user_id(theirs))

        response = await _request(
            "GET", f"/v1/recipes/{their_recipe}", token=_token(private_pem, mine)
        )

        # 403 would confirm the id exists. 404 says nothing either way.
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"
    finally:
        await _cleanup(mine)
        await _cleanup(theirs)


async def test_list_without_token_is_401() -> None:
    response = await _request("GET", "/v1/recipes")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
