"""Fetching, and the ways a stranger's URL goes wrong.

No network: httpx's MockTransport serves the responses, so these run in CI and cost nothing.
"""

import httpx
import pytest

from receptenapp.core.errors import ImportErrorCode, ImportFailedError
from receptenapp.providers.http import HttpxPageFetcher
from receptenapp.services.blog_extract import fetch_and_extract

RECIPE_HTML = """
<html><head><title>Snert</title></head><body>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Recipe","name":"Snert",
 "recipeIngredient":["500 g spliterwten","1 prei","1 rookworst"],
 "recipeInstructions":[{"@type":"HowToStep","text":"Week de erwten."},
                       {"@type":"HowToStep","text":"Kook alles gaar."}]}
</script></body></html>
"""


def fetcher_for(handler: object, **kwargs: object) -> HttpxPageFetcher:
    fetcher = HttpxPageFetcher(**kwargs)  # type: ignore[arg-type]
    fetcher._client = httpx.AsyncClient(  # noqa: SLF001 — swapping transport is the point
        transport=httpx.MockTransport(handler),  # type: ignore[arg-type]
        follow_redirects=True,
    )
    return fetcher


@pytest.mark.asyncio
async def test_fetches_and_extracts_a_recipe() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, html=RECIPE_HTML)

    bundle = await fetch_and_extract("https://blog.test/snert", fetcher_for(handler))
    assert (bundle.structured or {})["name"] == "Snert"
    assert len(bundle.structured["recipeIngredient"]) == 3  # type: ignore[index]


@pytest.mark.asyncio
async def test_url_norm_follows_the_redirect_destination() -> None:
    """A page reached through a redirect must be keyed on where it landed, not where it started."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/short":
            return httpx.Response(301, headers={"Location": "https://blog.test/echte-snert/"})
        return httpx.Response(200, html=RECIPE_HTML)

    bundle = await fetch_and_extract("https://blog.test/short", fetcher_for(handler))
    assert bundle.url_norm == "https://blog.test/echte-snert"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (404, ImportErrorCode.private_or_removed),
        (410, ImportErrorCode.private_or_removed),
        (403, ImportErrorCode.private_or_removed),
        (500, ImportErrorCode.scraper_failed),
        (503, ImportErrorCode.scraper_failed),
    ],
)
async def test_http_errors_map_to_taxonomy_codes(status: int, expected: ImportErrorCode) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status)

    with pytest.raises(ImportFailedError) as exc:
        await fetcher_for(handler).fetch("https://blog.test/x")
    assert exc.value.error_code is expected


@pytest.mark.asyncio
async def test_non_html_is_rejected_before_downloading_it() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"%PDF-1.4", headers={"content-type": "application/pdf"})

    with pytest.raises(ImportFailedError) as exc:
        await fetcher_for(handler).fetch("https://blog.test/recept.pdf")
    assert exc.value.error_code is ImportErrorCode.unsupported_url


@pytest.mark.asyncio
async def test_enormous_page_is_abandoned_rather_than_buffered() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x" * 4000, headers={"content-type": "text/html"})

    with pytest.raises(ImportFailedError) as exc:
        await fetcher_for(handler, max_bytes=1000).fetch("https://blog.test/huge")
    assert exc.value.error_code is ImportErrorCode.media_too_large


@pytest.mark.asyncio
async def test_timeout_is_its_own_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("too slow", request=request)

    with pytest.raises(ImportFailedError) as exc:
        await fetcher_for(handler).fetch("https://blog.test/slow")
    assert exc.value.error_code is ImportErrorCode.timeout


@pytest.mark.asyncio
async def test_connection_failure_is_not_a_crash() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    with pytest.raises(ImportFailedError) as exc:
        await fetcher_for(handler).fetch("https://nope.test/x")
    assert exc.value.error_code is ImportErrorCode.scraper_failed


@pytest.mark.asyncio
async def test_mislabelled_encoding_degrades_instead_of_raising() -> None:
    # A page claiming utf-8 while serving latin-1 must still yield usable text.
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content="<html><body>caf\xe9 crème".encode("latin-1"),
            headers={"content-type": "text/html; charset=utf-8"},
        )

    page = await fetcher_for(handler).fetch("https://blog.test/x")
    assert "caf" in page.html


@pytest.mark.asyncio
async def test_shortener_resolution_returns_the_destination() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "vm.tiktok.com":
            return httpx.Response(
                301, headers={"Location": "https://www.tiktok.com/@kok/video/123"}
            )
        return httpx.Response(200)

    resolved = await fetcher_for(handler).resolve_redirect("https://vm.tiktok.com/ZMabc/")
    assert resolved == "https://www.tiktok.com/@kok/video/123"


@pytest.mark.asyncio
async def test_shortener_failure_falls_back_to_the_original_url() -> None:
    # Losing an import because a shortener was down is the worse trade.
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    original = "https://vm.tiktok.com/ZMabc/"
    assert await fetcher_for(handler).resolve_redirect(original) == original
