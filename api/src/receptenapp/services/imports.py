"""Stage 0 to 5 of the import pipeline, joined up — see docs/03-import-pipeline.md.

The shape here is the one ADR-009 asks for: no queue, no worker, no Redis. `POST /v1/imports`
returns immediately and the work continues in this same process as a background task, writing an
`import_events` row per stage. The client polls `GET /v1/imports/{id}`, which is the documented
fallback for the SSE stream that arrives in Phase H — polling first because a progress screen driven
by real stage rows is honest, and one driven by a timer is a lie with an animation on it.

Because the task outlives the request, it opens its own session. The request's session is closed the
moment the response is sent.
"""

import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from receptenapp.core.config import Settings, settings
from receptenapp.core.errors import (
    ConflictError,
    ImportErrorCode,
    ImportFailedError,
    NotFoundError,
    SemanticError,
)
from receptenapp.db.models import (
    Import,
    ImportEvent,
    ImportStatus,
    PlanTier,
    Recipe,
    SourcePlatform,
    User,
)
from receptenapp.db.session import async_session_factory
from receptenapp.providers.apify import ActorRunner, HttpxActorRunner
from receptenapp.providers.http import HttpxPageFetcher, PageFetcher
from receptenapp.providers.openai import ChatCompleter, HttpxChatCompleter
from receptenapp.schemas.synthesis import SynthesisResult
from receptenapp.services.apify_normalise import fetch_social_evidence
from receptenapp.services.blog_extract import fetch_and_extract
from receptenapp.services.materialise import RecipeSource, materialise
from receptenapp.services.synthesis import synthesise
from receptenapp.services.url_norm import detect_platform, normalise_url_async
from receptenapp.services.validation import validate

STAGE_FETCH = "fetch"
STAGE_SYNTHESIZE = "synthesize"
STAGE_VALIDATE = "validate"

STATE_STARTED = "started"
STATE_DONE = "done"
STATE_FAILED = "failed"

SOCIAL_PLATFORMS = frozenset(
    {SourcePlatform.tiktok, SourcePlatform.instagram, SourcePlatform.youtube}
)

QUOTA_WINDOW_DAYS = 30


# --- Quota -------------------------------------------------------------------------------------


async def quota_used(db: AsyncSession, user_id: uuid.UUID) -> int:
    """Imports counted against this user in the current window.

    Derived by counting rows, never stored as a counter — a counter drifts and there is no way to
    tell that it has. The partial index on `(user_id, counted_against_quota, created_at)` is what
    makes this cheap enough to run before every import.
    """
    since = datetime.now(UTC) - timedelta(days=QUOTA_WINDOW_DAYS)
    result = await db.execute(
        select(func.count())
        .select_from(Import)
        .where(
            Import.user_id == user_id,
            Import.counted_against_quota.is_(True),
            Import.created_at >= since,
        )
    )
    return int(result.scalar_one())


def quota_limit(user: User, config: Settings) -> int:
    if user.tier is PlanTier.premium:
        return config.premium_imports_per_period
    return config.free_imports_per_30d


async def assert_quota_available(db: AsyncSession, user: User, config: Settings) -> None:
    """Checked before the first paid call, never after.

    A CLAUDE.md non-negotiable, and the reason it is stated as one: an over-quota import that has
    already run has already cost money, so refusing it afterwards protects nothing.
    """
    used = await quota_used(db, user.id)
    limit = quota_limit(user, config)
    if used >= limit:
        raise ImportFailedError(
            ImportErrorCode.quota_exceeded,
            "Je hebt al je imports van deze maand gebruikt.",
            details={"used": used, "limit": limit},
        )


# --- Creating an import ------------------------------------------------------------------------


async def _existing_recipe_for(
    db: AsyncSession, user_id: uuid.UUID, url_norm: str
) -> Recipe | None:
    result = await db.execute(
        select(Recipe).where(
            Recipe.user_id == user_id,
            Recipe.source_url_norm == url_norm,
            Recipe.deleted_at.is_(None),
        )
    )
    return result.scalars().first()


async def create_import(
    db: AsyncSession,
    user: User,
    url: str,
    *,
    fetcher: PageFetcher,
    config: Settings = settings,
) -> Import:
    """Normalise, refuse the obvious, and record the attempt. Spends nothing."""
    cleaned = url.strip()
    if not cleaned:
        raise SemanticError("Geen link ontvangen.")

    await assert_quota_available(db, user, config)

    # Shortener resolution happens here rather than in the background task so that a link that is
    # simply dead fails while the user is still looking at the paste screen.
    url_norm = await normalise_url_async(cleaned, fetcher.resolve_redirect)
    platform = detect_platform(urlsplit(url_norm).netloc)

    if platform is SourcePlatform.pinterest:
        # Pinterest is a link aggregator: the Pin resolves to somebody else's page, and that is what
        # should be imported. Resolving it needs its own actor, which is Phase N.
        raise ImportFailedError(
            ImportErrorCode.unsupported_url,
            "Pinterest-links kunnen we nog niet openen. Deel de originele link.",
        )

    if existing := await _existing_recipe_for(db, user.id, url_norm):
        # Answered before anything is spent. The client turns this into "Je hebt dit recept al".
        raise ConflictError(
            "Dit recept staat al in je bibliotheek.",
            details={"recipe_id": str(existing.id), "title": existing.title},
        )

    record = Import(
        user_id=user.id,
        status=ImportStatus.queued,
        platform=platform,
        source_url=cleaned,
        source_url_norm=url_norm,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


# --- Running one -------------------------------------------------------------------------------


async def _event(
    db: AsyncSession, import_id: uuid.UUID, stage: str, state: str, detail: str | None = None
) -> None:
    db.add(ImportEvent(import_id=import_id, stage=stage, state=state, detail=detail))
    # Committed immediately: these rows exist to be read by a poller *while* the import runs, so
    # batching them until the end would defeat the entire point of having them.
    await db.commit()


class _Providers:
    """The three external boundaries, created per import and closed with it.

    One httpx client per import rather than a shared pool: an import is a rare, slow, foreground
    operation, so the connection reuse a shared client buys is worth less than not having a global
    to manage the lifetime of.
    """

    def __init__(self, config: Settings) -> None:
        self.fetcher = HttpxPageFetcher()
        self.runner: ActorRunner | None = (
            HttpxActorRunner(config.apify_token) if config.apify_token else None
        )
        self.completer: ChatCompleter | None = (
            HttpxChatCompleter(config.openai_api_key) if config.openai_api_key else None
        )

    async def aclose(self) -> None:
        await self.fetcher.aclose()
        for provider in (self.runner, self.completer):
            closer = getattr(provider, "aclose", None)
            if closer is not None:
                await closer()


async def run_import(import_id: uuid.UUID, *, config: Settings = settings) -> None:
    """The whole pipeline for one import. Never raises — every failure lands on the row."""
    started = time.monotonic()
    providers = _Providers(config)

    async with async_session_factory() as db:
        record = await db.get(Import, import_id)
        if record is None or record.status is not ImportStatus.queued:
            # Already running, already finished, or gone. Re-running would double-spend.
            await providers.aclose()
            return

        try:
            result, source = await _fetch_and_synthesise(db, record, providers, config)
        except ImportFailedError as exc:
            await _mark_failed(db, record, exc, started)
            await providers.aclose()
            return
        except Exception as exc:  # noqa: BLE001 — a crash must still leave a readable row
            await _mark_failed(
                db,
                record,
                ImportFailedError(
                    ImportErrorCode.scraper_failed,
                    "Er ging iets mis bij het importeren.",
                    details={"exception": type(exc).__name__},
                ),
                started,
            )
            await providers.aclose()
            return

        record.draft = {"recipe": result.model_dump(mode="json"), "source": source.as_draft()}
        record.status = ImportStatus.ready_for_review
        # Set here and nowhere else: a failed import cost money on Apify but produced nothing the
        # user can use, and charging quota for that is indefensible. docs/06 spells this out.
        record.counted_against_quota = True
        record.duration_ms = int((time.monotonic() - started) * 1000)
        record.completed_at = datetime.now(UTC)
        await db.commit()

    await providers.aclose()


async def _fetch_and_synthesise(
    db: AsyncSession, record: Import, providers: _Providers, config: Settings
) -> tuple[SynthesisResult, RecipeSource]:
    record.status = ImportStatus.fetching
    await db.commit()
    await _event(db, record.id, STAGE_FETCH, STATE_STARTED)

    url = record.source_url_norm or record.source_url or ""
    if record.platform in SOCIAL_PLATFORMS:
        if providers.runner is None:
            raise ImportFailedError(
                ImportErrorCode.unsupported_url, "Voor dit platform is geen importer ingesteld."
            )
        bundle = await fetch_social_evidence(url, url, record.platform, providers.runner, config)
    else:
        bundle = await fetch_and_extract(url, providers.fetcher)

    await _event(db, record.id, STAGE_FETCH, STATE_DONE, f"{bundle.evidence_chars()} tekens")

    if providers.completer is None:
        raise ImportFailedError(
            ImportErrorCode.model_failed, "Importeren is tijdelijk niet beschikbaar."
        )

    record.status = ImportStatus.synthesizing
    await db.commit()
    await _event(db, record.id, STAGE_SYNTHESIZE, STATE_STARTED)
    result = await synthesise(bundle, providers.completer, config)
    await _event(db, record.id, STAGE_SYNTHESIZE, STATE_DONE, result.title)

    await _event(db, record.id, STAGE_VALIDATE, STATE_STARTED)
    result = validate(result)
    await _event(db, record.id, STAGE_VALIDATE, STATE_DONE)

    return result, RecipeSource.from_bundle(bundle)


async def _mark_failed(
    db: AsyncSession, record: Import, exc: ImportFailedError, started: float
) -> None:
    record.status = ImportStatus.failed
    record.error_code = str(exc.code)
    record.error_detail = exc.message
    record.duration_ms = int((time.monotonic() - started) * 1000)
    record.completed_at = datetime.now(UTC)
    await db.commit()
    await _event(db, record.id, STAGE_FETCH, STATE_FAILED, str(exc.code))


# --- Reading and finishing ---------------------------------------------------------------------


async def get_import(
    db: AsyncSession, user_id: uuid.UUID, import_id: uuid.UUID
) -> tuple[Import, list[ImportEvent]]:
    record = await db.get(Import, import_id)
    if record is None or record.user_id != user_id:
        raise NotFoundError("Deze import bestaat niet.")

    events = await db.execute(
        select(ImportEvent).where(ImportEvent.import_id == import_id).order_by(ImportEvent.id)
    )
    return record, list(events.scalars().all())


async def patch_draft(
    db: AsyncSession, user_id: uuid.UUID, import_id: uuid.UUID, patch: dict[str, Any]
) -> Import:
    """Apply the user's review edits to the draft recipe.

    A shallow merge over the recipe object, and re-validated afterwards: the review screen is where
    someone types "2 kilo" into a field, and the same rules that guard model output should guard
    hand-typed values.
    """
    record, _ = await get_import(db, user_id, import_id)
    if record.status is not ImportStatus.ready_for_review:
        raise SemanticError("Deze import kan niet meer worden aangepast.")

    draft = dict(record.draft or {})
    recipe = {**dict(draft.get("recipe") or {}), **patch}

    try:
        revalidated = validate(SynthesisResult.model_validate(recipe))
    except ImportFailedError as exc:
        raise SemanticError(exc.message, details=exc.details) from exc

    draft["recipe"] = revalidated.model_dump(mode="json")
    # Reassigned rather than mutated: SQLAlchemy does not track changes inside a JSONB dict, so an
    # in-place edit would be committed as a no-op and silently lost.
    record.draft = draft
    await db.commit()
    await db.refresh(record)
    return record


async def save_import(db: AsyncSession, user_id: uuid.UUID, import_id: uuid.UUID) -> Recipe:
    """Materialise the draft into the library. The first moment anything reaches `recipes`."""
    record, _ = await get_import(db, user_id, import_id)

    if record.recipe_id is not None:
        # Idempotent: a double-tap on Opslaan, or a retry after a dropped response, must not create
        # a second copy of the same recipe.
        existing = await db.get(Recipe, record.recipe_id)
        if existing is not None:
            return existing

    if record.status is not ImportStatus.ready_for_review or not record.draft:
        raise SemanticError("Deze import is niet klaar om op te slaan.")

    draft = record.draft
    result = SynthesisResult.model_validate(draft.get("recipe") or {})
    source = RecipeSource.from_draft(dict(draft.get("source") or {}))

    recipe = await materialise(db, user_id, result, source, import_id=record.id)
    record.recipe_id = recipe.id
    record.status = ImportStatus.saved
    await db.commit()
    await db.refresh(recipe)
    return recipe
