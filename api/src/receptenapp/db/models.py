import decimal
import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    ARRAY,
    TIMESTAMP,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from receptenapp.db.base import Base


class PlanTier(enum.StrEnum):
    free = "free"
    premium = "premium"


class Unit(enum.StrEnum):
    """`naar_smaak` exists so "peper en zout naar smaak" has somewhere to go that isn't a fake
    number — see docs/02-datamodel.md."""

    g = "g"
    kg = "kg"
    ml = "ml"
    l = "l"  # noqa: E741 — the unit is literally "l"; renaming it would break the enum value
    el = "el"
    tl = "tl"
    stuk = "stuk"
    snuf = "snuf"
    teentje = "teentje"
    bosje = "bosje"
    blikje = "blikje"
    pakje = "pakje"
    plak = "plak"
    handvol = "handvol"
    naar_smaak = "naar_smaak"


class ShelfCategory(enum.StrEnum):
    groente_fruit = "groente_fruit"
    vlees_vis = "vlees_vis"
    zuivel_eieren = "zuivel_eieren"
    brood_bakkerij = "brood_bakkerij"
    houdbaar = "houdbaar"
    kruiden_specerijen = "kruiden_specerijen"
    diepvries = "diepvries"
    dranken = "dranken"
    overig = "overig"


class Provenance(enum.StrEnum):
    """What the review screen renders as a coloured dot. With no jump-to-source in the product,
    the honesty of this field is the trust mechanism — see docs/02-datamodel.md."""

    explicit = "explicit"
    derived = "derived"
    estimated = "estimated"
    missing = "missing"


class MealType(enum.StrEnum):
    ontbijt = "ontbijt"
    lunch = "lunch"
    diner = "diner"
    tussendoor = "tussendoor"


class SourcePlatform(enum.StrEnum):
    tiktok = "tiktok"
    instagram = "instagram"
    youtube = "youtube"
    pinterest = "pinterest"
    web = "web"
    photo_ocr = "photo_ocr"
    manual = "manual"


class Difficulty(enum.StrEnum):
    makkelijk = "makkelijk"
    gemiddeld = "gemiddeld"
    uitdagend = "uitdagend"


class ImportStatus(enum.StrEnum):
    """The lifecycle of one import. The type already exists — migration 001 created it."""

    queued = "queued"
    fetching = "fetching"
    synthesizing = "synthesizing"
    ready_for_review = "ready_for_review"
    saved = "saved"
    failed = "failed"
    cancelled = "cancelled"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_email", "email", postgresql_where=text("deleted_at IS NULL")),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    clerk_user_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(Text)
    email_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    display_name: Mapped[str | None] = mapped_column(Text)
    avatar_url: Mapped[str | None] = mapped_column(Text)
    household_size: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("2")
    )
    locale: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'nl-NL'"))
    tier: Mapped[PlanTier] = mapped_column(
        SAEnum(PlanTier, name="plan_tier"), nullable=False, server_default=text("'free'")
    )
    trial_started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    diets: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'")
    )
    allergens: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'")
    )
    default_servings: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("2")
    )
    show_original_units: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    fan_oven_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    notif_cooking: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    notif_defrost: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    notif_group: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )


class Recipe(Base):
    """Per-user copy, never a shared mutable row — see docs/02-datamodel.md.

    Saving someone else's recipe gives you your own copy with `origin_recipe_id` pointing back. That
    costs storage and buys no edit conflicts, no per-field permission checks, and nobody changing
    the recipe you planned for Thursday.
    """

    __tablename__ = "recipes"
    __table_args__ = (
        Index(
            "ix_recipes_user_created",
            "user_id",
            text("created_at DESC"),
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_recipes_user_source_norm", "user_id", "source_url_norm"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    origin_recipe_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="SET NULL")
    )
    import_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("imports.id", ondelete="SET NULL")
    )

    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    image_blob_path: Mapped[str | None] = mapped_column(Text)
    meal_types: Mapped[list[MealType]] = mapped_column(
        ARRAY(SAEnum(MealType, name="meal_type")), nullable=False, server_default=text("'{}'")
    )
    servings: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("2"))
    prep_minutes: Mapped[int | None] = mapped_column(SmallInteger)
    cook_minutes: Mapped[int | None] = mapped_column(SmallInteger)
    difficulty: Mapped[Difficulty | None] = mapped_column(SAEnum(Difficulty, name="difficulty"))
    kcal_per_serving: Mapped[int | None] = mapped_column(SmallInteger)

    # Attribution is always shown — see docs/07-legal-avg.md.
    source_platform: Mapped[SourcePlatform] = mapped_column(
        SAEnum(SourcePlatform, name="source_platform"), nullable=False
    )
    source_url: Mapped[str | None] = mapped_column(Text)
    source_url_norm: Mapped[str | None] = mapped_column(Text)
    source_author: Mapped[str | None] = mapped_column(Text)
    source_title: Mapped[str | None] = mapped_column(Text)

    # Provenance for the recipe's own scalar fields — title, servings, prep/cook minutes, oven_c,
    # difficulty — as `{field: provenance}`. JSONB rather than six enum columns because the set of
    # fields tracked this way follows the prompt's schema, and that changes with a prompt version
    # while a column set changes with a migration.
    #
    # Without this the detail screen cannot tell a stated serving count from an inferred one, which
    # is the difference the whole provenance design exists to show.
    field_provenance: Mapped[dict[str, str] | None] = mapped_column(JSONB)

    notes: Mapped[str | None] = mapped_column(Text)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    cooked_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    last_cooked_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


class RecipeIngredient(Base):
    """The Prakkie export contract (D2) as well as the app's most-read table."""

    __tablename__ = "recipe_ingredients"
    __table_args__ = (
        UniqueConstraint("recipe_id", "position", name="uq_recipe_ingredients_recipe_position"),
        Index("ix_recipe_ingredients_recipe", "recipe_id"),
        Index("ix_recipe_ingredients_name_nl", "name_nl"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    section: Mapped[str | None] = mapped_column(Text)

    amount: Mapped[decimal.Decimal | None] = mapped_column(Numeric(10, 2))
    amount_max: Mapped[decimal.Decimal | None] = mapped_column(Numeric(10, 2))
    unit: Mapped[Unit | None] = mapped_column(SAEnum(Unit, name="unit"))
    name_nl: Mapped[str] = mapped_column(Text, nullable=False)
    qualifier: Mapped[str | None] = mapped_column(Text)
    category: Mapped[ShelfCategory] = mapped_column(
        SAEnum(ShelfCategory, name="shelf_category"),
        nullable=False,
        server_default=text("'overig'"),
    )
    optional: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    # Never discard this: it is what makes a conversion reversible, and the only debugging tool
    # left when a parse looks wrong weeks later.
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    original_amount: Mapped[decimal.Decimal | None] = mapped_column(Numeric(10, 2))
    # Free text while `unit` is an enum. Deliberate asymmetry: the source may say anything, our
    # output may not.
    original_unit: Mapped[str | None] = mapped_column(Text)
    provenance: Mapped[Provenance] = mapped_column(
        SAEnum(Provenance, name="provenance"), nullable=False, server_default=text("'explicit'")
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )


class RecipeStep(Base):
    __tablename__ = "recipe_steps"
    __table_args__ = (
        UniqueConstraint("recipe_id", "position", name="uq_recipe_steps_recipe_position"),
        Index("ix_recipe_steps_recipe", "recipe_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    # Always AI-rewritten, never copied from the source. Legal, docs/07-legal-avg.md.
    # Named `text_` only because `text` is SQLAlchemy's helper; the column itself is `text`.
    text_: Mapped[str] = mapped_column("text", Text, nullable=False)
    timer_seconds: Mapped[int | None] = mapped_column(Integer)
    temperature_c: Mapped[int | None] = mapped_column(SmallInteger)
    temperature_fan_c: Mapped[int | None] = mapped_column(SmallInteger)
    # Denormalised rather than a join table: cook mode reads this on every screen and never writes.
    ingredient_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, server_default=text("'{}'")
    )
    provenance: Mapped[Provenance] = mapped_column(
        SAEnum(Provenance, name="provenance"), nullable=False, server_default=text("'explicit'")
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )


class Import(Base):
    """One attempt to turn a URL into a recipe.

    A row exists from the moment the user pastes a link, including when the import fails — the
    failure is the interesting part, and a client that has to distinguish "still working" from
    "never started" needs something to poll.
    """

    __tablename__ = "imports"
    __table_args__ = (
        Index("ix_imports_user_created", "user_id", text("created_at DESC")),
        # Partial: the quota check reads only the rows that count, and there is no reason to index
        # the ones that do not. This is the index every single import hits.
        Index(
            "ix_imports_user_quota",
            "user_id",
            "counted_against_quota",
            "created_at",
            postgresql_where=text("counted_against_quota"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[ImportStatus] = mapped_column(
        SAEnum(ImportStatus, name="import_status"), nullable=False, server_default=text("'queued'")
    )
    platform: Mapped[SourcePlatform] = mapped_column(
        SAEnum(SourcePlatform, name="source_platform"), nullable=False
    )
    source_url: Mapped[str | None] = mapped_column(Text)
    source_url_norm: Mapped[str | None] = mapped_column(Text)

    # The editable review payload. Deliberately JSONB and not rows in `recipes`: nothing reaches the
    # library until the user presses Opslaan, so a half-corrected draft cannot show up in a search.
    draft: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    recipe_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="SET NULL")
    )

    cache_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    counted_against_quota: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    cost_eur_cents: Mapped[decimal.Decimal | None] = mapped_column(Numeric(8, 4))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(Text)
    error_detail: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


class ImportEvent(Base):
    """One stage transition. This is what the progress screen renders.

    `stage` and `state` are free text rather than enums on purpose: they are a telemetry log, and a
    new stage should not need a migration to be recordable. Nothing branches on their values.
    """

    __tablename__ = "import_events"
    __table_args__ = (Index("ix_import_events_import", "import_id", "id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    import_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("imports.id", ondelete="CASCADE"), nullable=False
    )
    stage: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)
    at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )


class Collection(Base):
    __tablename__ = "collections"
    __table_args__ = (Index("ix_collections_user", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    emoji: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )


class CollectionRecipe(Base):
    __tablename__ = "collection_recipes"
    __table_args__ = (Index("ix_collection_recipes_recipe", "recipe_id"),)

    collection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True
    )
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True
    )
    # This row's creation timestamp; named per docs/02 rather than `created_at`.
    added_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )


class CookLog(Base):
    __tablename__ = "cook_logs"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_cook_logs_rating_range"),
        Index("ix_cook_logs_recipe_cooked", "recipe_id", text("cooked_at DESC")),
        Index("ix_cook_logs_user", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # User-settable, so a cook can be logged after the fact — which is why `created_at` below is a
    # separate row-creation timestamp rather than a duplicate of this.
    cooked_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    photo_blob_path: Mapped[str | None] = mapped_column(Text)
    rating: Mapped[int | None] = mapped_column(SmallInteger)
    note: Mapped[str | None] = mapped_column(Text)
    # FK constraint arrives with the groups table in migration 005.
    shared_group_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
