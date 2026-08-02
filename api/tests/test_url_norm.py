"""Task 1.1 — the Stage 0 rule table from docs/03-import-pipeline.md.

No network: shorteners that need a live redirect are covered with a stub resolver.
"""

import pytest

from receptenapp.services.url_norm import (
    SourcePlatform,
    detect_platform,
    needs_redirect_resolution,
    normalise_url,
    normalise_url_async,
)

# (raw URL as a user might paste it, expected source_url_norm)
URL_PAIRS = [
    # --- TikTok ---
    (
        "https://www.tiktok.com/@chefkoen/video/7234567890123456789",
        "https://tiktok.com/@chefkoen/video/7234567890123456789",
    ),
    (
        "https://m.tiktok.com/@chefkoen/video/7234567890123456789?_t=8abc&_r=1",
        "https://tiktok.com/@chefkoen/video/7234567890123456789",
    ),
    (
        "https://www.tiktok.com/@chefkoen/video/7234567890123456789/",
        "https://tiktok.com/@chefkoen/video/7234567890123456789",
    ),
    (
        "https://www.tiktok.com/@chefkoen/video/7234567890123456789#recept",
        "https://tiktok.com/@chefkoen/video/7234567890123456789",
    ),
    (
        "HTTPS://WWW.TIKTOK.COM/@ChefKoen/video/7234567890123456789",
        "https://tiktok.com/@ChefKoen/video/7234567890123456789",
    ),
    # --- Instagram ---
    (
        "https://www.instagram.com/reel/CxYz123AbCd/?igsh=MzRlODBiNWFlZA==",
        "https://instagram.com/reel/CxYz123AbCd",
    ),
    ("https://instagram.com/reels/CxYz123AbCd", "https://instagram.com/reel/CxYz123AbCd"),
    ("https://www.instagram.com/tv/CxYz123AbCd/", "https://instagram.com/reel/CxYz123AbCd"),
    # /p/ is preserved: Instagram also serves photo posts there.
    ("https://www.instagram.com/p/CxYz123AbCd/", "https://instagram.com/p/CxYz123AbCd"),
    (
        "https://l.instagram.com/?u=https%3A%2F%2Fwww.leukerecepten.nl%2Fpasta%2F&e=AT0",
        "https://leukerecepten.nl/pasta",
    ),
    # --- YouTube ---
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "https://youtube.com/watch?v=dQw4w9WgXcQ"),
    (
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ&feature=share&t=42",
        "https://youtube.com/watch?v=dQw4w9WgXcQ",
    ),
    ("https://youtu.be/dQw4w9WgXcQ?si=xyz123", "https://youtube.com/watch?v=dQw4w9WgXcQ"),
    ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "https://youtube.com/watch?v=dQw4w9WgXcQ"),
    ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", "https://youtube.com/watch?v=dQw4w9WgXcQ"),
    ("https://www.youtube.com/embed/dQw4w9WgXcQ", "https://youtube.com/watch?v=dQw4w9WgXcQ"),
    # --- Pinterest ---
    (
        "https://nl.pinterest.com/pin/123456789012345678/",
        "https://pinterest.com/pin/123456789012345678",
    ),
    (
        "https://www.pinterest.com/pin/123456789012345678",
        "https://pinterest.com/pin/123456789012345678",
    ),
    # --- Blogs ---
    (
        "https://www.leukerecepten.nl/recepten/pasta-pesto/?utm_source=pinterest&utm_medium=social",
        "https://leukerecepten.nl/recepten/pasta-pesto",
    ),
    (
        "https://leukerecepten.nl/recepten/pasta-pesto/#ingredienten",
        "https://leukerecepten.nl/recepten/pasta-pesto",
    ),
    (
        "http://www.leukerecepten.nl/recepten/pasta-pesto",
        "https://leukerecepten.nl/recepten/pasta-pesto",
    ),
    (
        "https://ah.nl/allerhande/recept/R-R123?fbclid=IwAR123&gclid=abc",
        "https://ah.nl/allerhande/recept/R-R123",
    ),
    # Meaningful query params survive, and their order must not fork the cache key.
    (
        "https://blog.example.com/recept?b=2&a=1&utm_campaign=x",
        "https://blog.example.com/recept?a=1&b=2",
    ),
    (
        "https://blog.example.com/recept?a=1&b=2",
        "https://blog.example.com/recept?a=1&b=2",
    ),
    ("https://www.24kitchen.nl/recepten/stamppot/", "https://24kitchen.nl/recepten/stamppot"),
    # Scheme-less paste, which users do constantly.
    (
        "www.leukerecepten.nl/recepten/pasta-pesto/",
        "https://leukerecepten.nl/recepten/pasta-pesto",
    ),
    ("  https://leukerecepten.nl/pasta/  ", "https://leukerecepten.nl/pasta"),
    ("https://leukerecepten.nl/", "https://leukerecepten.nl"),
]


@pytest.mark.parametrize(("raw", "expected"), URL_PAIRS)
def test_normalise_url(raw: str, expected: str) -> None:
    assert normalise_url(raw) == expected


def test_fixture_table_covers_the_required_breadth() -> None:
    # The task asks for a table of 25 pairs; guard against it being whittled down later.
    assert len(URL_PAIRS) >= 25


def test_normalisation_is_idempotent() -> None:
    for raw, expected in URL_PAIRS:
        assert normalise_url(expected) == expected, raw


@pytest.mark.parametrize(
    ("url", "platform"),
    [
        ("https://tiktok.com/@a/video/1", SourcePlatform.tiktok),
        ("https://vm.tiktok.com/ZMabc123/", SourcePlatform.tiktok),
        ("https://instagram.com/reel/abc", SourcePlatform.instagram),
        ("https://youtu.be/abc", SourcePlatform.youtube),
        ("https://youtube.com/watch?v=abc", SourcePlatform.youtube),
        ("https://pin.it/abc123", SourcePlatform.pinterest),
        ("https://nl.pinterest.com/pin/1", SourcePlatform.pinterest),
        ("https://leukerecepten.nl/pasta", SourcePlatform.web),
    ],
)
def test_detect_platform(url: str, platform: SourcePlatform) -> None:
    from urllib.parse import urlsplit

    assert detect_platform(urlsplit(url).netloc) is platform


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://vm.tiktok.com/ZMabc123/", True),
        ("https://vt.tiktok.com/ZSabc123/", True),
        ("https://pin.it/abc123", True),
        # The form TikTok's own share sheet produces, so the one users actually paste.
        ("https://www.tiktok.com/t/ZP8n1HAPY/", True),
        ("https://tiktok.com/t/ZP8n1HAPY", True),
        # Resolvable offline, so no request should be spent on them.
        ("https://youtu.be/dQw4w9WgXcQ", False),
        ("https://l.instagram.com/?u=https%3A%2F%2Fx.nl%2Fa", False),
        ("https://tiktok.com/@a/video/1", False),
    ],
)
def test_needs_redirect_resolution(url: str, expected: bool) -> None:
    assert needs_redirect_resolution(url) is expected


@pytest.mark.asyncio
async def test_async_resolves_shortener_then_normalises() -> None:
    async def resolver(url: str) -> str:
        assert url == "https://vm.tiktok.com/ZMabc123/"
        return "https://www.tiktok.com/@chefkoen/video/7234567890123456789?_t=8abc"

    result = await normalise_url_async("https://vm.tiktok.com/ZMabc123/", resolver)
    assert result == "https://tiktok.com/@chefkoen/video/7234567890123456789"


@pytest.mark.asyncio
async def test_async_skips_resolver_when_not_needed() -> None:
    async def resolver(url: str) -> str:
        raise AssertionError("resolver must not be called for an offline-resolvable URL")

    result = await normalise_url_async("https://youtu.be/dQw4w9WgXcQ?si=x", resolver)
    assert result == "https://youtube.com/watch?v=dQw4w9WgXcQ"


@pytest.mark.asyncio
async def test_async_falls_back_to_unresolved_form_when_resolver_fails() -> None:
    async def resolver(url: str) -> str:
        raise TimeoutError("shortener down")

    # Still a stable cache key, rather than failing the whole import.
    result = await normalise_url_async("https://vm.tiktok.com/ZMabc123/", resolver)
    assert result == "https://tiktok.com/ZMabc123"


def test_empty_url_is_rejected() -> None:
    with pytest.raises(ValueError):
        normalise_url("   ")
