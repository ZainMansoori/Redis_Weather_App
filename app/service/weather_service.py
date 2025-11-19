import openmeteo_requests
import requests_cache
from retry_requests import retry
from typing import Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class WeatherService:
    def __init__(self):
        # Setup the Open-Meteo API client with cache and retry on error
        cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
        retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
        self.client = openmeteo_requests.Client(session=retry_session)
        self.api_url = "https://api.open-meteo.com/v1/forecast"
    
    def fetch_current_weather(
        self, 
        latitude: float, 
        longitude: float, 
        city_name: str = "Unknown"
    ) -> Optional[Dict]:
        """
        Fetch current weather data for a specific location.
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            city_name: Name of the city (for logging)
        
        Returns:
            Dictionary with weather data or None if failed
        """
        try:
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "current": ["temperature_2m", "wind_speed_10m"],
            }
            
            logger.info(f"Fetching weather for {city_name} (lat: {latitude}, lon: {longitude})")
            
            responses = self.client.weather_api(self.api_url, params=params)
            response = responses[0]
            
            # Process current data
            current = response.Current()
            current_temperature = current.Variables(0).Value()
            current_wind_speed = current.Variables(1).Value()
            current_time = current.Time()
            
            weather_data = {
                "temperature": round(current_temperature, 2),
                "wind_speed": round(current_wind_speed, 2),
                "timestamp": datetime.fromtimestamp(current_time),
                "latitude": response.Latitude(),
                "longitude": response.Longitude()
            }
            
            logger.info(f"Successfully fetched weather for {city_name}: "
                       f"temp={weather_data['temperature']}°C, "
                       f"wind={weather_data['wind_speed']}km/h")
            
            return weather_data
            
        except Exception as e:
            logger.error(f"Error fetching weather for {city_name}: {str(e)}")
            return None
    
    def fetch_multiple_cities(self, cities_config: Dict[str, Dict]) -> Dict[str, Optional[Dict]]:
        """
        Fetch weather data for multiple cities.
        
        Args:
            cities_config: Dictionary with city names as keys and {latitude, longitude} as values
        
        Returns:
            Dictionary with city names as keys and weather data as values
        """
        results = {}
        
        for city_name, coords in cities_config.items():
            weather_data = self.fetch_current_weather(
                latitude=coords["latitude"],
                longitude=coords["longitude"],
                city_name=city_name
            )
            results[city_name] = weather_data
        
        return results