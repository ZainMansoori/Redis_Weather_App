from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, Optional, TypedDict

import openmeteo_requests
import requests_cache
from retry_requests import retry

from app.configuration import get_settings

logger = logging.getLogger(__name__)


class WeatherResult(TypedDict):
    temperature: float
    wind_speed: float
    timestamp: datetime
    latitude: float
    longitude: float


class WeatherService:
    """Wrapper around the Open-Meteo client with cache + retries."""

    def __init__(self) -> None:
        settings = get_settings()
        cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
        retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
        self.client = openmeteo_requests.Client(session=retry_session)
        self.api_url = settings.WEATHER_API_URL

    def fetch_current_weather(
        self, latitude: float, longitude: float, city_name: str = "Unknown"
    ) -> Optional[WeatherResult]:
        """Fetch current temperature and wind speed for a city."""
        try:
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "current": ["temperature_2m", "wind_speed_10m"],
            }

            logger.info(
                "Fetching weather for %s (lat=%s, lon=%s)",
                city_name,
                latitude,
                longitude,
            )

            responses = self.client.weather_api(self.api_url, params=params)
            response = responses[0]
            current = response.Current()
            temperature = round(current.Variables(0).Value(), 2)
            wind_speed = round(current.Variables(1).Value(), 2)
            timestamp = datetime.fromtimestamp(current.Time(), tz=timezone.utc)

            result: WeatherResult = {
                "temperature": temperature,
                "wind_speed": wind_speed,
                "timestamp": timestamp,
                "latitude": response.Latitude(),
                "longitude": response.Longitude(),
            }

            logger.info(
                "Weather for %s => %.2f°C, %.2f km/h",
                city_name,
                temperature,
                wind_speed,
            )
            return result

        except Exception as exc:  # pragma: no cover - network errors
            logger.error("Failed to fetch %s weather: %s", city_name, exc, exc_info=True)
            return None

    def fetch_multiple_cities(
        self, cities_config: Dict[str, Dict[str, float]]
    ) -> Dict[str, Optional[WeatherResult]]:
        """Fetch weather data for multiple cities."""
        results: Dict[str, Optional[WeatherResult]] = {}
        for city_name, coords in cities_config.items():
            results[city_name] = self.fetch_current_weather(
                latitude=coords["latitude"],
                longitude=coords["longitude"],
                city_name=city_name,
            )
        return results
