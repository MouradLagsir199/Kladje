import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from receptenapp.db.models import PlanTier


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str | None
    email_verified: bool
    display_name: str | None
    avatar_url: str | None
    household_size: int
    locale: str
    tier: PlanTier
    created_at: datetime


class UserUpdate(BaseModel):
    display_name: str | None = None
    household_size: int | None = Field(default=None, ge=1, le=20)


class PreferencesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    diets: list[str]
    allergens: list[str]
    default_servings: int
    show_original_units: bool
    fan_oven_default: bool
    notif_cooking: bool
    notif_defrost: bool
    notif_group: bool
    updated_at: datetime


class PreferencesUpdate(BaseModel):
    diets: list[str] | None = None
    allergens: list[str] | None = None
    default_servings: int | None = Field(default=None, ge=1, le=20)
    show_original_units: bool | None = None
    fan_oven_default: bool | None = None
    notif_cooking: bool | None = None
    notif_defrost: bool | None = None
    notif_group: bool | None = None


class QuotaOut(BaseModel):
    used: int
    limit: int
    resets_at: datetime | None
    tier: PlanTier


class MeResponse(BaseModel):
    user: UserOut
    preferences: PreferencesOut
    quota: QuotaOut
