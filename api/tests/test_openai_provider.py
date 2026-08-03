"""M8 — the OpenAI boundary.

No network and no spend: httpx's MockTransport serves every response. Nothing under `tests/` is
allowed to reach the real API.
"""

import json
from typing import Any

import httpx
import pytest

from receptenapp.core.errors import ImportErrorCode, ImportFailedError
from receptenapp.providers.openai import HttpxChatCompleter

MINIMAL_RESULT = {"found": True, "title": "Snert"}


def completer_for(handler: object) -> HttpxChatCompleter:
    completer = HttpxChatCompleter("sk-test")
    completer._client = httpx.AsyncClient(  # noqa: SLF001 — swapping transport is the point
        transport=httpx.MockTransport(handler)  # type: ignore[arg-type]
    )
    return completer


def completion(content: str, *, finish_reason: str = "stop") -> dict[str, Any]:
    return {
        "choices": [{"finish_reason": finish_reason, "message": {"content": content}}],
        "usage": {"prompt_tokens": 1200, "completion_tokens": 400},
    }


async def call(completer: HttpxChatCompleter) -> dict[str, Any]:
    return await completer.complete_json(
        model="gpt-4.1-mini",
        system="system",
        user="user",
        json_schema={"type": "object"},
        schema_name="recipe_synthesis",
        max_output_tokens=2400,
    )


async def test_returns_the_parsed_json_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=completion(json.dumps(MINIMAL_RESULT)))

    assert await call(completer_for(handler)) == MINIMAL_RESULT


async def test_sends_a_strict_schema_and_the_token_cap() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(200, json=completion(json.dumps(MINIMAL_RESULT)))

    await call(completer_for(handler))

    assert captured["response_format"]["json_schema"]["strict"] is True
    assert captured["max_tokens"] == 2400
    # Two imports of the same URL must not disagree about what the source said.
    assert captured["temperature"] == 0


async def test_a_generation_cut_off_at_the_cap_is_not_a_parse_error() -> None:
    """`finish_reason: length` leaves JSON truncated mid-object.

    Reported as its own failure because "too long to process" and "the model returned nonsense"
    owe the user different answers.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        truncated = completion('{"found": true, "ingredi', finish_reason="length")
        return httpx.Response(200, json=truncated)

    with pytest.raises(ImportFailedError) as caught:
        await call(completer_for(handler))

    assert caught.value.error_code is ImportErrorCode.model_failed
    assert (caught.value.details or {})["reason"] == "max_tokens_reached"


async def test_rate_limiting_says_to_try_again() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "slow down"}})

    with pytest.raises(ImportFailedError) as caught:
        await call(completer_for(handler))

    assert caught.value.error_code is ImportErrorCode.model_failed
    assert (caught.value.details or {})["reason"] == "openai_rate_limited"


async def test_a_4xx_keeps_the_body_for_diagnosis() -> None:
    """A bad schema keyword and a revoked key are both 400s. The body is what separates them."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": {"message": "Invalid schema: maxLength"}})

    with pytest.raises(ImportFailedError) as caught:
        await call(completer_for(handler))

    assert "maxLength" in (caught.value.details or {})["body"]


async def test_a_refusal_is_surfaced_rather_than_parsed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"finish_reason": "stop", "message": {"content": "", "refusal": "I cannot"}}
                ]
            },
        )

    with pytest.raises(ImportFailedError) as caught:
        await call(completer_for(handler))

    assert (caught.value.details or {})["refusal"] == "I cannot"


async def test_non_json_content_fails_at_the_boundary() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=completion("dit is geen json"))

    with pytest.raises(ImportFailedError) as caught:
        await call(completer_for(handler))

    assert caught.value.error_code is ImportErrorCode.model_failed


async def test_a_json_array_is_rejected_not_coerced() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=completion("[]"))

    with pytest.raises(ImportFailedError) as caught:
        await call(completer_for(handler))

    assert (caught.value.details or {})["payload_type"] == "list"


async def test_a_timeout_is_a_timeout_not_a_model_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("too slow", request=request)

    with pytest.raises(ImportFailedError) as caught:
        await call(completer_for(handler))

    assert caught.value.error_code is ImportErrorCode.timeout


def test_an_empty_key_fails_at_construction() -> None:
    # Better here than as a 401 three layers into an import the user is watching.
    with pytest.raises(ValueError):
        HttpxChatCompleter("")
