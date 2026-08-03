"""What the model is allowed to hand back — the Pydantic side of docs/11-prompts.md's schema.

Two layers guard the same values on purpose. The JSON schema sent to OpenAI carries the types,
the enums and `additionalProperties: false`, because those are what actually shape generation.
The numeric bounds live here and in `services/validation.py` instead: a range keyword the API does
not recognise fails the whole call with a 400, while a range checked after the fact just clamps.

Field names are the short ones from the prompt (`prov`, `raw`, `pos`). Output tokens are the cost
driver, and every character of every key is paid for on every ingredient row.
"""

import enum

from pydantic import BaseModel, ConfigDict, Field

from receptenapp.db.models import (
    Difficulty,
    MealType,
    Provenance,
    ShelfCategory,
    Unit,
)


class Confidence(enum.StrEnum):
    high = "high"
    medium = "medium"
    low = "low"


class SynthIngredient(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pos: int
    section: str | None = None
    amount: float | None = None
    amount_max: float | None = None
    unit: Unit | None = None
    name_nl: str
    qualifier: str | None = None
    category: ShelfCategory
    optional: bool = False
    # The one field the model must echo from the source, against the general rule of not paying to
    # repeat input back. Only the model can segment source text into per-ingredient strings, and
    # without `raw` a wrong conversion is undebuggable six weeks later.
    raw: str
    orig_amount: float | None = None
    orig_unit: str | None = None
    prov: Provenance


class SynthStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pos: int
    text: str
    timer_seconds: int | None = None
    temperature_c: int | None = None
    # Positions, not ids — the model has never seen a UUID. Mapped after insert.
    ingredient_pos: list[int] = Field(default_factory=list)
    prov: Provenance


class FieldProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Provenance
    servings: Provenance
    prep_minutes: Provenance
    cook_minutes: Provenance
    oven_c: Provenance
    difficulty: Provenance


class SynthesisResult(BaseModel):
    """One recipe as the model sees it, before validation and before it touches the database."""

    model_config = ConfigDict(extra="forbid")

    found: bool
    confidence: Confidence

    title: str
    description: str | None = None
    meal_types: list[MealType] = Field(default_factory=list)
    servings: int | None = None
    prep_minutes: int | None = None
    cook_minutes: int | None = None
    difficulty: Difficulty | None = None
    oven_c: int | None = None

    ingredients: list[SynthIngredient] = Field(default_factory=list)
    steps: list[SynthStep] = Field(default_factory=list)
    field_provenance: FieldProvenance
    missing: list[str] = Field(default_factory=list)
