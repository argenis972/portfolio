"""
Application settings via environment variables.

Uses pydantic-settings for automatic validation and default values.
All settings can be overridden via .env or environment variables.
"""

from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized application settings.

    Attributes:
        app_name: Name displayed in OpenAPI documentation.
        environment: Execution environment (local, staging, production).
        allowed_origins: List of comma-separated CORS origins.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(
        default="Portfolio Backend API",
        validation_alias=AliasChoices("APP_NAME", "NOME_APP"),
    )
    environment: str = Field(
        default="local",
        validation_alias=AliasChoices("ENVIRONMENT", "AMBIENTE"),
    )
    allowed_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:5175,http://127.0.0.1:5175,http://localhost:4173,http://127.0.0.1:4173,https://argenisbackend.com",
        validation_alias=AliasChoices("ALLOWED_ORIGINS", "ORIGENS_PERMITIDAS"),
    )
    regex_allowed_origins: str | None = Field(
        default=r"^(https://(?:[a-zA-Z0-9\-]+\.)?argenisbackend\.com|https://portfolio(?:-[a-zA-Z0-9\-]+)?-argenis1412s-projects\.vercel\.app|http://localhost:\d+|http://127\.0\.0\.1:\d+)$",
        validation_alias=AliasChoices(
            "REGEX_ALLOWED_ORIGINS", "REGEX_ORIGENS_PERMITIDAS"
        ),
    )
    resend_api_key: str = Field(
        default="",
        alias="RESEND_API_KEY",
    )
    resend_from_email: str = Field(
        default="onboarding@resend.dev",
        alias="RESEND_FROM_EMAIL",
    )
    resend_to_email: str = Field(
        default="",
        alias="RESEND_TO_EMAIL",
    )
    database_url: str = Field(
        default="sqlite+aiosqlite:///./dev.db",
        alias="DATABASE_URL",
    )
    redis_url: str | None = Field(
        default=None,
        alias="REDIS_URL",
        description="Redis URL for cache and rate limiting (e.g., redis://localhost:6379/0).",
    )

    # --- Observability ---
    sentry_dsn: str = Field(
        default="",
        alias="SENTRY_DSN",
        description="Sentry DSN. Leave empty to disable (development/tests).",
    )
    sentry_traces_sample_rate: float = Field(
        default=0.2,
        alias="SENTRY_TRACES_SAMPLE_RATE",
        description="Percentage of transactions sent to Sentry (0.0 to 1.0). 0.2 = 20%.",
    )
    otlp_endpoint: str = Field(
        default="",
        alias="OTLP_ENDPOINT",
        description="OTLP endpoint to export traces (e.g., http://jaeger:4318). Empty = ConsoleExporter.",
    )
    redis_socket_timeout_seconds: float = Field(
        default=5.0,
        alias="REDIS_SOCKET_TIMEOUT_SECONDS",
    )
    redis_connect_timeout_seconds: float = Field(
        default=5.0,
        alias="REDIS_CONNECT_TIMEOUT_SECONDS",
    )
    db_connect_timeout_seconds: float = Field(
        default=5.0,
        alias="DB_CONNECT_TIMEOUT_SECONDS",
    )
    db_command_timeout_seconds: float = Field(
        default=10.0,
        alias="DB_COMMAND_TIMEOUT_SECONDS",
    )
    db_pool_size: int = Field(
        default=2,
        alias="DB_POOL_SIZE",
        description="SQLAlchemy pool size (default 2 for serverless/small instances).",
    )
    db_max_overflow: int = Field(
        default=2,
        alias="DB_MAX_OVERFLOW",
        description="SQLAlchemy max overflow connections.",
    )
    db_pool_recycle_seconds: int = Field(
        default=300,
        alias="DB_POOL_RECYCLE_SECONDS",
    )
    db_pool_timeout_seconds: float = Field(
        default=30.0,
        alias="DB_POOL_TIMEOUT_SECONDS",
    )
    db_pool_use_lifo: bool = Field(
        default=True,
        alias="DB_POOL_USE_LIFO",
        description="Use LIFO for pool connections (better for serverless).",
    )
    metrics_basic_auth_username: str = Field(
        default="",
        alias="METRICS_BASIC_AUTH_USERNAME",
    )
    metrics_basic_auth_password: str = Field(
        default="",
        alias="METRICS_BASIC_AUTH_PASSWORD",
    )
    trusted_proxy_depth: int = Field(
        default=1,
        alias="TRUSTED_PROXY_DEPTH",
        description="Number of trusted proxies (Edge/Load Balancer) before the application.",
    )
    trusted_proxy_ips: str = Field(
        default="",
        alias="TRUSTED_PROXY_IPS",
        description=(
            "Comma-separated allowlist of trusted proxy IPs. "
            "Empty = legacy mode (TRUSTED_PROXY_DEPTH only, compatible with Koyeb/dynamic IPs). "
            "Set to your LB/Nginx IP to enable strict anti-spoof mode."
        ),
    )

    def get_allowed_origins(self) -> list[str]:
        """
        Converts origins string into a list.

        Returns:
            List of URLs allowed for CORS.

        Example:
            "http://localhost:5173,http://127.0.0.1:5173"
            → ["http://localhost:5173", "http://127.0.0.1:5173"]
        """
        return [
            origin.strip()
            for origin in self.allowed_origins.split(",")
            if origin.strip()
        ]

    @property
    def debug(self) -> bool:
        """
        Returns True if the environment is development or local.
        This prevents leaking stack traces in production.
        """
        return self.environment in ("development", "local", "desenvolvimento")

    @property
    def is_production(self) -> bool:
        return self.environment in ("production", "producao", "producción")

    @property
    def metrics_basic_auth_enabled(self) -> bool:
        return bool(
            self.metrics_basic_auth_username.strip()
            and self.metrics_basic_auth_password.strip()
        )

    @property
    def trusted_proxy_ip_set(self) -> frozenset:
        """Returns the set of trusted proxy IPs (empty = legacy/compat mode)."""
        return frozenset(
            ip.strip() for ip in self.trusted_proxy_ips.split(",") if ip.strip()
        )

    @property
    def strict_proxy_mode(self) -> bool:
        """True when TRUSTED_PROXY_IPS is configured explicitly (anti-spoof enabled)."""
        return bool(self.trusted_proxy_ip_set)

    def validate_production(self) -> None:
        """Ensures minimum security and infrastructure requirements in production."""
        if not self.is_production:
            return

        errors: list[str] = []

        if self.database_url.startswith("sqlite"):
            errors.append("SQLite is not allowed in production")

        if not self.database_url.startswith("postgresql+asyncpg://"):
            errors.append("DATABASE_URL must use postgresql+asyncpg in production")

        if not self.redis_url:
            errors.append("REDIS_URL is required in production")

        if not self.metrics_basic_auth_enabled:
            errors.append(
                "METRICS_BASIC_AUTH_USERNAME and METRICS_BASIC_AUTH_PASSWORD are required in production"
            )

        if "*" in self.allowed_origins:
            errors.append("ALLOWED_ORIGINS cannot contain wildcard '*' in production")

        if self.regex_allowed_origins and self.regex_allowed_origins.strip() in {
            ".*",
            "^.*$",
        }:
            errors.append("REGEX_ALLOWED_ORIGINS is too permissive for production")

        if errors:
            raise RuntimeError("Invalid production configuration: " + "; ".join(errors))

    def validate_staging(self) -> None:
        if self.environment in ("staging", "homologação") and not self.redis_url:
            import warnings

            warnings.warn(
                "Staging without REDIS_URL: in-memory idempotency will result in race conditions with multiple workers"
            )


# Global settings instance
settings = Settings()
settings.validate_staging()
