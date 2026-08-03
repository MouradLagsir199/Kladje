"""M9 — the synthesis service. Never touches a paid API; `StubChatCompleter` stands in."""

from typing import Any

import pytest

from receptenapp.core.errors import ImportErrorCode, ImportFailedError
from receptenapp.db.models import SourcePlatform
from receptenapp.providers.openai import StubChatCompleter
from receptenapp.services.evidence import EvidenceBundle, TranscriptSegment
from receptenapp.services.prompts import get_prompt
from receptenapp.services.synthesis import MAX_PAGE_CHARS, MAX_TRANSCRIPT_CHARS, synthesise
from tests.support import make_settings

GOOD_RESULT: dict[str, Any] = {
    "found": True,
    "confidence": "medium",
    "title": "Simpele boterkoekjes",
    "description": None,
    "meal_types": ["tussendoor"],
    "servings": None,
    "prep_minutes": None,
    "cook_minutes": None,
    "difficulty": "makkelijk",
    "oven_c": None,
    "ingredients": [
        {
            "pos": 1,
            "section": None,
            "amount": 250,
            "amount_max": None,
            "unit": "g",
            "name_nl": "bloem",
            "qualifier": None,
            "category": "houdbaar",
            "optional": False,
            "raw": "two cups of flour",
            "orig_amount": 2,
            "orig_unit": "cups",
            "prov": "derived",
        }
    ],
    "steps": [
        {
            "pos": 1,
            "text": "Meng de bloem en boter tot een deeg.",
            "timer_seconds": None,
            "temperature_c": None,
            "ingredient_pos": [1],
            "prov": "explicit",
        }
    ],
    "field_provenance": {
        "title": "derived",
        "servings": "missing",
        "prep_minutes": "missing",
        "cook_minutes": "missing",
        "oven_c": "missing",
        "difficulty": "derived",
    },
    "missing": ["servings", "oven_c", "cook_minutes"],
}


def _bundle(**overrides: object) -> EvidenceBundle:
    base: dict[str, object] = {
        "platform": SourcePlatform.tiktok,
        "url": "https://tiktok.com/@k/video/1",
        "url_norm": "https://tiktok.com/@k/video/1",
        "caption": "Boterkoekjes: 2 cups bloem, 1 stick boter, zout naar smaak. Bakken tot goud.",
    }
    base.update(overrides)
    return EvidenceBundle(**base)  # type: ignore[arg-type]


def _result(**overrides: Any) -> dict[str, Any]:
    return {**GOOD_RESULT, **overrides}


async def test_returns_a_validated_recipe() -> None:
    completer = StubChatCompleter(GOOD_RESULT)

    result = await synthesise(_bundle(), completer, make_settings())

    assert result.title == "Simpele boterkoekjes"
    # The converted amount kept its original and is derived, never explicit.
    assert result.ingredients[0].prov == "derived"
    assert result.ingredients[0].orig_unit == "cups"


async def test_the_pinned_model_and_prompt_version_come_from_config() -> None:
    completer = StubChatCompleter(GOOD_RESULT)

    await synthesise(
        _bundle(), completer, make_settings(openai_model="gpt-4.1-mini", prompt_version=1)
    )

    # ADR-011: never chosen at a call site.
    assert completer.calls[0]["model"] == "gpt-4.1-mini"
    assert completer.calls[0]["max_output_tokens"] == get_prompt(1).max_output_tokens


async def test_evidence_too_thin_spends_nothing() -> None:
    """The gate is before the call, not after.

    Paying to read two emoji can only produce a hallucinated recipe.
    """
    completer = StubChatCompleter(GOOD_RESULT)

    with pytest.raises(ImportFailedError) as caught:
        await synthesise(_bundle(caption="😍🔥"), completer, make_settings())

    assert caught.value.error_code is ImportErrorCode.silent_video
    assert completer.calls == []


async def test_a_thin_blog_is_no_recipe_found_not_silent_video() -> None:
    completer = StubChatCompleter(GOOD_RESULT)

    with pytest.raises(ImportFailedError) as caught:
        await synthesise(
            _bundle(platform=SourcePlatform.web, caption="lekker!"), completer, make_settings()
        )

    assert caught.value.error_code is ImportErrorCode.no_recipe_found


async def test_long_evidence_is_clipped_before_it_is_sent() -> None:
    completer = StubChatCompleter(GOOD_RESULT)
    bundle = _bundle(
        platform=SourcePlatform.youtube,
        page_text="x" * (MAX_PAGE_CHARS * 2),
        transcript=[TranscriptSegment(text="y" * (MAX_TRANSCRIPT_CHARS * 2))],
    )

    await synthesise(bundle, completer, make_settings())

    sent = completer.calls[0]["user"]
    assert len(_section(sent, "PAGE TEXT")) == MAX_PAGE_CHARS
    assert len(_section(sent, "TRANSCRIPT")) == MAX_TRANSCRIPT_CHARS
    # Clipping the prompt copy must not touch the bundle that gets cached and debugged.
    assert len(bundle.page_text or "") == MAX_PAGE_CHARS * 2


def _section(message: str, label: str) -> str:
    """The body of one labelled evidence section.

    Measured this way rather than by counting the filler character: the prompt's own wording
    contains x's and y's, and a count would be off by however many.
    """
    return message.split(f"--- {label} ---\n", 1)[1].split("\n\n", 1)[0]


async def test_found_false_is_reported_as_no_recipe() -> None:
    """A haul video is not a recipe, and the prompt asks the model to say so."""
    completer = StubChatCompleter(_result(found=False, ingredients=[], steps=[]))

    with pytest.raises(ImportFailedError) as caught:
        await synthesise(_bundle(), completer, make_settings())

    assert caught.value.error_code is ImportErrorCode.no_recipe_found


async def test_a_recipe_with_no_steps_is_low_confidence_not_a_success() -> None:
    completer = StubChatCompleter(_result(steps=[]))

    with pytest.raises(ImportFailedError) as caught:
        await synthesise(_bundle(), completer, make_settings())

    assert caught.value.error_code is ImportErrorCode.low_confidence


async def test_a_payload_that_does_not_match_the_schema_fails_loudly() -> None:
    """Structured outputs make this near-impossible, which is why it must not pass silently:
    it means the JSON schema and the Pydantic model have drifted apart."""
    completer = StubChatCompleter(_result(ingredients=[{"pos": 1, "name_nl": "bloem"}]))

    with pytest.raises(ImportFailedError) as caught:
        await synthesise(_bundle(), completer, make_settings())

    assert caught.value.error_code is ImportErrorCode.model_failed


async def test_a_free_text_unit_is_rejected() -> None:
    """`unit` is an enum. Free text here would reach the database and break the shopping list."""
    bad = _result(
        ingredients=[{**GOOD_RESULT["ingredients"][0], "unit": "cups"}],
    )
    completer = StubChatCompleter(bad)

    with pytest.raises(ImportFailedError) as caught:
        await synthesise(_bundle(), completer, make_settings())

    assert caught.value.error_code is ImportErrorCode.model_failed
