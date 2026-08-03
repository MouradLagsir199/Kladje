"""M7 — Apify rows into EvidenceBundles, against real captured payloads.

Fixtures in `tests/fixtures/apify/` are unedited actor output. No network, no spend.
"""

import json
import pathlib
from typing import Any

import pytest

from receptenapp.core.errors import ImportErrorCode, ImportFailedError
from receptenapp.db.models import SourcePlatform
from receptenapp.providers.apify import StubActorRunner
from receptenapp.services.apify_normalise import (
    build_actor_input,
    fetch_social_evidence,
    normalise,
)
from tests.support import make_settings

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "apify"

PLATFORMS = [
    (SourcePlatform.tiktok, "tiktok.json"),
    (SourcePlatform.instagram, "instagram.json"),
    (SourcePlatform.youtube, "youtube.json"),
]


def payload(name: str) -> list[dict[str, Any]]:
    data = json.loads((FIXTURES / name).read_text("utf-8"))
    assert isinstance(data, list)
    return data


def bundle_for(platform: SourcePlatform, name: str) -> Any:
    return normalise(
        platform, payload(name), url="https://in.test/x", url_norm="https://norm.test/x"
    )


@pytest.mark.parametrize(("platform", "name"), PLATFORMS)
def test_every_captured_payload_normalises(platform: SourcePlatform, name: str) -> None:
    bundle = bundle_for(platform, name)
    assert bundle.platform is platform
    assert bundle.url_norm == "https://norm.test/x"
    assert bundle.title, "no title"
    assert bundle.caption, "no caption"


@pytest.mark.parametrize(("platform", "name"), PLATFORMS)
def test_timings_are_milliseconds_on_every_platform(platform: SourcePlatform, name: str) -> None:
    """The whole point of the seam: three timestamp formats in, one unit out."""
    for segment in bundle_for(platform, name).transcript:
        if segment.start_ms is not None:
            assert isinstance(segment.start_ms, int)
            # A whole video in under a second would mean seconds leaked through unconverted.
            assert 0 <= segment.start_ms < 24 * 3600 * 1000


def test_tiktok_transcript_and_author() -> None:
    bundle = bundle_for(SourcePlatform.tiktok, "tiktok.json")
    assert bundle.author == "Tyler Butterworth"
    assert "tomatoes" in bundle.transcript_text.lower()
    assert len(bundle.transcript) >= 5
    # Float seconds must have been scaled: 0.3s is 300ms, not 0.
    assert bundle.transcript[0].start_ms == 300
    # Neither the expiring CDN video URL nor the creator's avatar is a recipe photo.
    assert bundle.thumbnail_url is None


def test_instagram_author_and_empty_image_is_treated_as_absent() -> None:
    bundle = bundle_for(SourcePlatform.instagram, "instagram.json")
    assert bundle.author == "Yumna | Feel Good Foodie"
    assert "feta" in (bundle.caption or "").lower()
    # The actor returns img as "" rather than omitting it.
    assert bundle.thumbnail_url is None


def test_youtube_uses_description_because_the_transcript_is_noise() -> None:
    """The captured video's auto-transcript is literally "[Music] you you [Music]".

    Non-speech tags are dropped, so what little remains must not masquerade as a recipe — the
    description is the real evidence and has to survive.
    """
    bundle = bundle_for(SourcePlatform.youtube, "youtube.json")
    assert bundle.author == "KingNectuluhCooking"
    assert bundle.thumbnail_url and bundle.thumbnail_url.startswith("http")
    assert "[Music]" not in bundle.transcript_text
    assert (
        "peasoup" in (bundle.caption or "").lower()
        or "erwtensoep" in (bundle.caption or "").lower()
    )
    assert bundle.evidence_chars() > 200


def test_youtube_hms_timestamps_convert() -> None:
    from receptenapp.services.apify_normalise import _timestamp_to_ms

    assert _timestamp_to_ms("0:00") == 0
    assert _timestamp_to_ms("1:30") == 90_000
    assert _timestamp_to_ms("1:02:03") == 3_723_000
    assert _timestamp_to_ms("bogus") is None
    assert _timestamp_to_ms(None) is None


def test_non_speech_only_transcript_counts_as_silent() -> None:
    rows = [{"segments": [{"start": 0, "end": 2, "text": "[Music]"}, {"text": "[Applause]"}]}]
    bundle = normalise(SourcePlatform.tiktok, rows, url="u", url_norm="n")
    assert bundle.transcript == []
    assert bundle.is_silent is True


def test_actor_reported_error_is_a_failure_not_an_empty_recipe() -> None:
    rows = [{"errMsg": "video unavailable", "segments": []}]
    with pytest.raises(ImportFailedError) as exc:
        normalise(SourcePlatform.tiktok, rows, url="u", url_norm="n")
    assert exc.value.error_code is ImportErrorCode.scraper_failed


def test_no_rows_means_gone() -> None:
    with pytest.raises(ImportFailedError) as exc:
        normalise(SourcePlatform.instagram, [], url="u", url_norm="n")
    assert exc.value.error_code is ImportErrorCode.private_or_removed


def test_blog_platform_has_no_actor() -> None:
    with pytest.raises(ImportFailedError) as exc:
        build_actor_input(SourcePlatform.web, "https://blog.test/x")
    assert exc.value.error_code is ImportErrorCode.unsupported_url


def test_instagram_input_does_not_scrape_a_whole_account() -> None:
    # The documented example passes usernames, which pulls that account's recent posts.
    assert "usernames" not in build_actor_input(SourcePlatform.instagram, "https://ig.test/reel/a")


def test_youtube_input_satisfies_the_actor_minimum() -> None:
    # The actor rejects maxComments below 10 even when extraction is off.
    assert build_actor_input(SourcePlatform.youtube, "https://yt.test/x")["maxComments"] >= 10


@pytest.mark.asyncio
async def test_fetch_social_evidence_calls_the_right_actor() -> None:
    settings = make_settings(apify_actor_tiktok="ACTOR_TT")
    runner = StubActorRunner({"ACTOR_TT": payload("tiktok.json")})
    bundle = await fetch_social_evidence(
        "https://tiktok.com/@a/video/1",
        "https://tiktok.com/@a/video/1",
        SourcePlatform.tiktok,
        runner,
        settings,
    )
    assert bundle.author == "Tyler Butterworth"
    assert runner.calls[0][0] == "ACTOR_TT"


@pytest.mark.asyncio
async def test_missing_actor_config_fails_clearly() -> None:
    settings = make_settings(apify_actor_youtube=None)
    with pytest.raises(ImportFailedError) as exc:
        await fetch_social_evidence("u", "n", SourcePlatform.youtube, StubActorRunner({}), settings)
    assert exc.value.error_code is ImportErrorCode.unsupported_url


def test_transcription_failure_continues_on_the_caption() -> None:
    """Seen in the wild: "craw error: speechtext_obj is not defined".

    The actor could not transcribe, but the caption is still real evidence — and on TikTok the
    caption is very often where the recipe actually is. docs/03 calls this `no_transcript`.
    """
    rows = [
        {
            "errMsg": "craw error: speechtext_obj is not defined",
            "title": "Taco Stromboli: 500 g gehakt, 1 pizzadeeg, kaas. 20 min op 200 graden.",
            "nickname": "Someone",
            "segments": [],
        }
    ]
    bundle = normalise(SourcePlatform.tiktok, rows, url="u", url_norm="n")
    assert bundle.transcript == []
    assert "Stromboli" in (bundle.caption or "")
    assert bundle.is_too_thin_to_synthesise() is False


def test_transcription_failure_with_no_caption_is_still_a_failure() -> None:
    # Nothing salvageable: no transcript and no caption means there is no evidence at all.
    rows = [{"errMsg": "craw error: speechtext_obj is not defined", "segments": []}]
    with pytest.raises(ImportFailedError) as exc:
        normalise(SourcePlatform.tiktok, rows, url="u", url_norm="n")
    assert exc.value.error_code is ImportErrorCode.scraper_failed


def test_a_genuinely_dead_video_still_fails_even_with_a_caption() -> None:
    rows = [{"errMsg": "video unavailable or private", "title": "Some caption", "segments": []}]
    with pytest.raises(ImportFailedError) as exc:
        normalise(SourcePlatform.tiktok, rows, url="u", url_norm="n")
    assert exc.value.error_code is ImportErrorCode.scraper_failed
