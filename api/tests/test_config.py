import pytest
from pydantic import ValidationError


def test_settings_load_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@host/db")
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_x")
    monkeypatch.setenv("CLERK_JWKS_URL", "https://example.clerk.accounts.dev/.well-known/jwks.json")
    monkeypatch.setenv("CLERK_WEBHOOK_SECRET", "whsec_x")

    from receptenapp.core.config import Settings

    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.environment == "dev"
    assert settings.openai_model == "gpt-4.1-mini"


def test_missing_required_var_fails_clearly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_x")
    monkeypatch.setenv("CLERK_JWKS_URL", "https://example.clerk.accounts.dev/.well-known/jwks.json")
    monkeypatch.setenv("CLERK_WEBHOOK_SECRET", "whsec_x")

    from receptenapp.core.config import Settings

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)  # type: ignore[call-arg]

    assert "database_url" in str(exc_info.value)
