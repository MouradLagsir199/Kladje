"""Apify — how we get a transcript out of TikTok, Instagram and YouTube.

We do not download or transcribe video ourselves. Apify runs an actor per platform and hands back
a transcript plus metadata, which removes ffmpeg, media downloads and a third of the per-import
cost from the pipeline entirely (docs/03-import-pipeline.md).

Uses Apify's `run-sync-get-dataset-items` endpoint: start the actor, wait, get the rows, in one
request. Polling a run to completion by hand buys nothing here and is more to get wrong.

Behind a Protocol so normalisers and the import service can be tested against saved payloads
instead of paid calls.
"""

import asyncio
from typing import Any, Protocol

import httpx

from receptenapp.core.errors import ImportErrorCode, ImportFailedError

APIFY_BASE_URL = "https://api.apify.com/v2"

# docs/03 gives the actor 45s. The HTTP read timeout sits a little above it so that an actor that
# overruns is reported by Apify as its own timeout, rather than us guessing from a dropped socket.
_HTTP_TIMEOUT_MARGIN_SECONDS = 10.0


class ActorRunner(Protocol):
    async def run_actor(
        self, actor_id: str, run_input: dict[str, Any], *, timeout_seconds: int
    ) -> list[dict[str, Any]]: ...


class HttpxActorRunner:
    """The real client. One `httpx.AsyncClient` per instance so connections are reused."""

    def __init__(self, token: str, *, base_url: str = APIFY_BASE_URL) -> None:
        if not token:
            raise ValueError("APIFY_TOKEN is niet gezet.")
        self._token = token
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))

    async def aclose(self) -> None:
        await self._client.aclose()

    async def run_actor(
        self, actor_id: str, run_input: dict[str, Any], *, timeout_seconds: int
    ) -> list[dict[str, Any]]:
        if not actor_id:
            raise ImportFailedError(
                ImportErrorCode.unsupported_url,
                "Voor dit platform is geen importer ingesteld.",
            )

        url = f"{self._base_url}/acts/{actor_id}/run-sync-get-dataset-items"
        try:
            response = await self._client.post(
                url,
                params={"token": self._token, "timeout": timeout_seconds},
                json=run_input,
                timeout=httpx.Timeout(timeout_seconds + _HTTP_TIMEOUT_MARGIN_SECONDS),
            )
        except httpx.TimeoutException as exc:
            raise ImportFailedError(
                ImportErrorCode.timeout, "Het ophalen van de video duurde te lang."
            ) from exc
        except httpx.HTTPError as exc:
            raise ImportFailedError(
                ImportErrorCode.scraper_failed, "We konden de video nu niet ophalen."
            ) from exc

        # 408/504 mean the actor itself ran out of time — a different problem to it erroring.
        if response.status_code in (408, 504):
            raise ImportFailedError(
                ImportErrorCode.timeout, "Het ophalen van de video duurde te lang."
            )
        if response.status_code == 402:
            # Out of Apify credit. Not the user's fault and not retryable by them.
            raise ImportFailedError(
                ImportErrorCode.scraper_failed,
                "Importeren is tijdelijk niet beschikbaar.",
                details={"reason": "apify_payment_required"},
            )
        if response.status_code >= 400:
            raise ImportFailedError(
                ImportErrorCode.scraper_failed,
                "We konden de video nu niet ophalen.",
                details={"status_code": response.status_code},
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise ImportFailedError(
                ImportErrorCode.scraper_failed, "Onverwacht antwoord bij het ophalen."
            ) from exc

        if not isinstance(payload, list):
            raise ImportFailedError(
                ImportErrorCode.scraper_failed,
                "Onverwacht antwoord bij het ophalen.",
                details={"payload_type": type(payload).__name__},
            )
        return [row for row in payload if isinstance(row, dict)]


class StubActorRunner:
    """Returns canned payloads. Used by tests and by the offline import script."""

    def __init__(self, payloads: dict[str, list[dict[str, Any]]]) -> None:
        self._payloads = payloads
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def run_actor(
        self, actor_id: str, run_input: dict[str, Any], *, timeout_seconds: int
    ) -> list[dict[str, Any]]:
        self.calls.append((actor_id, run_input))
        await asyncio.sleep(0)
        return self._payloads.get(actor_id, [])
