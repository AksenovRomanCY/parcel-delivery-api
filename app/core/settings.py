"""Application configuration loaded from environment variables or `.env`.

Most modules import the singleton `settings` below, so environment variables
must be set before importing application modules in tests and worker processes.
"""

from decimal import Decimal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings pulled from environment or `.env`.

    The names intentionally mirror `.env.example`; this keeps Docker Compose,
    GitHub Actions, tests, and local runs using the same configuration contract.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore undeclared env vars
    )

    # Database configuration. DB_PROTOCOL allows the ORM URL to be switched
    # without touching code, though the current migrations target MySQL.
    DB_PROTOCOL: str = "mysql+aiomysql"
    DB_USER: str = "root"
    DB_PASSWORD: str = "root"
    DB_HOST: str = "db"
    DB_PORT: str = "3306"
    DB_NAME: str = "delivery"

    @property
    def DATABASE_URL(self) -> str:
        """Return the SQLAlchemy database URL assembled from DB_* settings."""
        return (
            f"{self.DB_PROTOCOL}://{self.DB_USER}:{self.DB_PASSWORD}@"
            f"{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # Redis configuration. DB 0 is used for application cache/rate data, while
    # REDIS_RATE_LIMIT_URL (DB 1) keeps rate-limit counters apart.
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASS: str = "yourstrongpass"

    @property
    def REDIS_URL(self) -> str:
        """Return the Redis URL used by application cache and job metadata."""
        return f"redis://:{self.REDIS_PASS}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    # Logging and environment mode. ENVIRONMENT is also forwarded to Sentry.
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
    ENVIRONMENT: str = "prod"  # or "dev"

    # Delivery formula coefficients. They are Decimals because parcel monetary
    # fields are stored as Numeric/Decimal and should not pass through float math.
    DELIVERY_WEIGHT_COEFF: Decimal = Decimal("0.5")
    DELIVERY_VALUE_COEFF: Decimal = Decimal("0.01")

    # Delivery job settings. LOCK_TTL should be higher than the expected maximum
    # job duration and lower than the scheduler interval if overlap must be rare.
    DELIVERY_BATCH_SIZE: int = 500
    DELIVERY_LOCK_TTL: int = 330
    DELIVERY_JOB_INTERVAL_MIN: int = 5

    # Cache TTLs in seconds. Parcel responses are short-lived because delivery
    # cost can be filled asynchronously after creation.
    CACHE_TTL_DEFAULT: int = 60
    CACHE_TTL_RATE: int = 600

    # Rate limiting values use limits syntax, for example "20/minute".
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_CREATE: str = "20/minute"
    RATE_LIMIT_LIST: str = "60/minute"
    RATE_LIMIT_DETAIL: str = "60/minute"
    RATE_LIMIT_PARCEL_TYPES: str = "100/minute"
    RATE_LIMIT_RECALC: str = "5/minute"

    @property
    def REDIS_RATE_LIMIT_URL(self) -> str:
        """Return the Redis URL reserved for rate-limit counters."""
        return f"redis://:{self.REDIS_PASS}@{self.REDIS_HOST}:{self.REDIS_PORT}/1"

    # Authentication mode:
    # - AUTH_REQUIRED=true requires Bearer JWT and stores parcel ownership in user_id.
    # - AUTH_REQUIRED=false keeps the deprecated anonymous X-Session-Id flow.
    JWT_SECRET_KEY: str = "change-me-in-production-use-32-bytes-minimum"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MIN: int = 30
    AUTH_REQUIRED: bool = True

    # Operational shared-secret for admin-only endpoints such as manual task
    # triggers. Empty string means those endpoints are disabled by default.
    TASK_ADMIN_TOKEN: str = ""

    # Observability. ENABLE_METRICS gates the Prometheus endpoint, and Sentry is
    # disabled when SENTRY_DSN is empty.
    ENABLE_METRICS: bool = True
    SENTRY_DSN: str = ""
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1


# Singleton instance used throughout the application.
settings = Settings()
