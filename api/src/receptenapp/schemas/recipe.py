import decimal
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from receptenapp.db.models import (
    Difficulty,
    MealType,
    Provenance,
    ShelfCategory,
    SourcePlatform,
    Unit,
)


class IngredientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    position: int
    section: str | None
    amount: decimal.Decimal | None
    amount_max: decimal.Decimal | None
    unit: Unit | None
    name_nl: str
    qualifier: str | None
    category: ShelfCategory
    optional: bool
    # Kept in the response on purpose: the client shows "wat de bron zei" under a converted line,
    # and without the raw text there is nothing to fall back on when a parse looks wrong.
    raw_text: str
    original_amount: decimal.Decimal | None
    original_unit: str | None
    provenance: Provenance


class StepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    position: int
    # The model attribute is `text_`; the column and the wire field are both `text`.
    text: str = Field(validation_alias="text_")
    timer_seconds: int | None
    temperature_c: int | None
    temperature_fan_c: int | None
    ingredient_ids: list[uuid.UUID]
    provenance: Provenance


class RecipeSummary(BaseModel):
    """One row in the library. Deliberately without ingredients and steps — a library of 200
    recipes should not ship 3000 ingredient rows to render a grid of thumbnails."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    image_url: str | None = None
    meal_types: list[MealType]
    servings: int
    prep_minutes: int | None
    cook_minutes: int | None
    difficulty: Difficulty | None
    source_platform: SourcePlatform
    source_author: str | None
    cooked_count: int
    created_at: datetime


class RecipeDetail(RecipeSummary):
    description: str | None
    kcal_per_serving: int | None
    source_url: str | None
    source_title: str | None
    notes: str | None
    last_cooked_at: datetime | None
    # Provenance for the recipe's own scalar fields, as `{field: provenance}`. Null on recipes
    # written before migration 003 — those genuinely do not know, and `{}` would claim otherwise.
    field_provenance: dict[str, str] | None = None
    ingredients: list[IngredientOut]
    steps: list[StepOut]


class RecipeList(BaseModel):
    items: list[RecipeSummary]
    next_cursor: str | None = None
