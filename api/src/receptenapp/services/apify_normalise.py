"""Turn Apify actor rows into `EvidenceBundle`s.

Every field name here was copied from a payload in `tests/fixtures/apify/`, captured by
`scripts/capture_apify_fixtures.py`. The three actors agree on almost nothing — different keys for
the caption, the author and the transcript, and three different ways of expressing a timestamp —
which is exactly the mess the bundle exists to absorb.
"""

import re
from typing import Any

from receptenapp.core.config import Settings
from receptenapp.core.errors import ImportErrorCode, ImportFailedError
from receptenapp.db.models import SourcePlatform
from receptenapp.providers.apify import ActorRunner
from receptenapp.services.evidence import EvidenceBundle, TranscriptSegment

# Caption tokens that carry no speech. YouTube's auto-captions emit these constantly, and a
# "transcript" made only of them is a silent video wearing a disguise — see the fixture, whose
# entire transcript is "[Music] you you [Music]".
_NON_SPEECH_RE = re.compile(
    r"^\s*[\[(](music|muziek|applause|applaus|laughter|gelach)[\])]\s*$", re.I
)
_TIMESTAMP_RE = re.compile(r"^(?:(\d+):)?(\d{1,2}):(\d{2})(?:\.(\d+))?$")

# Actor errors that mean "no speech to transcribe" rather than "this video is gone".
_TRANSCRIPTION_FAILURE_RE = re.compile(
    r"speechtext|no\s*(speech|transcript|subtitle|caption)|transcri\w*\s*(failed|unavailable)", re.I
)


def _clean(value: Any) -> str | None:
    return value.strip() or None if isinstance(value, str) else None


def _seconds_to_ms(value: Any) -> int | None:
    """TikTok and Instagram give float seconds."""
    if isinstance(value, int | float):
        return int(round(float(value) * 1000))
    return None


def _timestamp_to_ms(value: Any) -> int | None:
    """YouTube gives `"m:ss"`, and `"h:mm:ss"` once a video passes an hour."""
    if not isinstance(value, str):
        return None
    match = _TIMESTAMP_RE.match(value.strip())
    if not match:
        return None
    hours, minutes, seconds, fraction = match.groups()
    total = int(hours or 0) * 3600 + int(minutes) * 60 + int(seconds)
    return total * 1000 + int((fraction or "0").ljust(3, "0")[:3])


def _is_speech(text: str) -> bool:
    return bool(text.strip()) and not _NON_SPEECH_RE.match(text)


def _segments_from_start_end(rows: Any) -> list[TranscriptSegment]:
    """TikTok / Instagram: `{start, end, text}` with seconds as floats."""
    segments: list[TranscriptSegment] = []
    if not isinstance(rows, list):
        return segments
    for row in rows:
        if not isinstance(row, dict):
            continue
        text = _clean(row.get("text"))
        if not text or not _is_speech(text):
            continue
        segments.append(
            TranscriptSegment(
                text=text,
                start_ms=_seconds_to_ms(row.get("start")),
                end_ms=_seconds_to_ms(row.get("end")),
            )
        )
    return segments


def _segments_from_timestamps(rows: Any) -> list[TranscriptSegment]:
    """YouTube: `{time: "m:ss", text}`, with no end time — the next segment's start is the end."""
    segments: list[TranscriptSegment] = []
    if not isinstance(rows, list):
        return segments
    parsed: list[tuple[int | None, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        text = _clean(row.get("text"))
        if not text or not _is_speech(text):
            continue
        parsed.append((_timestamp_to_ms(row.get("time")), text))

    for index, (start_ms, text) in enumerate(parsed):
        next_start = parsed[index + 1][0] if index + 1 < len(parsed) else None
        segments.append(TranscriptSegment(text=text, start_ms=start_ms, end_ms=next_start))
    return segments


def _first_row(items: list[dict[str, Any]], platform: SourcePlatform) -> dict[str, Any]:
    if not items:
        raise ImportFailedError(
            ImportErrorCode.private_or_removed,
            "Dit bericht is niet meer beschikbaar.",
            details={"platform": str(platform)},
        )
    row = items[0]
    # The video actors report per-item failures in `errMsg` while still returning HTTP 200.
    if error := _clean(row.get("errMsg")):
        # A transcription failure is not a dead link. Seen in the wild as
        # "craw error: speechtext_obj is not defined" — the actor's way of saying the video has no
        # speech track. docs/03 calls that `no_transcript`: carry on with the caption alone rather
        # than failing the import, and let thin evidence be judged later on its merits.
        recoverable = bool(_TRANSCRIPTION_FAILURE_RE.search(error)) and bool(
            _clean(row.get("title"))
        )
        if not recoverable:
            raise ImportFailedError(
                ImportErrorCode.scraper_failed,
                "We konden deze video niet ophalen.",
                details={"actor_error": error[:200]},
            )
    return row


def normalise_tiktok(items: list[dict[str, Any]], *, url: str, url_norm: str) -> EvidenceBundle:
    row = _first_row(items, SourcePlatform.tiktok)
    return EvidenceBundle(
        platform=SourcePlatform.tiktok,
        url=_clean(row.get("url")) or url,
        url_norm=url_norm,
        author=_clean(row.get("nickname")),
        title=_clean(row.get("title")),
        caption=_clean(row.get("title")),
        transcript=_segments_from_start_end(row.get("segments")),
        # No thumbnail is returned. `videoUrl` is a signed CDN link that expires within hours and
        # `avatarUri` is the creator's face, so neither is usable as the recipe photo.
        thumbnail_url=None,
    )


def normalise_instagram(items: list[dict[str, Any]], *, url: str, url_norm: str) -> EvidenceBundle:
    row = _first_row(items, SourcePlatform.instagram)
    return EvidenceBundle(
        platform=SourcePlatform.instagram,
        url=_clean(row.get("url")) or url,
        url_norm=url_norm,
        author=_clean(row.get("userFullName")) or _clean(row.get("userName")),
        title=_clean(row.get("title")),
        caption=_clean(row.get("title")),
        transcript=_segments_from_start_end(row.get("segments")),
        # `img` comes back as an empty string in practice, so treat it as absent.
        thumbnail_url=_clean(row.get("img")),
    )


def normalise_youtube(items: list[dict[str, Any]], *, url: str, url_norm: str) -> EvidenceBundle:
    row = _first_row(items, SourcePlatform.youtube)
    channel = row.get("channel")
    author = _clean(channel.get("name")) if isinstance(channel, dict) else None
    return EvidenceBundle(
        platform=SourcePlatform.youtube,
        url=_clean(row.get("VideoURL")) or url,
        url_norm=url_norm,
        author=author,
        title=_clean(row.get("Video_title")),
        # The description is not a nice-to-have on YouTube: creators routinely paste the whole
        # ingredient list there, and on the captured fixture it is the *only* real evidence
        # because the auto-transcript is nothing but "[Music] you you [Music]".
        caption=_clean(row.get("Description")),
        transcript=_segments_from_timestamps(row.get("timestamps")),
        thumbnail_url=_clean(row.get("thumbnail")),
    )


_NORMALISERS = {
    SourcePlatform.tiktok: normalise_tiktok,
    SourcePlatform.instagram: normalise_instagram,
    SourcePlatform.youtube: normalise_youtube,
}


def build_actor_input(platform: SourcePlatform, url: str) -> dict[str, Any]:
    if platform is SourcePlatform.tiktok:
        return {"videoUrl": url}
    if platform is SourcePlatform.instagram:
        # Deliberately no `usernames`: the documented example pulls a whole account's recent posts.
        return {"videoUrl": url, "bulkUrls": [], "resultsLimit": 1}
    if platform is SourcePlatform.youtube:
        return {
            "youtubeUrl": [{"url": url}],
            "transcriptOnly": False,
            "extractcomments": False,
            # Must be >= 10 even with extraction off; the actor rejects 0.
            "maxComments": 10,
            "maxRepliesPerComment": 0,
        }
    raise ImportFailedError(ImportErrorCode.unsupported_url, "Deze link kennen we niet.")


def actor_id_for(platform: SourcePlatform, settings: Settings) -> str | None:
    return {
        SourcePlatform.tiktok: settings.apify_actor_tiktok,
        SourcePlatform.instagram: settings.apify_actor_instagram,
        SourcePlatform.youtube: settings.apify_actor_youtube,
    }.get(platform)


def normalise(
    platform: SourcePlatform, items: list[dict[str, Any]], *, url: str, url_norm: str
) -> EvidenceBundle:
    normaliser = _NORMALISERS.get(platform)
    if normaliser is None:
        raise ImportFailedError(ImportErrorCode.unsupported_url, "Deze link kennen we niet.")
    return normaliser(items, url=url, url_norm=url_norm)


async def fetch_social_evidence(
    url: str,
    url_norm: str,
    platform: SourcePlatform,
    runner: ActorRunner,
    settings: Settings,
) -> EvidenceBundle:
    """The social half of Stage 1: run the platform's actor and normalise what comes back."""
    actor_id = actor_id_for(platform, settings)
    if not actor_id:
        raise ImportFailedError(
            ImportErrorCode.unsupported_url, "Voor dit platform is geen importer ingesteld."
        )
    items = await runner.run_actor(
        actor_id,
        build_actor_input(platform, url),
        timeout_seconds=settings.apify_timeout_seconds,
    )
    return normalise(platform, items, url=url, url_norm=url_norm)
