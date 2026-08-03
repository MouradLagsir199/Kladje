"""Request and response shapes for the import flow.

Named `import_.py` because `import` is a keyword.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from receptenapp.db.models import ImportStatus, SourcePlatform


class ImportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Generous: a share sheet hands over a URL with a paragraph of tracking parameters attached.
    url: str = Field(min_length=4, max_length=2048)


class ImportEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    stage: str
    state: str
    detail: str | None
    at: datetime


class ImportOut(BaseModel):
    """What the progress screen polls.

    `draft` is null until the status reaches `ready_for_review`, and `error_code` is null unless it
    reached `failed`. The client switches on `status` and never has to guess.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: ImportStatus
    platform: SourcePlatform
    source_url: str | None
    draft: dict[str, Any] | None
    recipe_id: uuid.UUID | None
    error_code: str | None
    error_detail: str | None
    duration_ms: int | None
    created_at: datetime
    events: list[ImportEventOut] = Field(default_factory=list)


class DraftPatch(BaseModel):
    """A partial recipe from the review screen, merged over the draft.

    Deliberately loose: the review screen edits one field at a time and PATCHes as it goes, so the
    server accepts any subset and re-runs validation on the result rather than demanding the client
    send a whole recipe back on every keystroke.
    """

    model_config = ConfigDict(extra="allow")


class QuotaOut(BaseModel):
    used: int
    limit: int
