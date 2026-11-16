"""Application configuration module using pydantic-settings."""
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings schema loaded from environment variables or .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    POSTGRES_USER: str = Field(default="postgres")
    POSTGRES_PASSWORD: str = Field(default="change_me")
    POSTGRES_DB: str = Field(default="campus_bookings")
    POSTGRES_HOST: str = Field(default="db")
    POSTGRES_PORT: int = Field(default=5432)
    DATABASE_URL: Optional[str] = Field(default=None)
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8000)
    APP_ENV: str = Field(default="development")

    @property
    def effective_database_url(self) -> str:
        """Return the effective database URL, building a psycopg connection string if needed."""
        if self.DATABASE_URL:
            # Normalize legacy 'postgresql://' or 'postgres://' to 'postgresql+psycopg://' if needed
            url = self.DATABASE_URL
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+psycopg://", 1)
            elif url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+psycopg://", 1)
            return url
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
