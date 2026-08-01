import enum
import uuid
from datetime import datetime

from sqlalchemy import ARRAY, TIMESTAMP, Boolean, ForeignKey, Index, SmallInteger, Text, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from receptenapp.db.base import Base


class PlanTier(enum.StrEnum):
    free = "free"
    premium = "premium"


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
