"""Stage 2 of the import pipeline — see docs/03-import-pipeline.md.

TikTok, Instagram, YouTube and blog pages arrive in four completely different shapes. This module
is the one place that difference is allowed to exist: everything upstream converts into an
`EvidenceBundle`, and everything downstream only ever sees one structure.

That is what makes synthesis testable without paying for anything — a bundle can be written to a
fixture file and replayed forever.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from receptenapp.db.models import SourcePlatform


class TranscriptSegment(BaseModel):
    """One spoken chunk. Timings are milliseconds, always.

    The sources disagree: TikTok and Instagram give float seconds, YouTube gives `"m:ss"` strings.
    Normalising here is the whole point of the seam — downstream code should never learn which
    platform a segment came from.
    """

    model_config = ConfigDict(extra="forbid")

    text: str
    start_ms: int | None = None
    end_ms: int | None = None


class EvidenceBundle(BaseModel):
    """Everything we managed to learn about a source, before any AI touches it."""

    model_config = ConfigDict(extra="forbid")

    platform: SourcePlatform
    url: str
    url_norm: str
    author: str | None = None
    title: str | None = None
    # The post/video description. On TikTok and Reels this is often where the actual recipe lives.
    caption: str | None = None
    # schema.org Recipe as found on the page. Far more trustworthy than anything inferred, because
    # the site author wrote it deliberately.
    structured: dict[str, Any] | None = None
    transcript: list[TranscriptSegment] = Field(default_factory=list)
    page_text: str | None = None
    thumbnail_url: str | None = None

    @property
    def transcript_text(self) -> str:
        return " ".join(segment.text for segment in self.transcript if segment.text).strip()

    @property
    def has_structured_recipe(self) -> bool:
        return bool(self.structured)

    @property
    def is_silent(self) -> bool:
        """A video that yielded no spoken words.

        Not an error: plenty of cooking videos are music-over-hands. It means the caption is the
        only real evidence, and the import should route to prefilled manual entry rather than
        pretending a recipe was extracted.
        """
        return self.platform in _VIDEO_PLATFORMS and not self.transcript_text

    def evidence_chars(self) -> int:
        """Rough size of what we would send to the model. Used to decide whether it is worth
        spending a call at all."""
        parts = [self.title, self.caption, self.page_text, self.transcript_text]
        structured = str(self.structured) if self.structured else ""
        return sum(len(p) for p in parts if p) + len(structured)

    def is_too_thin_to_synthesise(self, minimum_chars: int = 40) -> bool:
        """True when there is so little to work with that a model call would only produce guesses.

        Cheaper and more honest to fail early than to pay for a hallucinated recipe.
        """
        return not self.has_structured_recipe and self.evidence_chars() < minimum_chars

    def truncated(self, *, max_transcript_chars: int, max_page_chars: int) -> "EvidenceBundle":
        """A copy with the long free-text fields clipped, for prompt cost control.

        A 20-minute YouTube transcript is what actually runs up an OpenAI bill — not the number of
        imports. Clipping happens here rather than in the prompt builder so the limit is visible
        and testable, and so the untruncated bundle is still what gets cached and debugged.
        """
        clipped_page = self.page_text
        if clipped_page and len(clipped_page) > max_page_chars:
            clipped_page = clipped_page[:max_page_chars]

        segments: list[TranscriptSegment] = []
        remaining = max_transcript_chars
        for segment in self.transcript:
            if remaining <= 0:
                break
            if len(segment.text) <= remaining:
                segments.append(segment)
                remaining -= len(segment.text)
            else:
                segments.append(segment.model_copy(update={"text": segment.text[:remaining]}))
                remaining = 0

        return self.model_copy(update={"page_text": clipped_page, "transcript": segments})


_VIDEO_PLATFORMS = frozenset(
    {SourcePlatform.tiktok, SourcePlatform.instagram, SourcePlatform.youtube}
)
