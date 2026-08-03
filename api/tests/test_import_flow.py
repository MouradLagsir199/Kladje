"""M11 + M12 — an import from pasted link to saved recipe.

Every external boundary is stubbed, so this never spends a cent: the page fetcher serves HTML from
memory and the completer returns a canned recipe. The pipeline itself is real, including the
background task, the event rows and the validation pass.
"""

import uuid
from types import SimpleNamespace
from typing import Any

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import select

from receptenapp.core import security
from receptenapp.db.models import Import, ImportStatus, Recipe, User
from receptenapp.db.session import async_session_factory
from receptenapp.main import app
from receptenapp.providers.openai import StubChatCompleter
from receptenapp.services import imports as imports_service

RECIPE_HTML = """
<html><head><title>Snert</title></head><body>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Recipe","name":"Snert",
 "author":{"@type":"Person","name":"Oma"},
 "recipeIngredient":["500 g spliterwten","1 prei","1 rookworst"],
 "recipeInstructions":[{"@type":"HowToStep","text":"Week de erwten een nacht."},
                       {"@type":"HowToStep","text":"Kook alles gaar."}]}
</script></body></html>
"""

COMPLETION: dict[str, Any] = {
    "found": True,
    "confidence": "high",
    "title": "Snert",
    "description": "Stevige Hollandse erwtensoep.",
    "meal_types": ["diner"],
    "servings": 4,
    "prep_minutes": 20,
    "cook_minutes": 90,
    "difficulty": "makkelijk",
    "oven_c": None,
    "ingredients": [
        {
            "pos": 1,
            "section": None,
            "amount": 500,
            "amount_max": None,
            "unit": "g",
            "name_nl": "spliterwten",
            "qualifier": None,
            "category": "houdbaar",
            "optional": False,
            "raw": "500 g spliterwten",
            "orig_amount": None,
            "orig_unit": None,
            "prov": "explicit",
        },
        {
            "pos": 2,
            "section": None,
            "amount": 1,
            "amount_max": None,
            "unit": "stuk",
            "name_nl": "prei",
            "qualifier": None,
            "category": "groente_fruit",
            "optional": False,
            "raw": "1 prei",
            "orig_amount": None,
            "orig_unit": None,
            "prov": "explicit",
        },
    ],
    "steps": [
        {
            "pos": 1,
            "text": "Week de spliterwten een nacht in koud water.",
            "timer_seconds": None,
            "temperature_c": None,
            "ingredient_pos": [1],
            "prov": "explicit",
        },
        {
            "pos": 2,
            "text": "Kook de soep zachtjes gaar met de prei erin.",
            "timer_seconds": 5400,
            "temperature_c": None,
            "ingredient_pos": [1, 2],
            "prov": "explicit",
        },
    ],
    "field_provenance": {
        "title": "explicit",
        "servings": "explicit",
        "prep_minutes": "explicit",
        "cook_minutes": "explicit",
        "oven_c": "missing",
        "difficulty": "derived",
    },
    "missing": ["oven_c"],
}


def _pem_pair() -> tuple[bytes, bytes]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return (
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ),
        key.public_key().public_bytes(
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


@pytest.fixture
def stub_providers(monkeypatch: pytest.MonkeyPatch) -> StubChatCompleter:
    """Swap the three boundaries for stubs, for both the request and the background task."""
    completer = StubChatCompleter(COMPLETION)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, html=RECIPE_HTML)

    real_init = imports_service._Providers.__init__  # noqa: SLF001

    def fake_init(self: Any, config: Any) -> None:
        real_init(self, config)
        self.fetcher._client = httpx.AsyncClient(  # noqa: SLF001
            transport=httpx.MockTransport(handler), follow_redirects=True
        )
        self.completer = completer

    monkeypatch.setattr(imports_service._Providers, "__init__", fake_init)  # noqa: SLF001

    # The paste endpoint builds its own fetcher for shortener resolution.
    original_fetcher_init = imports_service.HttpxPageFetcher.__init__

    def fake_fetcher_init(self: Any, *args: Any, **kwargs: Any) -> None:
        original_fetcher_init(self, *args, **kwargs)
        self._client = httpx.AsyncClient(  # noqa: SLF001
            transport=httpx.MockTransport(handler), follow_redirects=True
        )

    monkeypatch.setattr("receptenapp.api.imports.HttpxPageFetcher.__init__", fake_fetcher_init)
    return completer


def _token(private_pem: bytes, clerk_user_id: str) -> str:
    return jwt.encode({"sub": clerk_user_id}, private_pem, algorithm="RS256")


async def _request(
    method: str, path: str, *, token: str | None = None, json: dict[str, Any] | None = None
) -> httpx.Response:
    headers = {"Authorization": f"Bearer {token}"} if token else None
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        return await ac.request(method, path, headers=headers, json=json)


async def _cleanup(clerk_user_id: str) -> None:
    async with async_session_factory() as db:
        await db.execute(User.__table__.delete().where(User.clerk_user_id == clerk_user_id))
        await db.commit()


@pytest.fixture
async def signed_in(patched_jwk_client: None, rsa_keys: tuple[bytes, bytes]) -> Any:
    """A fresh user, its token, and cleanup afterwards."""
    private_pem, _ = rsa_keys
    clerk_user_id = f"user_test_{uuid.uuid4().hex}"
    token = _token(private_pem, clerk_user_id)
    await _request("GET", "/v1/me", token=token)
    try:
        yield SimpleNamespace(clerk_user_id=clerk_user_id, token=token)
    finally:
        await _cleanup(clerk_user_id)


async def test_paste_a_link_and_get_a_saved_recipe(
    signed_in: Any, stub_providers: StubChatCompleter
) -> None:
    """The whole loop, which is the point of the MVP gate."""
    created = await _request(
        "POST", "/v1/imports", token=signed_in.token, json={"url": "https://blog.test/snert"}
    )
    # 202, not 201: the work is still running when this returns.
    assert created.status_code == 202
    import_id = created.json()["id"]

    # ASGITransport runs background tasks before the response is released, so by here it is done.
    polled = await _request("GET", f"/v1/imports/{import_id}", token=signed_in.token)
    body = polled.json()
    assert body["status"] == "ready_for_review"
    assert body["draft"]["recipe"]["title"] == "Snert"
    assert body["draft"]["source"]["author"] == "Oma"

    # Real stage rows, not a timer. This is what the progress screen renders.
    stages = [(event["stage"], event["state"]) for event in body["events"]]
    assert ("fetch", "done") in stages
    assert ("synthesize", "done") in stages
    assert ("validate", "done") in stages

    saved = await _request("POST", f"/v1/imports/{import_id}/save", token=signed_in.token)
    assert saved.status_code == 201
    recipe = saved.json()
    assert recipe["title"] == "Snert"
    assert [i["name_nl"] for i in recipe["ingredients"]] == ["spliterwten", "prei"]
    assert recipe["steps"][1]["timer_seconds"] == 5400
    # The provenance of the recipe's own fields survives the round trip through the draft.
    assert recipe["field_provenance"]["oven_c"] == "missing"

    listed = await _request("GET", "/v1/recipes", token=signed_in.token)
    assert [r["title"] for r in listed.json()["items"]] == ["Snert"]


async def test_nothing_reaches_the_library_before_save(
    signed_in: Any, stub_providers: StubChatCompleter
) -> None:
    """The draft lives in `imports.draft` on purpose — an abandoned import leaves no junk."""
    await _request(
        "POST", "/v1/imports", token=signed_in.token, json={"url": "https://blog.test/snert"}
    )
    listed = await _request("GET", "/v1/recipes", token=signed_in.token)
    assert listed.json()["items"] == []


async def test_step_ingredient_positions_become_real_ids(
    signed_in: Any, stub_providers: StubChatCompleter
) -> None:
    """Cook mode reads `ingredient_ids` directly; the model only ever knew positions."""
    created = await _request(
        "POST", "/v1/imports", token=signed_in.token, json={"url": "https://blog.test/snert"}
    )
    import_id = created.json()["id"]
    recipe = (await _request("POST", f"/v1/imports/{import_id}/save", token=signed_in.token)).json()

    by_name = {i["name_nl"]: i["id"] for i in recipe["ingredients"]}
    assert recipe["steps"][1]["ingredient_ids"] == [by_name["spliterwten"], by_name["prei"]]


async def test_a_review_edit_is_applied_and_revalidated(
    signed_in: Any, stub_providers: StubChatCompleter
) -> None:
    created = await _request(
        "POST", "/v1/imports", token=signed_in.token, json={"url": "https://blog.test/snert"}
    )
    import_id = created.json()["id"]

    patched = await _request(
        "PATCH",
        f"/v1/imports/{import_id}/draft",
        token=signed_in.token,
        json={"title": "Snert van oma", "servings": 6},
    )
    assert patched.status_code == 200
    assert patched.json()["draft"]["recipe"]["title"] == "Snert van oma"

    recipe = (await _request("POST", f"/v1/imports/{import_id}/save", token=signed_in.token)).json()
    assert recipe["title"] == "Snert van oma"
    assert recipe["servings"] == 6


async def test_a_hand_typed_serving_count_is_validated_too(
    signed_in: Any, stub_providers: StubChatCompleter
) -> None:
    """The review screen is where someone types 200 into a field.

    The same rules that guard model output have to guard hand-typed values, or the validation layer
    is only protecting against the one source that was already the most careful.
    """
    created = await _request(
        "POST", "/v1/imports", token=signed_in.token, json={"url": "https://blog.test/snert"}
    )
    import_id = created.json()["id"]

    patched = await _request(
        "PATCH", f"/v1/imports/{import_id}/draft", token=signed_in.token, json={"servings": 200}
    )
    assert patched.status_code == 200
    # Not believed, and not clamped to something that looks deliberate.
    assert patched.json()["draft"]["recipe"]["servings"] is None


async def test_saving_twice_returns_the_same_recipe(
    signed_in: Any, stub_providers: StubChatCompleter
) -> None:
    """A double-tap on Opslaan, or a retry after a dropped response, must not duplicate."""
    created = await _request(
        "POST", "/v1/imports", token=signed_in.token, json={"url": "https://blog.test/snert"}
    )
    import_id = created.json()["id"]

    first = await _request("POST", f"/v1/imports/{import_id}/save", token=signed_in.token)
    second = await _request("POST", f"/v1/imports/{import_id}/save", token=signed_in.token)

    assert first.json()["id"] == second.json()["id"]
    listed = await _request("GET", "/v1/recipes", token=signed_in.token)
    assert len(listed.json()["items"]) == 1


async def test_importing_the_same_url_twice_is_a_conflict(
    signed_in: Any, stub_providers: StubChatCompleter
) -> None:
    """Answered before anything is spent — the client shows "Je hebt dit recept al"."""
    created = await _request(
        "POST", "/v1/imports", token=signed_in.token, json={"url": "https://blog.test/snert"}
    )
    import_id = created.json()["id"]
    await _request("POST", f"/v1/imports/{import_id}/save", token=signed_in.token)

    again = await _request(
        "POST", "/v1/imports", token=signed_in.token, json={"url": "https://blog.test/snert"}
    )
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "conflict"


async def test_a_failed_import_does_not_count_against_quota(
    signed_in: Any, monkeypatch: pytest.MonkeyPatch, stub_providers: StubChatCompleter
) -> None:
    """It cost money on Apify and produced nothing usable. Charging for that is indefensible."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    def fake_init(self: Any, config: Any) -> None:
        self.fetcher = imports_service.HttpxPageFetcher()
        self.fetcher._client = httpx.AsyncClient(  # noqa: SLF001
            transport=httpx.MockTransport(handler)
        )
        self.runner = None
        self.completer = StubChatCompleter(COMPLETION)

    monkeypatch.setattr(imports_service._Providers, "__init__", fake_init)  # noqa: SLF001

    created = await _request(
        "POST", "/v1/imports", token=signed_in.token, json={"url": "https://blog.test/weg"}
    )
    import_id = created.json()["id"]

    body = (await _request("GET", f"/v1/imports/{import_id}", token=signed_in.token)).json()
    assert body["status"] == "failed"
    assert body["error_code"] == "private_or_removed"

    async with async_session_factory() as db:
        record = await db.get(Import, uuid.UUID(import_id))
        assert record is not None
        assert record.counted_against_quota is False


async def test_quota_is_refused_before_any_paid_call(
    signed_in: Any, monkeypatch: pytest.MonkeyPatch, stub_providers: StubChatCompleter
) -> None:
    """A CLAUDE.md non-negotiable: an over-quota import that already ran has already cost money."""
    monkeypatch.setattr(imports_service, "quota_used", lambda db, user_id: _ten())

    refused = await _request(
        "POST", "/v1/imports", token=signed_in.token, json={"url": "https://blog.test/snert"}
    )
    assert refused.status_code == 422
    assert refused.json()["error"]["code"] == "quota_exceeded"
    # Nothing was recorded, so nothing can be mistaken for an attempt in progress.
    async with async_session_factory() as db:
        rows = await db.execute(select(Recipe).where(Recipe.title == "Snert"))
        assert rows.scalars().first() is None


async def _ten() -> int:
    return 10


async def test_someone_elses_import_is_invisible(
    signed_in: Any,
    rsa_keys: tuple[bytes, bytes],
    stub_providers: StubChatCompleter,
) -> None:
    private_pem, _ = rsa_keys
    other = f"user_test_{uuid.uuid4().hex}"
    other_token = _token(private_pem, other)
    await _request("GET", "/v1/me", token=other_token)

    try:
        created = await _request(
            "POST", "/v1/imports", token=signed_in.token, json={"url": "https://blog.test/snert"}
        )
        import_id = created.json()["id"]

        seen = await _request("GET", f"/v1/imports/{import_id}", token=other_token)
        assert seen.status_code == 404
    finally:
        await _cleanup(other)


async def test_an_unsupported_link_is_rejected_with_its_own_code(
    signed_in: Any, stub_providers: StubChatCompleter
) -> None:
    refused = await _request(
        "POST",
        "/v1/imports",
        token=signed_in.token,
        json={"url": "https://www.pinterest.com/pin/123456789/"},
    )
    assert refused.status_code == 422
    assert refused.json()["error"]["code"] == "unsupported_url"


async def test_the_import_status_is_readable_the_whole_way_through(
    signed_in: Any, stub_providers: StubChatCompleter
) -> None:
    """A row exists from the moment the link is pasted, including on failure.

    A client that has to tell "still working" from "never started" needs something to poll.
    """
    created = await _request(
        "POST", "/v1/imports", token=signed_in.token, json={"url": "https://blog.test/snert"}
    )
    assert created.json()["status"] in {status.value for status in ImportStatus}
