"""Run the import pipeline against real URLs (task M14).

    uv run python scripts/try_import.py <url> [<url> ...]
    uv run python scripts/try_import.py --sample
    uv run python scripts/try_import.py <url> --synthesise
    uv run python scripts/try_import.py <url> --synthesise --save-for user_2abc...

Evidence only, by default. `--synthesise` spends one OpenAI call per URL; `--save-for` writes the
result into that Clerk user's library, which is how real data gets onto a screen while the import
endpoint does not exist yet. Social URLs spend one Apify actor run each. Blogs cost nothing.
"""

import argparse
import asyncio
import pathlib
import sys
from urllib.parse import urlsplit

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from sqlalchemy import select  # noqa: E402

from receptenapp.core.config import settings  # noqa: E402
from receptenapp.core.errors import ImportFailedError  # noqa: E402
from receptenapp.db.models import SourcePlatform, User  # noqa: E402
from receptenapp.db.session import async_session_factory  # noqa: E402
from receptenapp.providers.apify import HttpxActorRunner  # noqa: E402
from receptenapp.providers.http import HttpxPageFetcher  # noqa: E402
from receptenapp.providers.openai import HttpxChatCompleter  # noqa: E402
from receptenapp.schemas.synthesis import SynthesisResult  # noqa: E402
from receptenapp.services.apify_normalise import fetch_social_evidence  # noqa: E402
from receptenapp.services.blog_extract import fetch_and_extract  # noqa: E402
from receptenapp.services.evidence import EvidenceBundle  # noqa: E402
from receptenapp.services.materialise import materialise  # noqa: E402
from receptenapp.services.synthesis import synthesise  # noqa: E402
from receptenapp.services.url_norm import detect_platform, normalise_url_async  # noqa: E402

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


def summarise_evidence(bundle: EvidenceBundle) -> None:
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


def summarise_recipe(result: SynthesisResult) -> None:
    """Print it the way the detail screen would read it, provenance included.

    The four-letter provenance prefix is the point of this output: a wall of plausible numbers with
    no way to see which were stated and which were computed is exactly what this app must not be.
    """
    print(f"\n  === {result.title} ({result.confidence}) ===")
    meta = [
        f"{result.servings} pers." if result.servings else "porties: ontbreekt",
        f"{result.prep_minutes} min voorbereiden" if result.prep_minutes else None,
        f"{result.cook_minutes} min koken" if result.cook_minutes else None,
        str(result.difficulty) if result.difficulty else None,
        f"oven {result.oven_c}" if result.oven_c else None,
    ]
    print("  " + " · ".join(m for m in meta if m))
    if result.missing:
        print(f"  ontbreekt: {', '.join(result.missing)}")
    # The scalar fields are where a plausible wrong number does the most damage, so print what the
    # model claims about each one. A `servings` it calls "explicit" had better be in the source.
    provenance = result.field_provenance
    print(
        "  provenance: "
        + ", ".join(
            f"{name}={getattr(provenance, name)}"
            for name in ("title", "servings", "prep_minutes", "cook_minutes", "difficulty")
        )
    )

    print("\n  Ingrediënten")
    for item in sorted(result.ingredients, key=lambda i: i.pos):
        amount = "" if item.amount is None else f"{item.amount:g} "
        unit = f"{item.unit} " if item.unit else ""
        original = (
            f"   (bron: {item.orig_amount:g} {item.orig_unit})"
            if item.orig_amount is not None
            else ""
        )
        print(f"    [{str(item.prov)[:4]}] {amount}{unit}{item.name_nl}{original}")

    print("\n  Bereiding")
    for step in sorted(result.steps, key=lambda s: s.pos):
        timer = f"  (timer {step.timer_seconds}s)" if step.timer_seconds else ""
        print(f"    {step.pos}. [{str(step.prov)[:4]}] {step.text}{timer}")


async def evidence_for(
    url: str, fetcher: HttpxPageFetcher, runner: HttpxActorRunner | None
) -> EvidenceBundle | None:
    url_norm = await normalise_url_async(url, fetcher.resolve_redirect)
    platform = detect_platform(urlsplit(url_norm).netloc)

    if platform in SOCIAL:
        if runner is None:
            print("  skipped (no Apify token)")
            return None
        return await fetch_social_evidence(url_norm, url_norm, platform, runner, settings)
    return await fetch_and_extract(url_norm, fetcher)


async def save_for(
    clerk_user_ids: list[str], result: SynthesisResult, bundle: EvidenceBundle
) -> None:
    """Save one synthesis to one or more libraries.

    Several ids because a dev database usually holds more than one of your own test accounts, and
    re-running synthesis per account would pay for the same recipe twice.
    """
    async with async_session_factory() as db:
        for clerk_user_id in clerk_user_ids:
            found = await db.execute(select(User).where(User.clerk_user_id == clerk_user_id))
            user = found.scalar_one_or_none()
            if user is None:
                print(f"  NOT SAVED: no user with clerk_user_id {clerk_user_id}")
                continue
            recipe = await materialise(db, user.id, result, bundle)
            await db.commit()
            print(f"  saved as {recipe.id} for {clerk_user_id}")


async def run_one(
    url: str,
    fetcher: HttpxPageFetcher,
    runner: HttpxActorRunner | None,
    completer: HttpxChatCompleter | None,
    save_clerk_user_ids: list[str],
) -> bool:
    print(f"\n=== {url[:100]}")
    try:
        bundle = await evidence_for(url, fetcher, runner)
        if bundle is None:
            return True
        summarise_evidence(bundle)

        if completer is None:
            return True

        result = await synthesise(bundle, completer, settings)
        summarise_recipe(result)

        if save_clerk_user_ids:
            await save_for(save_clerk_user_ids, result, bundle)
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
    parser.add_argument(
        "--synthesise", action="store_true", help="spend one OpenAI call per URL and print a recipe"
    )
    parser.add_argument(
        "--save-for",
        metavar="CLERK_USER_IDS",
        help="comma-separated Clerk user ids to write the recipe into",
    )
    args = parser.parse_args()
    save_for_ids = [part for part in (args.save_for or "").split(",") if part.strip()]

    urls = SAMPLE_URLS if args.sample else args.urls
    if not urls:
        parser.error("give at least one URL, or --sample")
    if args.save_for and not args.synthesise:
        parser.error("--save-for needs --synthesise; there is nothing to save otherwise")

    fetcher = HttpxPageFetcher()
    runner = HttpxActorRunner(settings.apify_token) if settings.apify_token else None
    completer = None
    if args.synthesise:
        if not settings.openai_api_key:
            parser.error("OPENAI_API_KEY is not set")
        completer = HttpxChatCompleter(settings.openai_api_key)
        print(f"synthesis on: model {settings.openai_model}, prompt v{settings.prompt_version}")

    ok = 0
    try:
        for url in urls:
            if await run_one(url, fetcher, runner, completer, save_for_ids):
                ok += 1
    finally:
        await fetcher.aclose()
        if runner:
            await runner.aclose()
        if completer:
            await completer.aclose()

    print(f"\n{ok}/{len(urls)} produced evidence")
    return 0 if ok == len(urls) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
