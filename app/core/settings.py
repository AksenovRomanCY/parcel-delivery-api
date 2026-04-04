"""Application configuration loaded from environment variables or .env file."""

from decimal import Decimal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings pulled from environment or .env file.

    Supports MySQL and Redis connection strings, logging level, and
    environment mode. Automatically loads variables from a .env file
    unless overridden by real environment values.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore undeclared env vars
    )

    # Database configuration
    DB_PROTOCOL: str = "mysql+aiomysql"
    DB_USER: str = "root"
    DB_PASSWORD: str = "root"
    DB_HOST: str = "db"
    DB_PORT: str = "3306"
    DB_NAME: str = "delivery"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"{self.DB_PROTOCOL}://{self.DB_USER}:{self.DB_PASSWORD}@"
            f"{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # Redis configuration
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASS: str = "yourstrongpass"

    @property
    def REDIS_URL(self) -> str:
        return f"redis://:{self.REDIS_PASS}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    # Logging and environment mode
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
    ENVIRONMENT: str = "prod"  # or "dev"

    # Delivery formula coefficients
    DELIVERY_WEIGHT_COEFF: Decimal = Decimal("0.5")
    DELIVERY_VALUE_COEFF: Decimal = Decimal("0.01")

    # Delivery job settings
    DELIVERY_BATCH_SIZE: int = 500
    DELIVERY_LOCK_TTL: int = 330
    DELIVERY_JOB_INTERVAL_MIN: int = 5

    # Cache TTL (seconds)
    CACHE_TTL_DEFAULT: int = 60
    CACHE_TTL_RATE: int = 600

    # Rate limiting
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_CREATE: str = "20/minute"
    RATE_LIMIT_LIST: str = "60/minute"
    RATE_LIMIT_DETAIL: str = "60/minute"
    RATE_LIMIT_PARCEL_TYPES: str = "100/minute"
    RATE_LIMIT_RECALC: str = "5/minute"

    @property
    def REDIS_RATE_LIMIT_URL(self) -> str:
        return f"redis://:{self.REDIS_PASS}@{self.REDIS_HOST}:{self.REDIS_PORT}/1"

    # JWT Authentication
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MIN: int = 30
    AUTH_REQUIRED: bool = False

    # Observability
    ENABLE_METRICS: bool = True
    SENTRY_DSN: str = ""
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1


# Singleton instance used throughout the application
settings = Settings()
