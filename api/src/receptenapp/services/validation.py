"""Stage 4 of the import pipeline — deterministic repair, after the model, before the user.

Cheap insurance against a small model's bad day. Everything here is a rule that does not need
judgement, which is exactly why it does not belong in a prompt: asking a model to remember to clamp
servings costs tokens on every import and still fails sometimes.

The two rules with a story attached are `_plausible_servings` and `_drop_meaningless_unit`. Both
came from a single real TikTok that passed the JSON schema untouched.
"""

import re
from collections import OrderedDict

from receptenapp.core.errors import ImportErrorCode, ImportFailedError
from receptenapp.db.models import Provenance, ShelfCategory, Unit
from receptenapp.schemas.synthesis import SynthesisResult, SynthIngredient, SynthStep

MIN_SERVINGS, MAX_SERVINGS = 1, 24
MIN_MINUTES, MAX_MINUTES = 0, 1440
MIN_OVEN_C, MAX_OVEN_C = 40, 300

MIN_INGREDIENTS = 2
MIN_STEPS = 1

# Units that mean nothing without a number. "ml olie" is not a line anyone writes; "snuf zout" is.
MEASURES_NEEDING_AN_AMOUNT = frozenset({Unit.g, Unit.kg, Unit.ml, Unit.l, Unit.el, Unit.tl})

# Units counted in whole things. Half a clove of garlic is not a measurement anyone can act on.
COUNTABLE_UNITS = frozenset({Unit.stuk, Unit.teentje, Unit.plak, Unit.blikje, Unit.pakje})

# A serving count this high is nearly always the yield in pieces rather than people — "makes 18
# tacos" read as "serves 18". Above it we drop the number instead of clamping to 24, because
# clamping would replace one wrong answer with a different wrong answer that looks deliberate.
IMPLAUSIBLE_SERVINGS_ABOVE = 12

_WHITESPACE_RE = re.compile(r"\s+")


def _clamp(value: int | None, low: int, high: int) -> int | None:
    if value is None:
        return None
    return max(low, min(high, value))


def _normalise_name(name: str) -> str:
    return _WHITESPACE_RE.sub(" ", name).strip().lower()


def _plausible_servings(result: SynthesisResult) -> tuple[int | None, Provenance]:
    """Servings, or nothing at all when the number cannot be believed.

    A real import returned `servings: 18` for a taco recipe — inside the schema's 1–24 range, so
    nothing rejected it, and the detail screen would have shown "18 pers." as fact. An empty field
    the user fills in is fine; a plausible wrong number is the failure this whole design exists to
    prevent, because the user has no way to know it was wrong.
    """
    servings = result.servings
    if servings is None:
        return None, Provenance.missing
    if servings < MIN_SERVINGS or servings > IMPLAUSIBLE_SERVINGS_ABOVE:
        return None, Provenance.missing
    return servings, result.field_provenance.servings


def _drop_meaningless_unit(item: SynthIngredient) -> SynthIngredient:
    """A measure with no amount is noise. The same TikTok produced `unit: ml` for "groente olie"
    with `amount: null`, because the source never said how much."""
    if item.amount is None and item.unit in MEASURES_NEEDING_AN_AMOUNT:
        return item.model_copy(update={"unit": None})
    return item


def _round_countable(item: SynthIngredient) -> SynthIngredient:
    """Never show a fractional egg. `1.33 ei` becomes `1–2`."""
    if item.unit not in COUNTABLE_UNITS or item.amount is None:
        return item
    if float(item.amount).is_integer():
        return item

    low = max(1, int(item.amount))
    high = low + 1
    # An existing amount_max is the model's own range and is left alone; this only fills a gap.
    return item.model_copy(update={"amount": low, "amount_max": item.amount_max or high})


def _repair_category(item: SynthIngredient) -> SynthIngredient:
    """`category` drives the shopping list's aisle grouping, so an unknown value gets a home rather
    than failing the import. Pydantic has already rejected anything outside the enum, which leaves
    this as a guard for the day the enum grows."""
    if item.category not in set(ShelfCategory):
        return item.model_copy(update={"category": ShelfCategory.overig})
    return item


def _merge_duplicates(items: list[SynthIngredient]) -> list[SynthIngredient]:
    """Fold rows with the same name and unit together, summing the amounts.

    Transcripts cause this constantly: a cook says "olive oil" at the start and again for the sauce,
    and two `2 el olijfolie` rows become a shopping list that buys twice as much. Rows where either
    side has no amount are left alone — 'snuf zout' twice is not '2 snuf zout'.
    """
    merged: OrderedDict[tuple[str, str | None], SynthIngredient] = OrderedDict()

    for item in items:
        key = (_normalise_name(item.name_nl), str(item.unit) if item.unit else None)
        existing = merged.get(key)

        if existing is None:
            merged[key] = item
            continue
        if existing.amount is None or item.amount is None:
            # Not summable, and not worth guessing at. Keep both by giving this one its own key.
            merged[(key[0], f"{key[1]}#{len(merged)}")] = item
            continue

        merged[key] = existing.model_copy(
            update={
                "amount": existing.amount + item.amount,
                # A range plus a range is not a range we can defend, so it collapses to the sum.
                "amount_max": None,
                "raw": f"{existing.raw} + {item.raw}",
                # Summing two stated amounts is a computation, so the result is derived even when
                # both inputs were explicit.
                "prov": Provenance.derived,
            }
        )

    return [
        item.model_copy(update={"pos": index + 1}) for index, item in enumerate(merged.values())
    ]


def _clean_step(step: SynthStep, allowed: set[int]) -> SynthStep:
    return step.model_copy(
        update={
            "temperature_c": _clamp(step.temperature_c, MIN_OVEN_C, MAX_OVEN_C),
            "timer_seconds": _clamp(step.timer_seconds, 0, MAX_MINUTES * 60),
            # Positions the model invented, or ones that vanished in the merge above, would render
            # as ingredients that are not in the recipe.
            "ingredient_pos": [pos for pos in step.ingredient_pos if pos in allowed],
        }
    )


def validate(result: SynthesisResult) -> SynthesisResult:
    """Repair what can be repaired, drop what cannot be believed, reject what is hollow."""
    ingredients = [
        _round_countable(_repair_category(_drop_meaningless_unit(item)))
        for item in sorted(result.ingredients, key=lambda i: i.pos)
    ]
    ingredients = _merge_duplicates(ingredients)

    allowed = {item.pos for item in ingredients}
    steps = [
        step.model_copy(update={"pos": index + 1})
        for index, step in enumerate(
            _clean_step(step, allowed) for step in sorted(result.steps, key=lambda s: s.pos)
        )
    ]

    # Checked after repair, not before: dropping a duplicate should not be able to turn a viable
    # recipe into a rejected one, but a recipe that was only ever one ingredient must not pass.
    if len(ingredients) < MIN_INGREDIENTS or len(steps) < MIN_STEPS:
        raise ImportFailedError(
            ImportErrorCode.low_confidence,
            "We konden hier geen volledig recept uit halen.",
            details={"ingredients": len(ingredients), "steps": len(steps)},
        )

    servings, servings_provenance = _plausible_servings(result)
    missing = set(result.missing)
    if servings is None:
        missing.add("servings")

    return result.model_copy(
        update={
            "servings": servings,
            "prep_minutes": _clamp(result.prep_minutes, MIN_MINUTES, MAX_MINUTES),
            "cook_minutes": _clamp(result.cook_minutes, MIN_MINUTES, MAX_MINUTES),
            "oven_c": _clamp(result.oven_c, MIN_OVEN_C, MAX_OVEN_C),
            "ingredients": ingredients,
            "steps": steps,
            "field_provenance": result.field_provenance.model_copy(
                update={"servings": servings_provenance}
            ),
            "missing": sorted(missing),
        }
    )
