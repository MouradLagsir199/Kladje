"""Versioned prompts.

A prompt is loaded by number, never written at a call site. `PROMPT_VERSION` in config decides
which one runs, and bumping it is what invalidates cached synthesis selectively — see ADR-011.
Editing a prompt in place instead of adding a version silently changes every future import while
leaving old ones attributed to a prompt that no longer exists.
"""

from dataclasses import dataclass
from typing import Any, Protocol

from receptenapp.services.evidence import EvidenceBundle
from receptenapp.services.prompts import v1


class UserMessageBuilder(Protocol):
    def __call__(self, bundle: EvidenceBundle) -> str: ...


@dataclass(frozen=True, slots=True)
class PromptSet:
    version: int
    system: str
    json_schema: dict[str, Any]
    build_user_message: UserMessageBuilder
    # Hard ceiling on generated tokens. A runaway generation is the one way a single import can
    # cost real money, so the limit travels with the prompt it was measured against.
    max_output_tokens: int


_VERSIONS: dict[int, PromptSet] = {
    1: PromptSet(
        version=1,
        system=v1.SYSTEM_PROMPT,
        json_schema=v1.JSON_SCHEMA,
        build_user_message=v1.build_user_message,
        max_output_tokens=v1.MAX_OUTPUT_TOKENS,
    )
}


def get_prompt(version: int) -> PromptSet:
    prompt = _VERSIONS.get(version)
    if prompt is None:
        # Loud on purpose: a config pointing at a prompt that does not exist must not silently
        # fall back to another one, because provenance would then be recorded against the wrong
        # version.
        raise ValueError(f"No synthesis prompt for version {version}; have {sorted(_VERSIONS)}")
    return prompt
