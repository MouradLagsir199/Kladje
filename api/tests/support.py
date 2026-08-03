"""Shared test helpers."""

from typing import Any

from receptenapp.core.config import Settings


def make_settings(**overrides: Any) -> Settings:
    """Settings with `.env` explicitly disabled.

    Without `_env_file=None` these tests read the developer's real `api/.env`, so they would pass
    or fail depending on which actor ids and model happen to be configured locally.
    """
    base: dict[str, Any] = {
        "_env_file": None,
        "database_url": "postgresql+asyncpg://x/y",
        "clerk_secret_key": "k",
        "clerk_jwks_url": "u",
        "clerk_webhook_secret": "w",
    }
    base.update(overrides)
    return Settings(**base)
