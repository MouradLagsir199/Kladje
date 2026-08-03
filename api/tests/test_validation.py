"""M10 — deterministic repair after the model.

Pure functions, no DB, no network. Every case here is a rule from §2.5 of the workplan, and the two
marked as such came from a real import that passed the JSON schema untouched.
"""

from typing import Any

import pytest

from receptenapp.core.errors import ImportErrorCode, ImportFailedError
from receptenapp.schemas.synthesis import SynthesisResult
from receptenapp.services.validation import validate


def ingredient(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "pos": 1,
        "section": None,
        "amount": 200,
        "amount_max": None,
        "unit": "g",
        "name_nl": "spaghetti",
        "qualifier": None,
        "category": "houdbaar",
        "optional": False,
        "raw": "200 g spaghetti",
        "orig_amount": None,
        "orig_unit": None,
        "prov": "explicit",
    }
    base.update(overrides)
    return base


def step(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "pos": 1,
        "text": "Kook de pasta.",
        "timer_seconds": None,
        "temperature_c": None,
        "ingredient_pos": [1],
        "prov": "explicit",
    }
    base.update(overrides)
    return base


def result(**overrides: Any) -> SynthesisResult:
    base: dict[str, Any] = {
        "found": True,
        "confidence": "high",
        "title": "Pasta",
        "description": None,
        "meal_types": ["diner"],
        "servings": 4,
        "prep_minutes": 10,
        "cook_minutes": 15,
        "difficulty": "makkelijk",
        "oven_c": None,
        "ingredients": [ingredient(), ingredient(pos=2, name_nl="pesto", unit="el", amount=4)],
        "steps": [step(), step(pos=2, text="Roer de pesto erdoor.", ingredient_pos=[2])],
        "field_provenance": {
            "title": "explicit",
            "servings": "explicit",
            "prep_minutes": "explicit",
            "cook_minutes": "explicit",
            "oven_c": "missing",
            "difficulty": "derived",
        },
        "missing": [],
    }
    base.update(overrides)
    return SynthesisResult.model_validate(base)


def test_a_good_recipe_passes_through_unchanged() -> None:
    original = result()
    assert validate(original).servings == 4
    assert len(validate(original).ingredients) == 2


# --- The two that came from a real import ------------------------------------------------------


def test_a_yield_masquerading_as_servings_is_dropped_not_clamped() -> None:
    """A real taco import returned `servings: 18` — the yield in pieces, read as people.

    18 is inside the schema's 1-24 range, so nothing rejected it and the detail screen would have
    shown "18 pers." as fact. Clamping to 24 would swap one wrong number for another that looks
    deliberate; the honest answer is no number and a prompt to fill it in.
    """
    validated = validate(result(servings=18))

    assert validated.servings is None
    assert validated.field_provenance.servings == "missing"
    assert "servings" in validated.missing


def test_a_measure_with_no_amount_loses_the_unit() -> None:
    """Same import: `unit: ml` for "groente olie" with no amount, because the source never said."""
    validated = validate(
        result(
            ingredients=[
                ingredient(),
                ingredient(pos=2, name_nl="groente olie", unit="ml", amount=None),
            ]
        )
    )
    oil = next(i for i in validated.ingredients if i.name_nl == "groente olie")
    assert oil.unit is None


@pytest.mark.parametrize("unit", ["snuf", "handvol", "naar_smaak", "teentje"])
def test_a_vague_unit_survives_without_an_amount(unit: str) -> None:
    """ "snuf zout" and "handvol rucola" read perfectly without a number — only measures don't."""
    validated = validate(
        result(
            ingredients=[ingredient(), ingredient(pos=2, name_nl="zout", unit=unit, amount=None)]
        )
    )
    assert validated.ingredients[1].unit == unit


# --- Clamps ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("field", "given", "expected"),
    [
        ("prep_minutes", 99999, 1440),
        ("cook_minutes", -5, 0),
        ("oven_c", 900, 300),
        ("oven_c", 5, 40),
    ],
)
def test_implausible_scalars_are_clamped(field: str, given: int, expected: int) -> None:
    assert getattr(validate(result(**{field: given})), field) == expected


def test_a_step_temperature_is_clamped_too() -> None:
    validated = validate(result(steps=[step(temperature_c=850), step(pos=2)]))
    assert validated.steps[0].temperature_c == 300


# --- Rounding ----------------------------------------------------------------------------------


def test_a_fractional_egg_becomes_a_range() -> None:
    validated = validate(
        result(
            ingredients=[
                ingredient(),
                ingredient(pos=2, name_nl="ei", unit="stuk", amount=1.33),
            ]
        )
    )
    egg = next(i for i in validated.ingredients if i.name_nl == "ei")
    assert (egg.amount, egg.amount_max) == (1, 2)


def test_a_whole_countable_is_left_alone() -> None:
    validated = validate(
        result(ingredients=[ingredient(), ingredient(pos=2, name_nl="ei", unit="stuk", amount=3)])
    )
    egg = next(i for i in validated.ingredients if i.name_nl == "ei")
    assert (egg.amount, egg.amount_max) == (3, None)


def test_a_fractional_weight_is_not_rounded() -> None:
    # 1.5 kg is a perfectly measurable quantity; only countable things resist halving.
    validated = validate(
        result(
            ingredients=[
                ingredient(),
                ingredient(pos=2, name_nl="aardappel", unit="kg", amount=1.5),
            ]
        )
    )
    potato = next(i for i in validated.ingredients if i.name_nl == "aardappel")
    assert potato.amount == 1.5


# --- Deduplication -----------------------------------------------------------------------------


def test_duplicate_ingredients_are_merged_and_summed() -> None:
    """Transcripts cause this: oil named once at the start and again for the sauce.

    Two rows would make the shopping list buy twice as much.
    """
    validated = validate(
        result(
            ingredients=[
                ingredient(pos=1, name_nl="olijfolie", unit="el", amount=2, raw="2 el olie"),
                ingredient(pos=2, name_nl="Olijfolie ", unit="el", amount=1, raw="1 el olie"),
                ingredient(pos=3, name_nl="pasta", unit="g", amount=300),
            ]
        )
    )
    oil = next(i for i in validated.ingredients if i.name_nl.strip().lower() == "olijfolie")

    assert oil.amount == 3
    # Summing two stated amounts is a computation, so the result cannot claim to be explicit.
    assert oil.prov == "derived"
    assert len(validated.ingredients) == 2


def test_the_same_name_in_a_different_unit_is_not_merged() -> None:
    # 200 g tomatoes and 1 blikje tomatoes are different shopping-list lines.
    validated = validate(
        result(
            ingredients=[
                ingredient(pos=1, name_nl="tomaten", unit="g", amount=200),
                ingredient(pos=2, name_nl="tomaten", unit="blikje", amount=1),
            ]
        )
    )
    assert len(validated.ingredients) == 2


def test_unsummable_duplicates_are_both_kept() -> None:
    # "snuf zout" twice is not "2 snuf zout", and guessing is worse than keeping both.
    validated = validate(
        result(
            ingredients=[
                ingredient(pos=1, name_nl="zout", unit="snuf", amount=None),
                ingredient(pos=2, name_nl="zout", unit="snuf", amount=None),
            ]
        )
    )
    assert len(validated.ingredients) == 2


def test_positions_are_dense_after_merging() -> None:
    validated = validate(
        result(
            ingredients=[
                ingredient(pos=1, name_nl="olie", unit="el", amount=1),
                ingredient(pos=2, name_nl="olie", unit="el", amount=1),
                ingredient(pos=3, name_nl="pasta", unit="g", amount=300),
                ingredient(pos=9, name_nl="pesto", unit="el", amount=2),
            ]
        )
    )
    assert [i.pos for i in validated.ingredients] == [1, 2, 3]


def test_a_step_pointing_at_a_merged_away_ingredient_drops_the_reference() -> None:
    """Cook mode reads `ingredient_ids` directly, so a dangling position becomes a phantom pill."""
    validated = validate(
        result(
            ingredients=[
                ingredient(pos=1, name_nl="olie", unit="el", amount=1),
                ingredient(pos=2, name_nl="olie", unit="el", amount=1),
                ingredient(pos=3, name_nl="pasta", unit="g", amount=300),
            ],
            steps=[step(ingredient_pos=[1, 2, 3, 47])],
        )
    )
    assert validated.steps[0].ingredient_pos == [1, 2]


# --- Minimum viability -------------------------------------------------------------------------


def test_one_ingredient_is_not_a_recipe() -> None:
    with pytest.raises(ImportFailedError) as caught:
        validate(result(ingredients=[ingredient()]))
    assert caught.value.error_code is ImportErrorCode.low_confidence


def test_no_steps_is_not_a_recipe() -> None:
    with pytest.raises(ImportFailedError) as caught:
        validate(result(steps=[]))
    assert caught.value.error_code is ImportErrorCode.low_confidence


def test_viability_is_judged_after_merging_not_before() -> None:
    """Three rows that collapse to two are still a recipe.

    Checking before the merge would pass a recipe that is really one ingredient; checking after and
    rejecting on the pre-merge count would fail a perfectly good one.
    """
    validated = validate(
        result(
            ingredients=[
                ingredient(pos=1, name_nl="olie", unit="el", amount=1),
                ingredient(pos=2, name_nl="olie", unit="el", amount=1),
                ingredient(pos=3, name_nl="pasta", unit="g", amount=300),
            ]
        )
    )
    assert len(validated.ingredients) == 2


def test_a_single_ingredient_duplicated_is_still_rejected() -> None:
    with pytest.raises(ImportFailedError):
        validate(
            result(
                ingredients=[
                    ingredient(pos=1, name_nl="olie", unit="el", amount=1),
                    ingredient(pos=2, name_nl="olie", unit="el", amount=2),
                ]
            )
        )
