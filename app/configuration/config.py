from functools import lru_cache
from typing import Dict

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Service configuration
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8000)
    ALLOWED_ORIGINS: str = Field(default="*")

    # Data stores
    DATABASE_URL: str = Field(..., description="SQLAlchemy connection string")
    REDIS_URL: str = Field(..., description="Redis connection URL")

    # External APIs
    WEATHER_API_URL: str = Field(
        default="https://api.open-meteo.com/v1/forecast",
        description="Base URL for Open-Meteo API",
    )

    # Background processing
    SCHEDULER_INTERVAL_SECONDS: int = Field(default=60, ge=15, le=3600)

    # City metadata
    CITIES: Dict[str, Dict[str, float]] = Field(
        default_factory=lambda: {
            "London": {"latitude": 51.5072, "longitude": -0.1276},
            "New York": {"latitude": 40.7128, "longitude": -74.0060},
            "Tokyo": {"latitude": 35.6762, "longitude": 139.6503},
            "Cairo": {"latitude": 30.0444, "longitude": 31.2357},
        }
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
