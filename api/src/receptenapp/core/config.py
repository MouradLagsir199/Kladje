from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Every variable in docs/12-manual-setup.md's environment contract.

    Fields with no default are required — startup fails with a clear
    pydantic ValidationError naming the missing variable. Fields whose
    credential doesn't exist until a later build phase (OpenAI, Apify,
    RevenueCat, Sentry, App Insights) default to None so the API can boot
    in earlier phases; the provider/service that needs them is responsible
    for checking they're set before its first real call.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Core ---
    environment: Literal["dev", "prod"] = "dev"
    log_level: str = "INFO"
    api_base_url: str = "http://localhost:8000"

    # --- Database ---
    database_url: str

    # --- Auth (Clerk) ---
    clerk_secret_key: str
    clerk_jwks_url: str
    clerk_webhook_secret: str

    # --- OpenAI ---
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"  # pinned, see ADR-011 — never override per-call
    prompt_version: int = 1

    # --- Apify ---
    apify_token: str | None = None
    apify_actor_tiktok: str | None = None
    apify_actor_instagram: str | None = None
    apify_actor_youtube: str | None = None
    apify_timeout_seconds: int = 45

    # --- Storage ---
    azure_storage_account: str | None = None
    azure_storage_container: str = "recipe-media"

    # --- Billing ---
    revenuecat_webhook_secret: str | None = None
    free_imports_per_30d: int = 10
    premium_imports_per_period: int = 100

    # --- Limits ---
    import_rate_per_minute: int = 5
    import_rate_per_hour: int = 30
    daily_spend_alert_eur: int = 25

    # --- Observability ---
    sentry_dsn: str | None = None
    applicationinsights_connection_string: str | None = Field(
        default=None, validation_alias="APPLICATIONINSIGHTS_CONNECTION_STRING"
    )


settings = Settings()  # type: ignore[call-arg]  # required fields come from the environment
