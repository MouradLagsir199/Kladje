"""M3 — the one shape every source collapses into."""

import pytest
from pydantic import ValidationError

from receptenapp.db.models import SourcePlatform
from receptenapp.services.evidence import EvidenceBundle, TranscriptSegment


def _bundle(**overrides: object) -> EvidenceBundle:
    base: dict[str, object] = {
        "platform": SourcePlatform.tiktok,
        "url": "https://www.tiktok.com/@chefkoen/video/7234567890123456789?_t=8abc",
        "url_norm": "https://tiktok.com/@chefkoen/video/7234567890123456789",
    }
    base.update(overrides)
    return EvidenceBundle(**base)  # type: ignore[arg-type]


def test_round_trips_through_json() -> None:
    original = _bundle(
        author="chefkoen",
        title="Pasta pesto",
        caption="Snelste pasta ooit",
        structured={"@type": "Recipe", "name": "Pasta pesto"},
        transcript=[
            TranscriptSegment(text="Kook de pasta", start_ms=0, end_ms=1500),
            TranscriptSegment(text="Voeg pesto toe", start_ms=1500, end_ms=3000),
        ],
        page_text="Een simpele pasta.",
        thumbnail_url="https://cdn.example.com/thumb.jpg",
    )
    restored = EvidenceBundle.model_validate_json(original.model_dump_json())
    assert restored == original


def test_minimal_bundle_needs_only_platform_and_urls() -> None:
    bundle = _bundle()
    assert bundle.transcript == []
    assert bundle.structured is None
    assert bundle.transcript_text == ""


def test_unknown_field_is_rejected() -> None:
    # Guards the seam: a normaliser inventing a field should fail loudly here, not silently drop it.
    with pytest.raises(ValidationError):
        _bundle(sentiment="positive")


def test_transcript_text_joins_segments() -> None:
    bundle = _bundle(
        transcript=[
            TranscriptSegment(text="Kook de pasta"),
            TranscriptSegment(text="Voeg pesto toe"),
        ]
    )
    assert bundle.transcript_text == "Kook de pasta Voeg pesto toe"


def test_timings_are_milliseconds_regardless_of_source() -> None:
    # YouTube gives "m:ss", TikTok float seconds. Both must arrive here already converted.
    segment = TranscriptSegment(text="x", start_ms=90_000, end_ms=91_500)
    assert segment.start_ms == 90_000


@pytest.mark.parametrize(
    ("platform", "transcript", "expected"),
    [
        (SourcePlatform.tiktok, [], True),
        (SourcePlatform.instagram, [], True),
        (SourcePlatform.youtube, [], True),
        (SourcePlatform.tiktok, [TranscriptSegment(text="Kook de pasta")], False),
        # A blog has no audio, so "silent" is meaningless for it.
        (SourcePlatform.web, [], False),
    ],
)
def test_is_silent_only_applies_to_video(
    platform: SourcePlatform, transcript: list[TranscriptSegment], expected: bool
) -> None:
    assert _bundle(platform=platform, transcript=transcript).is_silent is expected


def test_structured_recipe_is_never_considered_too_thin() -> None:
    # schema.org data is deliberate authoring, so it is worth a call even when short.
    bundle = _bundle(platform=SourcePlatform.web, structured={"@type": "Recipe", "name": "Soep"})
    assert bundle.is_too_thin_to_synthesise() is False


def test_near_empty_bundle_is_too_thin_to_spend_a_call_on() -> None:
    assert _bundle(caption="lekker!").is_too_thin_to_synthesise() is True


def test_enough_caption_is_worth_synthesising() -> None:
    bundle = _bundle(caption="Pasta pesto: kook 200 g pasta, roer 3 el pesto erdoor, klaar.")
    assert bundle.is_too_thin_to_synthesise() is False


def test_truncation_clips_page_text_and_transcript() -> None:
    bundle = _bundle(
        page_text="x" * 5000,
        transcript=[
            TranscriptSegment(text="a" * 100),
            TranscriptSegment(text="b" * 100),
            TranscriptSegment(text="c" * 100),
        ],
    )
    clipped = bundle.truncated(max_transcript_chars=150, max_page_chars=1000)

    assert len(clipped.page_text or "") == 1000
    assert len(clipped.transcript_text.replace(" ", "")) == 150
    # First segment survives whole, second is cut mid-way, third is dropped entirely.
    assert len(clipped.transcript) == 2


def test_truncation_leaves_the_original_untouched() -> None:
    # The full bundle is what gets cached and debugged; only the prompt copy is clipped.
    bundle = _bundle(page_text="x" * 5000)
    bundle.truncated(max_transcript_chars=10, max_page_chars=10)
    assert len(bundle.page_text or "") == 5000


def test_truncation_is_a_no_op_when_already_short() -> None:
    bundle = _bundle(page_text="kort", transcript=[TranscriptSegment(text="ook kort")])
    assert bundle.truncated(max_transcript_chars=1000, max_page_chars=1000) == bundle


def test_silent_video_with_a_full_caption_is_a_normal_import() -> None:
    """The common TikTok shape: no speech, but the recipe typed under the clip.

    Routing this to manual entry because the audio was music would throw away a perfectly good
    import — so "no speech" and "nothing to work with" must stay separate questions.
    """
    bundle = _bundle(
        caption=(
            "Crispy potato nuggets. Ingredients: 5 medium potatoes, 100 g cheese, "
            "2 el bloem, zout. Bake 20 min at 200 graden."
        )
    )
    assert bundle.is_silent is True
    assert bundle.needs_manual_entry is False


def test_silent_video_with_nothing_else_goes_to_manual_entry() -> None:
    bundle = _bundle(caption="😍🔥")
    assert bundle.is_silent is True
    assert bundle.needs_manual_entry is True
