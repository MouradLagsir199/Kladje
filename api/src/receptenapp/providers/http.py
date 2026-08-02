"""Fetching a web page — the only place the import pipeline touches the open internet.

Behind an interface so the pipeline can be tested without network access, and so the whole thing
can be swapped for a proxying fetcher later without touching a service.

Everything here is defensive about one thing: a URL comes from a user, and points at a server we
know nothing about. It may be slow, enormous, not HTML at all, or gone.
"""

from dataclasses import dataclass
from typing import Protocol

import httpx

from receptenapp.core.errors import ImportErrorCode, ImportFailedError

# A browser UA. Plenty of sites serve a bot page or a 403 to anything that looks scripted, and
# this is a single request the user explicitly asked for, on a page they are already looking at.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

DEFAULT_TIMEOUT_SECONDS = 15.0
# Recipe pages are big — half a megabyte was typical across our fixtures — but nothing legitimate
# is 20 MB. The cap exists so one bad URL cannot exhaust the container's memory.
MAX_PAGE_BYTES = 5_000_000

_HTML_CONTENT_TYPES = ("text/html", "application/xhtml+xml", "text/plain")


@dataclass(frozen=True)
class FetchedPage:
    """`url` is the URL after redirects, which is not always the one asked for."""

    url: str
    html: str
    status_code: int


class PageFetcher(Protocol):
    async def fetch(self, url: str) -> FetchedPage: ...

    async def resolve_redirect(self, url: str) -> str: ...


class HttpxPageFetcher:
    """The real implementation. One client per instance so connections are reused."""

    def __init__(
        self,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_bytes: int = MAX_PAGE_BYTES,
        user_agent: str = USER_AGENT,
    ) -> None:
        self._max_bytes = max_bytes
        self._client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout_seconds,
            headers={
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
            },
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def fetch(self, url: str) -> FetchedPage:
        try:
            async with self._client.stream("GET", url) as response:
                if response.status_code in (401, 403, 404, 410):
                    raise ImportFailedError(
                        ImportErrorCode.private_or_removed,
                        "Deze pagina is niet meer beschikbaar.",
                        details={"status_code": response.status_code},
                    )
                if response.status_code >= 400:
                    raise ImportFailedError(
                        ImportErrorCode.scraper_failed,
                        "De website reageerde niet zoals verwacht.",
                        details={"status_code": response.status_code},
                    )

                content_type = response.headers.get("content-type", "").lower()
                if content_type and not content_type.startswith(_HTML_CONTENT_TYPES):
                    raise ImportFailedError(
                        ImportErrorCode.unsupported_url,
                        "Deze link wijst niet naar een webpagina.",
                        details={"content_type": content_type},
                    )

                # Read incrementally so an enormous response is abandoned rather than buffered.
                chunks: list[bytes] = []
                total = 0
                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > self._max_bytes:
                        raise ImportFailedError(
                            ImportErrorCode.media_too_large,
                            "Deze pagina is te groot om te verwerken.",
                            details={"max_bytes": self._max_bytes},
                        )
                    chunks.append(chunk)

                body = b"".join(chunks)
                # charset_normalizer via httpx handles the declared charset; a page that lies about
                # its encoding should still yield mostly-readable text rather than blowing up.
                encoding = response.charset_encoding or "utf-8"
                html = body.decode(encoding, errors="replace")
                return FetchedPage(
                    url=str(response.url), html=html, status_code=response.status_code
                )

        except httpx.TimeoutException as exc:
            raise ImportFailedError(
                ImportErrorCode.timeout, "De website reageerde te traag."
            ) from exc
        except httpx.HTTPError as exc:
            raise ImportFailedError(
                ImportErrorCode.scraper_failed, "We konden deze pagina niet ophalen."
            ) from exc

    async def resolve_redirect(self, url: str) -> str:
        """Follow a shortener to its destination without downloading the page.

        Satisfies `services.url_norm.RedirectResolver`. HEAD is enough and costs nothing; some
        shorteners refuse it, so fall back to a GET whose body we never read.
        """
        try:
            response = await self._client.head(url)
            if response.status_code >= 400:
                async with self._client.stream("GET", url) as streamed:
                    return str(streamed.url)
            return str(response.url)
        except httpx.HTTPError:
            # Not fatal: the caller falls back to the unresolved URL, which is still a valid key.
            return url
