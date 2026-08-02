"""Stage 0 of the import pipeline — see docs/03-import-pipeline.md.

The output of this module is `source_url_norm`, which is the `source_cache` key. That makes it a
cost control, not a cosmetic detail: two spellings of the same video that normalise differently
each pay for their own scrape and synthesis.

Everything here except `normalise_url_async` is pure and synchronous. Shorteners that can only be
resolved by asking the network (`vm.tiktok.com`, `pin.it`) are handled behind an injected
`RedirectResolver` so the rule table stays testable without touching the internet.
"""

import re
from typing import Protocol
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from receptenapp.db.models import SourcePlatform

# Exact-match tracking parameters. `si` and `feature` are YouTube's, `igsh`/`igshid` Instagram's,
# `_t`/`_r` TikTok's.
TRACKING_PARAMS = frozenset(
    {
        "fbclid",
        "gclid",
        "igsh",
        "igshid",
        "mc_cid",
        "mc_eid",
        "si",
        "feature",
        "_t",
        "_r",
    }
)
TRACKING_PREFIXES = ("utm_",)

# Shorteners whose target can only be learned by following a redirect.
NETWORK_SHORTENER_HOSTS = frozenset({"vm.tiktok.com", "vt.tiktok.com", "pin.it"})

# `tiktok.com/t/<code>` is the same kind of shortener, but on the main host rather than its own —
# so it cannot be recognised by hostname alone. This is the form the TikTok share sheet produces,
# which makes it the one users actually paste.
_SHORTENED_PATH_RE = re.compile(r"^/t/[A-Za-z0-9]+/?$")

_TIKTOK_VIDEO_RE = re.compile(r"^/@(?P<author>[^/]+)/video/(?P<id>\d+)")
_TIKTOK_BARE_VIDEO_RE = re.compile(r"^/video/(?P<id>\d+)")
_INSTAGRAM_RE = re.compile(r"^/(?:reel|reels|tv|p)/(?P<code>[^/]+)")
_YOUTUBE_PATH_ID_RE = re.compile(r"^/(?:shorts|embed|live|v)/(?P<id>[^/]+)")
_PINTEREST_PIN_RE = re.compile(r"^/pin/(?P<id>\d+)")


class RedirectResolver(Protocol):
    """Follows redirects for a shortened URL and returns the final URL.

    Implemented in `providers/` — this module never performs I/O itself, so the rule table can be
    tested without the network and without paying for a live request.
    """

    async def __call__(self, url: str) -> str: ...


def _canonical_host(host: str) -> str:
    host = host.lower().removeprefix("www.").removeprefix("m.")
    return host.removesuffix(".")


def _is_tracking(key: str) -> bool:
    lowered = key.lower()
    return lowered in TRACKING_PARAMS or lowered.startswith(TRACKING_PREFIXES)


def _clean_query(query: str) -> str:
    """Drop tracking parameters and sort the rest, so parameter order can't fork the cache key."""
    kept = [(k, v) for k, v in parse_qsl(query, keep_blank_values=True) if not _is_tracking(k)]
    return urlencode(sorted(kept))


def detect_platform(host: str) -> SourcePlatform:
    host = _canonical_host(host)
    if host == "tiktok.com" or host.endswith(".tiktok.com"):
        return SourcePlatform.tiktok
    if host in {"instagram.com", "l.instagram.com"} or host.endswith(".instagram.com"):
        return SourcePlatform.instagram
    if host in {"youtube.com", "youtu.be"} or host.endswith(".youtube.com"):
        return SourcePlatform.youtube
    if host in {"pinterest.com", "pin.it"} or ".pinterest." in f".{host}":
        return SourcePlatform.pinterest
    return SourcePlatform.web


def needs_redirect_resolution(url: str) -> bool:
    """True when the URL hides its destination behind a redirect we cannot infer offline."""
    parts = urlsplit(url if "//" in url[:10] else f"https://{url}")
    host = _canonical_host(parts.netloc)
    if host in NETWORK_SHORTENER_HOSTS:
        return True
    return host == "tiktok.com" and bool(_SHORTENED_PATH_RE.match(parts.path))


def _build(host: str, path: str, query: str = "") -> str:
    return urlunsplit(("https", host, path, query, ""))


def _normalise_tiktok(host: str, path: str) -> str:
    if match := _TIKTOK_VIDEO_RE.match(path):
        return _build("tiktok.com", f"/@{match['author']}/video/{match['id']}")
    if match := _TIKTOK_BARE_VIDEO_RE.match(path):
        # Author-less form; keep the id so the cache key is still stable.
        return _build("tiktok.com", f"/video/{match['id']}")
    return _build("tiktok.com", path)


def _normalise_instagram(host: str, path: str, query: str) -> str:
    # `l.instagram.com/?u=<encoded>` is Instagram's outbound link wrapper — the real destination is
    # in `u`, so unwrap it rather than caching the wrapper.
    if host == "l.instagram.com":
        target = dict(parse_qsl(query)).get("u")
        if target:
            return normalise_url(target)
    if match := _INSTAGRAM_RE.match(path):
        # `/reels/` and `/tv/` are aliases Instagram serves the same reel under, so they collapse.
        # `/p/` is deliberately preserved: it is also used for photo posts, and rewriting those to
        # `/reel/` would misrepresent what the source actually is.
        prefix = "p" if path.startswith("/p/") else "reel"
        return _build("instagram.com", f"/{prefix}/{match['code']}")
    return _build("instagram.com", path)


def _normalise_youtube(host: str, path: str, query: str) -> str:
    params = dict(parse_qsl(query))
    video_id = None
    if host == "youtu.be":
        video_id = path.lstrip("/").split("/")[0]
    elif match := _YOUTUBE_PATH_ID_RE.match(path):
        video_id = match["id"]
    elif path == "/watch":
        video_id = params.get("v")

    if video_id:
        return _build("youtube.com", "/watch", urlencode({"v": video_id}))
    return _build("youtube.com", path, _clean_query(query))


def _normalise_pinterest(host: str, path: str, query: str) -> str:
    if match := _PINTEREST_PIN_RE.match(path):
        return _build("pinterest.com", f"/pin/{match['id']}")
    return _build(host, path, _clean_query(query))


def normalise_url(url: str) -> str:
    """Canonicalise a source URL into the `source_cache` key.

    Pure: shorteners needing a live redirect are canonicalised as far as possible and returned
    as-is. Callers that can afford I/O should use `normalise_url_async`.
    """
    raw = url.strip()
    if not raw:
        raise ValueError("URL is leeg.")
    if "//" not in raw.split("?", 1)[0][:10]:
        # Tolerate "tiktok.com/@x/video/1" — users paste URLs without a scheme constantly.
        raw = f"https://{raw}"

    parts = urlsplit(raw)
    host = _canonical_host(parts.netloc.split("@")[-1].split(":")[0])
    path = parts.path.rstrip("/") or "/"

    platform = detect_platform(host)
    if platform is SourcePlatform.tiktok:
        return _normalise_tiktok(host, path)
    if platform is SourcePlatform.instagram:
        return _normalise_instagram(host, path, parts.query)
    if platform is SourcePlatform.youtube:
        return _normalise_youtube(host, path, parts.query)
    if platform is SourcePlatform.pinterest:
        return _normalise_pinterest(host, path, parts.query)

    query = _clean_query(parts.query)
    return _build(host, "" if path == "/" else path, query)


async def normalise_url_async(url: str, resolver: RedirectResolver) -> str:
    """`normalise_url`, but first follows redirects for shorteners that need the network.

    A resolver failure is not fatal: the unresolved form is still a usable, stable cache key, and
    failing the whole import because a shortener was slow would be a worse trade.
    """
    if needs_redirect_resolution(url):
        try:
            resolved = await resolver(url)
        except Exception:
            return normalise_url(url)
        if resolved:
            return normalise_url(resolved)
    return normalise_url(url)
