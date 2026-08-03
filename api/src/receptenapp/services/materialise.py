"""Turn a `SynthesisResult` into rows in the database.

The one place model output becomes durable data, so it is also the last place a bad value can be
stopped. Three things happen here that the model cannot do for itself:

  - positions are reassigned from the model's `pos` to a dense 0..n-1 sequence, because `pos`
    is only a hint and a repeated one would violate the unique constraint;
  - `ingredient_pos` becomes real ingredient ids, which requires the ingredients to exist first;
  - the fan-oven temperature is computed, which the prompt explicitly forbids the model from doing.
"""

import decimal
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from receptenapp.db.models import (
    Recipe,
    RecipeIngredient,
    RecipeStep,
    SourcePlatform,
)
from receptenapp.schemas.synthesis import SynthesisResult
from receptenapp.services.evidence import EvidenceBundle

# A fan oven runs 20 °C cooler for the same result. One rule, applied once, rather than asking the
# model to do arithmetic it has no reason to be good at — see docs/11-prompts.md.
FAN_OVEN_OFFSET_C = 20

DEFAULT_SERVINGS = 2


def _decimal(value: float | None) -> decimal.Decimal | None:
    """Numeric(10, 2) — quantise here rather than letting the driver decide how to round."""
    if value is None:
        return None
    return decimal.Decimal(str(value)).quantize(decimal.Decimal("0.01"))


def fan_temperature(temperature_c: int | None) -> int | None:
    if temperature_c is None:
        return None
    return max(temperature_c - FAN_OVEN_OFFSET_C, 0)


@dataclass(frozen=True, slots=True)
class RecipeSource:
    """Just the attribution fields, lifted out of the evidence.

    Separate from `EvidenceBundle` because a draft has to survive in `imports.draft` between the
    import and the user pressing Opslaan, and carrying a 24 000-character page extract through that
    round trip to reach five strings would be absurd.
    """

    platform: SourcePlatform
    url: str | None
    url_norm: str | None
    author: str | None
    title: str | None

    @classmethod
    def from_bundle(cls, bundle: EvidenceBundle) -> "RecipeSource":
        return cls(
            platform=bundle.platform,
            url=bundle.url,
            url_norm=bundle.url_norm,
            author=bundle.author,
            title=bundle.title,
        )

    @classmethod
    def from_draft(cls, data: dict[str, Any]) -> "RecipeSource":
        return cls(
            platform=SourcePlatform(data.get("platform") or SourcePlatform.manual),
            url=data.get("url"),
            url_norm=data.get("url_norm"),
            author=data.get("author"),
            title=data.get("title"),
        )

    def as_draft(self) -> dict[str, Any]:
        return {
            "platform": str(self.platform),
            "url": self.url,
            "url_norm": self.url_norm,
            "author": self.author,
            "title": self.title,
        }


async def materialise(
    db: AsyncSession,
    user_id: uuid.UUID,
    result: SynthesisResult,
    source: RecipeSource,
    *,
    import_id: uuid.UUID | None = None,
) -> Recipe:
    """Write the recipe, its ingredients and its steps. Caller owns the transaction."""
    recipe = Recipe(
        user_id=user_id,
        import_id=import_id,
        title=result.title,
        description=result.description,
        meal_types=result.meal_types,
        # `servings` is NOT NULL. A missing serving count is recorded as the household default
        # rather than a guess; `field_provenance.servings` is what says it was never stated.
        servings=result.servings or DEFAULT_SERVINGS,
        prep_minutes=result.prep_minutes,
        cook_minutes=result.cook_minutes,
        difficulty=result.difficulty,
        source_platform=source.platform,
        source_url=source.url,
        source_url_norm=source.url_norm,
        source_author=source.author,
        source_title=source.title,
        # Migration 003 gave this a home. Without it the detail screen cannot tell a stated serving
        # count from an inferred one, which is the distinction the whole provenance design exists
        # to show.
        field_provenance=result.field_provenance.model_dump(mode="json"),
    )
    db.add(recipe)
    await db.flush()

    # Sorted by the model's own numbering, then renumbered densely. Trusting `pos` to be unique and
    # gap-free is how you get a unique-constraint violation on someone's first import.
    ingredient_ids: dict[int, uuid.UUID] = {}
    for position, item in enumerate(sorted(result.ingredients, key=lambda i: i.pos)):
        row = RecipeIngredient(
            recipe_id=recipe.id,
            position=position,
            section=item.section,
            amount=_decimal(item.amount),
            amount_max=_decimal(item.amount_max),
            unit=item.unit,
            name_nl=item.name_nl,
            qualifier=item.qualifier,
            category=item.category,
            optional=item.optional,
            raw_text=item.raw,
            original_amount=_decimal(item.orig_amount),
            original_unit=item.orig_unit,
            provenance=item.prov,
        )
        db.add(row)
        await db.flush()
        ingredient_ids[item.pos] = row.id

    for position, step in enumerate(sorted(result.steps, key=lambda s: s.pos)):
        db.add(
            RecipeStep(
                recipe_id=recipe.id,
                position=position,
                text_=step.text,
                timer_seconds=step.timer_seconds,
                temperature_c=step.temperature_c,
                temperature_fan_c=fan_temperature(step.temperature_c),
                # Unknown positions are dropped rather than stored as dangling references: cook
                # mode reads this array directly and would show an ingredient that does not exist.
                ingredient_ids=[
                    ingredient_ids[pos] for pos in step.ingredient_pos if pos in ingredient_ids
                ],
                provenance=step.prov,
            )
        )

    return recipe
