"""recipes, recipe_ingredients, recipe_steps, collections, collection_recipes, cook_logs

Revision ID: 002
Revises: 001
Create Date: 2026-08-03

Two forward references cannot be expressed yet, because the tables they point at do not exist:

- `recipes.import_id` → `imports(id)`, created in 003
- `cook_logs.shared_group_id` → `groups(id)`, created in 005

Both columns are created here, nullable and without the constraint, and the foreign keys are added
by those later migrations. Adding a constraint later is non-destructive; adding the *column* later
would mean changing a table other code already writes to, which is what expand/contract exists to
avoid.

All nine enums already exist from 001, so every enum reference here is `create_type=False`.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: str | None = "001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

UNIT = [
    "g",
    "kg",
    "ml",
    "l",
    "el",
    "tl",
    "stuk",
    "snuf",
    "teentje",
    "bosje",
    "blikje",
    "pakje",
    "plak",
    "handvol",
    "naar_smaak",
]
SHELF_CATEGORY = [
    "groente_fruit",
    "vlees_vis",
    "zuivel_eieren",
    "brood_bakkerij",
    "houdbaar",
    "kruiden_specerijen",
    "diepvries",
    "dranken",
    "overig",
]
PROVENANCE = ["explicit", "derived", "estimated", "missing"]
MEAL_TYPE = ["ontbijt", "lunch", "diner", "tussendoor"]
SOURCE_PLATFORM = ["tiktok", "instagram", "youtube", "pinterest", "web", "photo_ocr", "manual"]
DIFFICULTY = ["makkelijk", "gemiddeld", "uitdagend"]


def _enum(values: list[str], name: str) -> postgresql.ENUM:
    return postgresql.ENUM(*values, name=name, create_type=False)


def upgrade() -> None:
    op.create_table(
        "recipes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "origin_recipe_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recipes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # FK to imports(id) added in 003 — see module docstring.
        sa.Column("import_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_blob_path", sa.Text(), nullable=True),
        sa.Column(
            "meal_types",
            postgresql.ARRAY(_enum(MEAL_TYPE, "meal_type")),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("servings", sa.SmallInteger(), nullable=False, server_default=sa.text("2")),
        sa.Column("prep_minutes", sa.SmallInteger(), nullable=True),
        sa.Column("cook_minutes", sa.SmallInteger(), nullable=True),
        sa.Column("difficulty", _enum(DIFFICULTY, "difficulty"), nullable=True),
        sa.Column("kcal_per_serving", sa.SmallInteger(), nullable=True),
        sa.Column("source_platform", _enum(SOURCE_PLATFORM, "source_platform"), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_url_norm", sa.Text(), nullable=True),
        sa.Column("source_author", sa.Text(), nullable=True),
        sa.Column("source_title", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("cooked_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_cooked_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_recipes_user_created",
        "recipes",
        ["user_id", sa.text("created_at DESC")],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    # Powers "Je hebt dit recept al" — see docs/03 Stage 0, source_url_norm is the dedupe key.
    op.create_index("ix_recipes_user_source_norm", "recipes", ["user_id", "source_url_norm"])
    # Postgres ships a Dutch stemmer; use it rather than 'simple'. The two-argument form with a
    # literal config is IMMUTABLE, which is what makes it indexable.
    op.execute(
        "CREATE INDEX ix_recipes_search ON recipes USING GIN "
        "(to_tsvector('dutch', title || ' ' || coalesce(description, '')))"
    )

    op.create_table(
        "recipe_ingredients",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "recipe_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recipes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("section", sa.Text(), nullable=True),
        sa.Column("amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("amount_max", sa.Numeric(10, 2), nullable=True),
        sa.Column("unit", _enum(UNIT, "unit"), nullable=True),
        sa.Column("name_nl", sa.Text(), nullable=False),
        sa.Column("qualifier", sa.Text(), nullable=True),
        sa.Column(
            "category",
            _enum(SHELF_CATEGORY, "shelf_category"),
            nullable=False,
            server_default=sa.text("'overig'"),
        ),
        sa.Column("optional", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        # Never discarded: this is what makes a conversion reversible and auditable, and the only
        # debugging tool left when a parse looks wrong weeks later.
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("original_amount", sa.Numeric(10, 2), nullable=True),
        # Free text on purpose while `unit` is an enum: the source may say anything, we may not.
        sa.Column("original_unit", sa.Text(), nullable=True),
        sa.Column(
            "provenance",
            _enum(PROVENANCE, "provenance"),
            nullable=False,
            server_default=sa.text("'explicit'"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("recipe_id", "position", name="uq_recipe_ingredients_recipe_position"),
    )
    op.create_index("ix_recipe_ingredients_recipe", "recipe_ingredients", ["recipe_id"])
    op.create_index("ix_recipe_ingredients_name_nl", "recipe_ingredients", ["name_nl"])

    op.create_table(
        "recipe_steps",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "recipe_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recipes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        # Always AI-rewritten, never copied from the source. Legal, docs/07-legal-avg.md.
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("timer_seconds", sa.Integer(), nullable=True),
        sa.Column("temperature_c", sa.SmallInteger(), nullable=True),
        sa.Column("temperature_fan_c", sa.SmallInteger(), nullable=True),
        # Denormalised rather than a join table: cook mode reads this on every screen, never writes.
        sa.Column(
            "ingredient_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column(
            "provenance",
            _enum(PROVENANCE, "provenance"),
            nullable=False,
            server_default=sa.text("'explicit'"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("recipe_id", "position", name="uq_recipe_steps_recipe_position"),
    )
    op.create_index("ix_recipe_steps_recipe", "recipe_steps", ["recipe_id"])

    op.create_table(
        "collections",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("emoji", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_collections_user", "collections", ["user_id"])

    op.create_table(
        "collection_recipes",
        sa.Column(
            "collection_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("collections.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "recipe_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recipes.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        # This join row's creation timestamp; named per docs/02 rather than `created_at`.
        sa.Column(
            "added_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_collection_recipes_recipe", "collection_recipes", ["recipe_id"])

    op.create_table(
        "cook_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "recipe_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recipes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # User-settable (a cook can be logged after the fact), which is why `created_at` below is
        # a separate, non-negotiable row-creation timestamp rather than a duplicate of this.
        sa.Column(
            "cooked_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("photo_blob_path", sa.Text(), nullable=True),
        sa.Column("rating", sa.SmallInteger(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        # FK to groups(id) added in 005 — see module docstring.
        sa.Column("shared_group_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_cook_logs_rating_range"),
    )
    op.create_index(
        "ix_cook_logs_recipe_cooked",
        "cook_logs",
        ["recipe_id", sa.text("cooked_at DESC")],
    )
    op.create_index("ix_cook_logs_user", "cook_logs", ["user_id"])


def downgrade() -> None:
    # Reverse dependency order. Indexes and constraints go with their tables.
    op.drop_table("cook_logs")
    op.drop_table("collection_recipes")
    op.drop_table("collections")
    op.drop_table("recipe_steps")
    op.drop_table("recipe_ingredients")
    op.drop_table("recipes")
