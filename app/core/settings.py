"""Application configuration loaded from environment variables or .env file."""

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


# Singleton instance used throughout the application
settings = Settings()
