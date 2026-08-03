"""OpenAI — the one call that turns evidence into a recipe.

Raw `httpx` against the REST API rather than the `openai` package, matching `providers/apify.py`.
One request, one response, a schema we control; the SDK's retry and streaming machinery buys
nothing here and its version churn would be one more thing to track.

Behind a Protocol (ADR-005) so every layer above can be tested against a saved completion instead
of a paid call. Nothing in `tests/` may reach this class.

Cost control lives in three places, none of them here:
  - `EvidenceBundle.truncated()` caps what goes in — a 20-minute transcript is the real bill.
  - `EvidenceBundle.is_too_thin_to_synthesise()` refuses to call at all on evidence that could
    only produce guesses.
  - `PromptSet.max_output_tokens` caps what comes back.
This module only enforces the last one, because it is the only one that is an API parameter.
"""

import json
from typing import Any, Protocol

import httpx

from receptenapp.core.errors import ImportErrorCode, ImportFailedError

OPENAI_BASE_URL = "https://api.openai.com/v1"

# Generation is slow and a recipe is not short. Well above p99, below the point where a user has
# already given up and closed the app.
_REQUEST_TIMEOUT_SECONDS = 90.0


class ChatCompleter(Protocol):
    """Structured completion, narrowed to exactly what synthesis needs."""

    async def complete_json(
        self,
        *,
        model: str,
        system: str,
        user: str,
        json_schema: dict[str, Any],
        schema_name: str,
        max_output_tokens: int,
    ) -> dict[str, Any]: ...


class HttpxChatCompleter:
    def __init__(self, api_key: str, *, base_url: str = OPENAI_BASE_URL) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is niet gezet.")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(_REQUEST_TIMEOUT_SECONDS))

    async def aclose(self) -> None:
        await self._client.aclose()

    async def complete_json(
        self,
        *,
        model: str,
        system: str,
        user: str,
        json_schema: dict[str, Any],
        schema_name: str,
        max_output_tokens: int,
    ) -> dict[str, Any]:
        body = {
            "model": model,
            # Deterministic as the API allows. Two imports of the same URL should not disagree
            # about whether the source stated a serving count.
            "temperature": 0,
            "max_tokens": max_output_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": schema_name, "strict": True, "schema": json_schema},
            },
        }

        try:
            response = await self._client.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=body,
            )
        except httpx.TimeoutException as exc:
            raise ImportFailedError(
                ImportErrorCode.timeout, "Het uitlezen van het recept duurde te lang."
            ) from exc
        except httpx.HTTPError as exc:
            raise ImportFailedError(
                ImportErrorCode.model_failed, "We konden het recept nu niet uitlezen."
            ) from exc

        if response.status_code == 429:
            raise ImportFailedError(
                ImportErrorCode.model_failed,
                "Even te druk. Probeer het over een minuut opnieuw.",
                details={"reason": "openai_rate_limited"},
            )
        if response.status_code >= 400:
            # The body carries the real reason (bad schema keyword, revoked key, no credit) and is
            # worth keeping: without it a 400 here is indistinguishable from a 400 there.
            raise ImportFailedError(
                ImportErrorCode.model_failed,
                "We konden het recept nu niet uitlezen.",
                details={"status_code": response.status_code, "body": response.text[:400]},
            )

        payload = response.json()
        choices = payload.get("choices") or []
        if not choices:
            raise ImportFailedError(
                ImportErrorCode.model_failed, "Onverwacht antwoord bij het uitlezen."
            )

        choice = choices[0]
        # A generation cut off at the token cap yields JSON that is truncated mid-object. Caught
        # here rather than as a parse error, because "the recipe was too long" and "the model
        # returned nonsense" need different answers.
        if choice.get("finish_reason") == "length":
            raise ImportFailedError(
                ImportErrorCode.model_failed,
                "Dit recept is te lang om automatisch te verwerken.",
                details={"reason": "max_tokens_reached", "limit": max_output_tokens},
            )

        content = (choice.get("message") or {}).get("content")
        if not isinstance(content, str) or not content.strip():
            # `refusal` is a separate field from `content`; a refusal leaves content empty.
            raise ImportFailedError(
                ImportErrorCode.model_failed,
                "Onverwacht antwoord bij het uitlezen.",
                details={"refusal": ((choice.get("message") or {}).get("refusal") or "")[:200]},
            )

        try:
            parsed = json.loads(content)
        except ValueError as exc:
            raise ImportFailedError(
                ImportErrorCode.model_failed, "Onverwacht antwoord bij het uitlezen."
            ) from exc

        if not isinstance(parsed, dict):
            raise ImportFailedError(
                ImportErrorCode.model_failed,
                "Onverwacht antwoord bij het uitlezen.",
                details={"payload_type": type(parsed).__name__},
            )
        return parsed


class StubChatCompleter:
    """Returns a canned completion. Used by tests and by the offline import script."""

    def __init__(self, result: dict[str, Any]) -> None:
        self._result = result
        self.calls: list[dict[str, Any]] = []

    async def complete_json(
        self,
        *,
        model: str,
        system: str,
        user: str,
        json_schema: dict[str, Any],
        schema_name: str,
        max_output_tokens: int,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "model": model,
                "system": system,
                "user": user,
                "max_output_tokens": max_output_tokens,
            }
        )
        return self._result
