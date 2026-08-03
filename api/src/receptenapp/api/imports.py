import uuid
from collections.abc import Sequence

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from receptenapp.api.recipes import to_detail
from receptenapp.core.security import get_current_user
from receptenapp.db.models import Import, ImportEvent, User
from receptenapp.db.session import get_db
from receptenapp.providers.http import HttpxPageFetcher
from receptenapp.schemas.import_ import (
    DraftPatch,
    ImportCreate,
    ImportEventOut,
    ImportOut,
)
from receptenapp.schemas.recipe import RecipeDetail
from receptenapp.services import imports as imports_service
from receptenapp.services import recipes as recipes_service

router = APIRouter(prefix="/v1/imports", tags=["imports"])


def _out(record: Import, events: Sequence[ImportEvent] = ()) -> ImportOut:
    out = ImportOut.model_validate(record)
    return out.model_copy(
        update={"events": [ImportEventOut.model_validate(event) for event in events]}
    )


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_import(
    data: ImportCreate,
    background: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ImportOut:
    """Accept the link and start work. Returns before the import finishes.

    202 rather than 201: an import takes tens of seconds, and holding the connection open for it
    would put the progress screen at the mercy of every proxy timeout between here and the phone.
    The client polls `GET /v1/imports/{id}`.
    """
    fetcher = HttpxPageFetcher()
    try:
        record = await imports_service.create_import(db, user, data.url, fetcher=fetcher)
    finally:
        # Only used for shortener resolution during creation; the background task opens its own.
        await fetcher.aclose()

    background.add_task(imports_service.run_import, record.id)
    return _out(record)


@router.get("/{import_id}")
async def get_import(
    import_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ImportOut:
    record, events = await imports_service.get_import(db, user.id, import_id)
    return _out(record, events)


@router.patch("/{import_id}/draft")
async def patch_draft(
    import_id: uuid.UUID,
    patch: DraftPatch,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ImportOut:
    record = await imports_service.patch_draft(
        db, user.id, import_id, patch.model_dump(exclude_unset=True)
    )
    return _out(record)


@router.post("/{import_id}/save", status_code=status.HTTP_201_CREATED)
async def save_import(
    import_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RecipeDetail:
    """Materialise the draft and hand back the finished recipe.

    Returns the full recipe rather than just an id so the done screen and the detail screen behind
    it have everything they need without a second round trip.
    """
    recipe = await imports_service.save_import(db, user.id, import_id)
    found = await recipes_service.get_recipe(db, user.id, recipe.id)
    return to_detail(found)
