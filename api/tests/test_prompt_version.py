"""M9 — the prompt is loaded by version, and its schema is shaped the way strict mode demands."""

from typing import Any

import pytest

from receptenapp.db.models import SourcePlatform
from receptenapp.services.evidence import EvidenceBundle, TranscriptSegment
from receptenapp.services.prompts import get_prompt


def test_version_one_exists_and_reports_its_own_number() -> None:
    prompt = get_prompt(1)
    assert prompt.version == 1
    assert prompt.max_output_tokens > 0


def test_an_unknown_version_raises_rather_than_falling_back() -> None:
    """Silently using another version would attribute an import to a prompt that never ran."""
    with pytest.raises(ValueError, match="version 99"):
        get_prompt(99)


def test_the_prompt_carries_the_rules_that_cannot_be_lost() -> None:
    system = get_prompt(1).system

    # Each of these is a requirement from docs/07-legal-avg.md or a non-negotiable in CLAUDE.md.
    assert "REWRITE every step in your own words" in system
    assert 'A converted quantity is "derived", never "explicit".' in system
    assert "Do NOT guess: servings, oven temperature, prep time, cook time, difficulty." in system
    assert "must be Dutch" in system
    # The worked example is load-bearing: it is what keeps provenance honest under pressure.
    assert "two cups of flour" in system


def _walk_objects(schema: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if schema.get("type") == "object" or "properties" in schema:
        found.append(schema)
    for value in schema.get("properties", {}).values():
        found += _walk_objects(value)
    if isinstance(items := schema.get("items"), dict):
        found += _walk_objects(items)
    return found


def test_every_object_in_the_schema_satisfies_strict_mode() -> None:
    """OpenAI strict mode wants `additionalProperties: false` and every key in `required`.

    Optionality is expressed by allowing null, never by leaving a key out. Getting this wrong is a
    400 on the whole call, so it is worth asserting rather than discovering in production.
    """
    for obj in _walk_objects(get_prompt(1).json_schema):
        properties = set(obj.get("properties", {}))
        assert obj.get("additionalProperties") is False, obj.get("title", properties)
        assert set(obj.get("required", [])) == properties, properties


def test_the_schema_carries_no_range_keywords() -> None:
    """Bounds are enforced in Pydantic instead.

    An unrecognised range keyword fails the entire request; a bound checked afterwards just
    clamps. See schemas/synthesis.py.
    """
    rendered = repr(get_prompt(1).json_schema)
    for keyword in ("maxLength", "minLength", "minimum", "maximum"):
        assert keyword not in rendered


def test_enums_match_the_database() -> None:
    ingredient = get_prompt(1).json_schema["properties"]["ingredients"]["items"]["properties"]
    units = ingredient["unit"]["enum"]

    assert "naar_smaak" in units
    assert None in units  # nothing fits is a legitimate answer; inventing a unit is not
    assert set(ingredient["prov"]["enum"]) == {"explicit", "derived", "estimated", "missing"}


def _bundle(**overrides: object) -> EvidenceBundle:
    base: dict[str, object] = {
        "platform": SourcePlatform.web,
        "url": "https://blog.test/snert",
        "url_norm": "https://blog.test/snert",
    }
    base.update(overrides)
    return EvidenceBundle(**base)  # type: ignore[arg-type]


def test_the_user_message_labels_each_kind_of_evidence() -> None:
    """The labels are load-bearing: the prompt tells the model to trust these in order."""
    message = get_prompt(1).build_user_message(
        _bundle(
            structured={"@type": "Recipe", "name": "Snert"},
            page_text="Een winterse klassieker.",
            transcript=[TranscriptSegment(text="Week de erwten een nacht.")],
            caption="Snert zoals oma hem maakte",
            author="Koen",
        )
    )

    assert "--- STRUCTURED RECIPE DATA (schema.org) ---" in message
    assert "--- PAGE TEXT ---" in message
    assert "--- TRANSCRIPT ---" in message
    assert "--- CAPTION ---" in message
    assert message.index("STRUCTURED") < message.index("PAGE TEXT") < message.index("TRANSCRIPT")
    assert "Author: Koen" in message


def test_absent_evidence_gets_no_empty_section() -> None:
    message = get_prompt(1).build_user_message(_bundle(caption="Alleen een caption"))

    assert "--- CAPTION ---" in message
    assert "PAGE TEXT" not in message
    assert "TRANSCRIPT" not in message


def test_a_title_equal_to_the_caption_is_not_sent_twice() -> None:
    # TikTok and Instagram give the same string for both; paying to send it twice is waste.
    message = get_prompt(1).build_user_message(_bundle(title="Snert", caption="Snert"))
    assert message.count("Snert") == 1
