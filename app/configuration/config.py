import os
from dotenv import load_dotenv

load_dotenv(".env")

class Settings(): 
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    # Redis
    REDIS_URL = os.getenv("REDIS_URL")
    
    # Weather API
    WEATHER_API_URL = os.getenv("WEATHER_API_URL")
    
    # Cities Configuration
    CITIES: dict = {
        "London": {"latitude": 51.5072, "longitude": -0.1276},
        "New York": {"latitude": 40.7128, "longitude": -74.0060},
        "Tokyo": {"latitude": 35.6762, "longitude": 139.6503},
        "Cairo": {"latitude": 30.0444, "longitude": 31.2357}
    }
