from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from receptenapp.core.security import get_current_user
from receptenapp.db.models import User
from receptenapp.db.session import get_db
from receptenapp.schemas.user import (
    MeResponse,
    PreferencesOut,
    PreferencesUpdate,
    UserOut,
    UserUpdate,
)
from receptenapp.services import users as users_service

router = APIRouter(prefix="/v1/me", tags=["me"])


@router.get("")
async def get_me(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> MeResponse:
    return await users_service.build_me_response(db, user)


@router.patch("")
async def patch_me(
    data: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    updated = await users_service.update_profile(db, user, data)
    return UserOut.model_validate(updated)


@router.patch("/preferences")
async def patch_me_preferences(
    data: PreferencesUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PreferencesOut:
    updated = await users_service.update_preferences(db, user.id, data)
    return PreferencesOut.model_validate(updated)
