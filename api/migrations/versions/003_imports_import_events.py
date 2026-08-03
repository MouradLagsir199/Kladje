"""imports, import_events, the deferred recipes.import_id FK, and recipes.field_provenance

Revision ID: 003
Revises: 002
Create Date: 2026-08-03

Deliberately minimal. `source_cache` is not here: it is a cost optimisation, and re-importing during
development paying OpenAI twice is pennies until there are users (see the Phase H table in
docs/13-build-tasks.md).

Two things are worth reading before editing this file.

**Order matters in both directions.** `imports.recipe_id` and `recipes.import_id` point at each
other, so the FK from recipes can only be added once `imports` exists — which is exactly why 002
created that column without its constraint. The downgrade has to drop that constraint before
dropping `imports`, or Postgres refuses.

**`import_status` already exists.** Migration 001 created all nine enum types, so every enum
reference here is `create_type=False`. Letting Alembic autogenerate this file produces
`sa.Enum(...)` without that flag, which fails on a database where 001 has run — the reason
CLAUDE.md says autogenerate then always hand-edit.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: str | None = "002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

IMPORT_STATUS = [
    "queued",
    "fetching",
    "synthesizing",
    "ready_for_review",
    "saved",
    "failed",
    "cancelled",
]
SOURCE_PLATFORM = ["tiktok", "instagram", "youtube", "pinterest", "web", "photo_ocr", "manual"]


def upgrade() -> None:
    import_status = postgresql.ENUM(*IMPORT_STATUS, name="import_status", create_type=False)
    source_platform = postgresql.ENUM(*SOURCE_PLATFORM, name="source_platform", create_type=False)

    op.create_table(
        "imports",
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
        sa.Column("status", import_status, nullable=False, server_default=sa.text("'queued'")),
        sa.Column("platform", source_platform, nullable=False),
        sa.Column("source_url", sa.Text()),
        sa.Column("source_url_norm", sa.Text()),
        sa.Column("draft", postgresql.JSONB()),
        sa.Column(
            "recipe_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recipes.id", ondelete="SET NULL"),
        ),
        sa.Column("cache_hit", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "counted_against_quota",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("cost_eur_cents", sa.Numeric(8, 4)),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("error_code", sa.Text()),
        sa.Column("error_detail", sa.Text()),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True)),
    )
    op.create_index("ix_imports_user_created", "imports", ["user_id", sa.text("created_at DESC")])
    # Partial index. The quota count only ever reads rows where this is true, so indexing the rest
    # would be dead weight on the hottest check in the product.
    op.create_index(
        "ix_imports_user_quota",
        "imports",
        ["user_id", "counted_against_quota", "created_at"],
        postgresql_where=sa.text("counted_against_quota"),
    )

    op.create_table(
        "import_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "import_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("imports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stage", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("detail", sa.Text()),
        sa.Column(
            "at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
    )
    op.create_index("ix_import_events_import", "import_events", ["import_id", "id"])

    # The forward reference 002 left open. Non-destructive: the column already exists and is
    # nullable, so this only adds the constraint.
    op.create_foreign_key(
        "fk_recipes_import_id",
        "recipes",
        "imports",
        ["import_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Provenance for the recipe's own scalar fields. Nullable with no default: rows written before
    # this migration genuinely do not know, and `{}` would claim otherwise.
    op.add_column("recipes", sa.Column("field_provenance", postgresql.JSONB()))


def downgrade() -> None:
    op.drop_column("recipes", "field_provenance")
    # Before `imports` can go, the constraint pointing at it has to. The *column* stays — 002 owns
    # it, and dropping it here would strand a table 002 believes it created in full.
    op.drop_constraint("fk_recipes_import_id", "recipes", type_="foreignkey")

    op.drop_index("ix_import_events_import", table_name="import_events")
    op.drop_table("import_events")

    op.drop_index("ix_imports_user_quota", table_name="imports")
    op.drop_index("ix_imports_user_created", table_name="imports")
    op.drop_table("imports")
    # The enum types are not dropped: 001 created them and 001's downgrade removes them.
