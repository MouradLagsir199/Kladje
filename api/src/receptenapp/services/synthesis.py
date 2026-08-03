"""Stage 3 of the import pipeline: an `EvidenceBundle` becomes a structured recipe.

The only place in the codebase that spends model money. Everything about it is arranged so that a
call happens once, on evidence worth reading, with a bounded amount of text in both directions.
"""

from pydantic import ValidationError

from receptenapp.core.config import Settings
from receptenapp.core.errors import ImportErrorCode, ImportFailedError
from receptenapp.providers.openai import ChatCompleter
from receptenapp.schemas.synthesis import SynthesisResult
from receptenapp.services.evidence import EvidenceBundle
from receptenapp.services.prompts import get_prompt

# Roughly 5k and 6k tokens. Comfortably above a long blog recipe and a ten-minute transcript, and
# far below what a rambling 40-minute video would send if left uncapped.
MAX_TRANSCRIPT_CHARS = 20_000
MAX_PAGE_CHARS = 24_000

SCHEMA_NAME = "recipe_synthesis"


async def synthesise(
    bundle: EvidenceBundle,
    completer: ChatCompleter,
    settings: Settings,
) -> SynthesisResult:
    """Read a recipe out of the evidence. One model call, or none at all."""
    if bundle.is_too_thin_to_synthesise():
        # Refused before the call, not after. Paying to read two emoji can only produce a
        # hallucinated recipe, and the honest answer is to offer manual entry.
        raise ImportFailedError(
            ImportErrorCode.silent_video if bundle.is_silent else ImportErrorCode.no_recipe_found,
            "Hier staat te weinig in om een recept van te maken.",
            details={"evidence_chars": bundle.evidence_chars()},
        )

    prompt = get_prompt(settings.prompt_version)
    clipped = bundle.truncated(
        max_transcript_chars=MAX_TRANSCRIPT_CHARS, max_page_chars=MAX_PAGE_CHARS
    )

    raw = await completer.complete_json(
        model=settings.openai_model,
        system=prompt.system,
        user=prompt.build_user_message(clipped),
        json_schema=prompt.json_schema,
        schema_name=SCHEMA_NAME,
        max_output_tokens=prompt.max_output_tokens,
    )

    try:
        result = SynthesisResult.model_validate(raw)
    except ValidationError as exc:
        # Structured outputs make this close to impossible, which is exactly why it must be loud:
        # if it happens, the schema and the Pydantic model have drifted apart.
        raise ImportFailedError(
            ImportErrorCode.model_failed,
            "Het recept kwam in een onverwachte vorm terug.",
            details={"errors": exc.errors(include_url=False)[:3]},
        ) from exc

    if not result.found:
        # The model was asked to say so rather than construct a recipe out of a haul video.
        raise ImportFailedError(
            ImportErrorCode.no_recipe_found,
            "We konden hier geen recept in vinden.",
        )

    if not result.ingredients or not result.steps:
        raise ImportFailedError(
            ImportErrorCode.low_confidence,
            "We konden hier geen volledig recept uit halen.",
            details={
                "ingredients": len(result.ingredients),
                "steps": len(result.steps),
                "confidence": str(result.confidence),
            },
        )

    return result
