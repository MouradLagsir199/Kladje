"""Run the evidence half of the import pipeline against real URLs (task M14, in progress).

    uv run python scripts/try_import.py <url> [<url> ...]
    uv run python scripts/try_import.py --sample

Blogs cost nothing. Social URLs spend one Apify actor run each. Synthesis is not wired in yet, so
this stops at the evidence bundle — which is the part worth eyeballing before paying a model to
read it.
"""

import argparse
import asyncio
import pathlib
import sys
from urllib.parse import urlsplit

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from receptenapp.core.config import settings  # noqa: E402
from receptenapp.core.errors import ImportFailedError  # noqa: E402
from receptenapp.db.models import SourcePlatform  # noqa: E402
from receptenapp.providers.apify import HttpxActorRunner  # noqa: E402
from receptenapp.providers.http import HttpxPageFetcher  # noqa: E402
from receptenapp.services.apify_normalise import fetch_social_evidence  # noqa: E402
from receptenapp.services.blog_extract import fetch_and_extract  # noqa: E402
from receptenapp.services.evidence import EvidenceBundle  # noqa: E402
from receptenapp.services.url_norm import (  # noqa: E402
    detect_platform,
    normalise_url_async,
)

SAMPLE_URLS = [
    "https://www.tiktok.com/t/ZP8n1HAPY/",
    "https://www.tiktok.com/t/ZP8n1M2cG/",
    "https://www.tiktok.com/t/ZP8n14AVt/",
    "https://www.instagram.com/reel/DOCTm9eE-D-/?igsh=MW5kM2p3c2hlOGphdA==",
    "https://www.instagram.com/reel/DS3DPehEnpA/?igsh=cXlkdnR6aGk0Zmp2",
    "https://www.instagram.com/reel/DXMUPlzk8xi/?igsh=MWtiZ2NtMWl6OGFxdw==",
    "https://www.allrecipes.com/pizza-lasagna-recipe-12005007"
    "?utm_campaign=allrecipes_6a64ebabe999d00001fcb5f4&utm_medium=social&utm_source=pinterest.com",
    "https://www.allrecipes.com/pesto-zucchini-and-corn-orzo-casserole-recipe-11961784"
    "?utm_campaign=allrecipes_6a00b9966ee13f0001978ad6&utm_medium=social&utm_source=pinterest.com",
]

SOCIAL = {SourcePlatform.tiktok, SourcePlatform.instagram, SourcePlatform.youtube}


def summarise(bundle: EvidenceBundle) -> None:
    print(f"  platform    {bundle.platform}")
    print(f"  url_norm    {bundle.url_norm}")
    print(f"  author      {bundle.author!r}")
    print(f"  title       {(bundle.title or '')[:90]!r}")
    print(f"  caption     {(bundle.caption or '')[:90]!r}")
    if bundle.structured:
        print(
            f"  structured  {len(bundle.structured.get('recipeIngredient', []))} ingredients, "
            f"{len(bundle.structured.get('recipeInstructions', []))} steps"
        )
    print(f"  transcript  {len(bundle.transcript)} segments, {len(bundle.transcript_text)} chars")
    print(f"  thumbnail   {(bundle.thumbnail_url or '-')[:70]}")
    if bundle.needs_manual_entry:
        verdict = "TOO THIN -> manual entry (not worth a model call)"
    elif bundle.is_silent:
        verdict = "OK on caption alone (no speech in the video)"
    else:
        verdict = "OK - enough evidence to synthesise"
    print(f"  evidence    {bundle.evidence_chars()} chars -> {verdict}")


async def run_one(url: str, fetcher: HttpxPageFetcher, runner: HttpxActorRunner | None) -> bool:
    print(f"\n=== {url[:100]}")
    try:
        url_norm = await normalise_url_async(url, fetcher.resolve_redirect)
        platform = detect_platform(urlsplit(url_norm).netloc)

        if platform in SOCIAL:
            if runner is None:
                print("  skipped (no Apify token)")
                return True
            bundle = await fetch_social_evidence(url_norm, url_norm, platform, runner, settings)
        else:
            bundle = await fetch_and_extract(url_norm, fetcher)

        summarise(bundle)
        return True
    except ImportFailedError as exc:
        print(f"  FAILED [{exc.code}] {exc.message}  {exc.details or ''}")
        return False
    except Exception as exc:  # noqa: BLE001 — one bad URL must not stop the batch
        print(f"  CRASHED {type(exc).__name__}: {exc}")
        return False


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("urls", nargs="*")
    parser.add_argument("--sample", action="store_true", help="use the built-in URL list")
    args = parser.parse_args()

    urls = SAMPLE_URLS if args.sample else args.urls
    if not urls:
        parser.error("give at least one URL, or --sample")

    fetcher = HttpxPageFetcher()
    runner = HttpxActorRunner(settings.apify_token) if settings.apify_token else None
    ok = 0
    try:
        for url in urls:
            if await run_one(url, fetcher, runner):
                ok += 1
    finally:
        await fetcher.aclose()
        if runner:
            await runner.aclose()

    print(f"\n{ok}/{len(urls)} produced evidence")
    return 0 if ok == len(urls) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
