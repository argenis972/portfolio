import os

import pytest

from app.settings import Settings


def test_debug_disabled_in_production():
    """Ensures debug is disabled in production."""
    os.environ["ENVIRONMENT"] = "production"
    settings = Settings()
    assert settings.debug is False
    if "ENVIRONMENT" in os.environ:
        del os.environ["ENVIRONMENT"]


def test_debug_enabled_in_development():
    """Ensures debug is enabled in development."""
    os.environ["ENVIRONMENT"] = "development"
    settings = Settings()
    assert settings.debug is True
    if "ENVIRONMENT" in os.environ:
        del os.environ["ENVIRONMENT"]


def test_debug_enabled_in_local():
    """Ensures debug is enabled in local environment."""
    os.environ["ENVIRONMENT"] = "local"
    settings = Settings()
    assert settings.debug is True
    if "ENVIRONMENT" in os.environ:
        del os.environ["ENVIRONMENT"]


def test_validate_production_fails_without_redis_and_metrics_auth():
    os.environ["ENVIRONMENT"] = "production"
    os.environ["DATABASE_URL"] = (
        "postgresql+asyncpg://postgres:secret@db.example.com:5432/postgres"
    )
    os.environ.pop("REDIS_URL", None)
    os.environ.pop("METRICS_BASIC_AUTH_USERNAME", None)
    os.environ.pop("METRICS_BASIC_AUTH_PASSWORD", None)

    settings = Settings()

    with pytest.raises(RuntimeError):
        settings.validate_production()

    for key in [
        "ENVIRONMENT",
        "DATABASE_URL",
        "REDIS_URL",
        "METRICS_BASIC_AUTH_USERNAME",
        "METRICS_BASIC_AUTH_PASSWORD",
    ]:
        os.environ.pop(key, None)


def test_validate_production_accepts_supabase_and_metrics_auth():
    os.environ["ENVIRONMENT"] = "production"
    os.environ["DATABASE_URL"] = (
        "postgresql+asyncpg://postgres:secret@db.example.com:5432/postgres"
    )
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"
    os.environ["METRICS_BASIC_AUTH_USERNAME"] = "metrics"
    os.environ["METRICS_BASIC_AUTH_PASSWORD"] = "secret"

    settings = Settings()
    settings.validate_production()

    for key in [
        "ENVIRONMENT",
        "DATABASE_URL",
        "REDIS_URL",
        "METRICS_BASIC_AUTH_USERNAME",
        "METRICS_BASIC_AUTH_PASSWORD",
    ]:
        os.environ.pop(key, None)


# --- A1: Security — API docs must be disabled in production ---


def test_docs_accessible_in_local(client):
    """
    /openapi.json must be accessible in local/dev environments.
    The test client runs with AMBIENTE=local (default), so the app was
    created with docs_url/redoc_url/openapi_url set — 200 expected.
    """
    response = client.get("/openapi.json")
    assert response.status_code == 200


def test_root_does_not_expose_docs_in_production(client):
    """
    Root endpoint must not advertise /docs path in production.
    Leaking the docs path is an unnecessary hint for attackers.
    We patch is_production at the settings instance level to simulate prod.
    """
    from unittest.mock import PropertyMock, patch

    from app.settings import settings

    with patch.object(
        type(settings), "is_production", new_callable=PropertyMock, return_value=True
    ):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "docs" not in data, (
            "Root endpoint must not include 'docs' key in production"
        )


def test_root_exposes_docs_in_local(client):
    """Root endpoint includes 'docs' key only in non-production environments."""
    from unittest.mock import PropertyMock, patch

    from app.settings import settings

    with patch.object(
        type(settings), "is_production", new_callable=PropertyMock, return_value=False
    ):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "docs" in data
        assert data["docs"] == "/docs"
