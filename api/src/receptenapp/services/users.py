import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from receptenapp.db.models import PlanTier, User, UserPreferences
from receptenapp.schemas.user import (
    MeResponse,
    PreferencesOut,
    PreferencesUpdate,
    QuotaOut,
    UserOut,
    UserUpdate,
)

_FREE_MONTHLY_LIMIT = 10
_PREMIUM_MONTHLY_LIMIT = 100


async def get_or_create_preferences(db: AsyncSession, user_id: uuid.UUID) -> UserPreferences:
    result = await db.execute(select(UserPreferences).where(UserPreferences.user_id == user_id))
    preferences = result.scalar_one_or_none()
    if preferences is not None:
        return preferences

    preferences = UserPreferences(user_id=user_id)
    db.add(preferences)
    await db.commit()
    await db.refresh(preferences)
    return preferences


def _quota_stub(tier: PlanTier) -> QuotaOut:
    """No import usage is tracked until Phase 1's imports table lands (docs/06-monetisation.md),
    so this always reports zero used against the tier's rolling/monthly limit."""
    limit = _FREE_MONTHLY_LIMIT if tier == PlanTier.free else _PREMIUM_MONTHLY_LIMIT
    return QuotaOut(used=0, limit=limit, resets_at=None, tier=tier)


async def build_me_response(db: AsyncSession, user: User) -> MeResponse:
    preferences = await get_or_create_preferences(db, user.id)
    return MeResponse(
        user=UserOut.model_validate(user),
        preferences=PreferencesOut.model_validate(preferences),
        quota=_quota_stub(user.tier),
    )


async def update_profile(db: AsyncSession, user: User, data: UserUpdate) -> User:
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user


async def update_preferences(
    db: AsyncSession, user_id: uuid.UUID, data: PreferencesUpdate
) -> UserPreferences:
    preferences = await get_or_create_preferences(db, user_id)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(preferences, field, value)
    await db.commit()
    await db.refresh(preferences)
    return preferences
