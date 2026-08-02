"""Capture one real Apify payload per platform into tests/fixtures/apify/ (task M6).

Run this before touching a normaliser. Every field name in the normalisers is copied from a payload
this script saved — guessing them is how "Apify's response differs from what the docs assume" turns
into a debugging session later.

    uv run python scripts/capture_apify_fixtures.py

Costs a few cents. Existing fixtures are not overwritten unless --force is passed.
"""

import argparse
import asyncio
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from receptenapp.core.config import settings  # noqa: E402
from receptenapp.providers.apify import HttpxActorRunner  # noqa: E402

FIXTURES = pathlib.Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "apify"

TARGETS = [
    (
        "tiktok",
        settings.apify_actor_tiktok,
        "https://www.tiktok.com/@butterworthdasyrup/video/7484033605795204394",
        lambda url: {"videoUrl": url},
    ),
    (
        "instagram",
        settings.apify_actor_instagram,
        "https://www.instagram.com/reel/CKnLRkOAi3j/",
        # No `usernames`: the documented example pulls a whole account's recent posts, which is
        # both slower and not what a single import needs.
        lambda url: {"videoUrl": url, "bulkUrls": [], "resultsLimit": 1},
    ),
    (
        "youtube",
        settings.apify_actor_youtube,
        "https://www.youtube.com/watch?v=oHCnwRLbfFc",
        # transcriptOnly stays False: creators routinely paste the full ingredient list into the
        # description, and docs/03 calls that the highest-confidence evidence YouTube offers.
        # maxComments must be >= 10 even when extractcomments is False — the actor rejects 0 with
        # "Field input.maxComments must be >= 10". Found by calling it; no doc says so.
        lambda url: {
            "youtubeUrl": [{"url": url}],
            "transcriptOnly": False,
            "extractcomments": False,
            "maxComments": 10,
            "maxRepliesPerComment": 0,
        },
    ),
]


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="re-fetch fixtures that already exist")
    parser.add_argument("--only", help="platform name to capture on its own")
    args = parser.parse_args()

    if not settings.apify_token:
        print("APIFY_TOKEN is not set", file=sys.stderr)
        return 1

    FIXTURES.mkdir(parents=True, exist_ok=True)
    runner = HttpxActorRunner(settings.apify_token)
    failures = 0
    try:
        for name, actor_id, url, build_input in TARGETS:
            if args.only and args.only != name:
                continue
            out = FIXTURES / f"{name}.json"
            if out.exists() and not args.force:
                print(f"{name:10} skip (already captured)")
                continue
            if not actor_id:
                print(f"{name:10} SKIP — no actor id configured")
                failures += 1
                continue

            print(f"{name:10} calling actor {actor_id} …", flush=True)
            try:
                items = await runner.run_actor(
                    actor_id, build_input(url), timeout_seconds=settings.apify_timeout_seconds
                )
            except Exception as exc:  # noqa: BLE001 — one platform failing must not lose the rest
                print(f"{name:10} FAILED {type(exc).__name__}: {exc}")
                failures += 1
                continue

            out.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
            top_keys = sorted(items[0].keys()) if items else []
            print(f"{name:10} {len(items)} item(s) -> {out.name}")
            print(f"{'':10} keys: {', '.join(top_keys)[:300]}")
    finally:
        await runner.aclose()
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
