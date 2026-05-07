import os
from app.settings import Settings

def test_settings_accepts_english_environment():
    """Verifies that ENVIRONMENT key is correctly loaded."""
    os.environ["ENVIRONMENT"] = "production"
    os.environ.pop("AMBIENTE", None)
    settings = Settings()
    assert settings.environment == "production"
    os.environ.pop("ENVIRONMENT", None)

def test_settings_accepts_legacy_ambiente():
    """Verifies that legacy AMBIENTE key is correctly loaded (Backward Compatibility)."""
    os.environ["AMBIENTE"] = "production"
    os.environ.pop("ENVIRONMENT", None)
    settings = Settings()
    assert settings.environment == "production"
    os.environ.pop("AMBIENTE", None)

def test_settings_prefers_english_over_legacy():
    """Verifies that ENVIRONMENT takes precedence if both are provided."""
    os.environ["ENVIRONMENT"] = "production"
    os.environ["AMBIENTE"] = "development"
    settings = Settings()
    # ENVIRONMENT should win based on order in AliasChoices("ENVIRONMENT", "AMBIENTE")
    assert settings.environment == "production"
    os.environ.pop("ENVIRONMENT", None)
    os.environ.pop("AMBIENTE", None)

def test_settings_accepts_legacy_app_name():
    """Verifies that legacy NOME_APP key is correctly loaded."""
    os.environ["NOME_APP"] = "Legacy App"
    os.environ.pop("APP_NAME", None)
    settings = Settings()
    assert settings.app_name == "Legacy App"
    os.environ.pop("NOME_APP", None)

def test_settings_accepts_legacy_cors_origins():
    """Verifies that legacy ORIGENS_PERMITIDAS key is correctly loaded."""
    os.environ["ORIGENS_PERMITIDAS"] = "http://legacy.com"
    os.environ.pop("ALLOWED_ORIGINS", None)
    settings = Settings()
    assert settings.allowed_origins == "http://legacy.com"
    os.environ.pop("ORIGENS_PERMITIDAS", None)

def test_settings_detects_legacy_production_value():
    """Verifies that legacy 'producao' is detected as production."""
    os.environ["ENVIRONMENT"] = "producao"
    settings = Settings()
    assert settings.is_production is True
    assert settings.debug is False
    os.environ.pop("ENVIRONMENT", None)

def test_settings_detects_legacy_development_value():
    """Verifies that legacy 'desenvolvimento' is detected as debug mode."""
    os.environ["ENVIRONMENT"] = "desenvolvimento"
    settings = Settings()
    assert settings.is_production is False
    assert settings.debug is True
    os.environ.pop("ENVIRONMENT", None)