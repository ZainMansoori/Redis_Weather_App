from datetime import datetime, timezone
import logging
from typing import Dict

from rq import get_current_job
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import JobHistory, JobStatus, WeatherData
from app.service.weather_service import WeatherResult, WeatherService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def fetch_and_store_weather(cities_config: Dict[str, Dict[str, float]]):
    """
    Worker task to fetch weather data for multiple cities and store in database.
    Implements retry logic for failed cities (up to 3 attempts per city).
    
    Args:
        cities_config: Dictionary with city names as keys and {latitude, longitude} as values
    """
    job = get_current_job()
    job_id = job.id if job else "unknown"
    
    logger.info(f"[Job {job_id}] Starting weather fetch for {len(cities_config)} cities")
    
    db: Session = SessionLocal()
    job_record = None
    
    try:
        # Update job status to processing
        job_record = db.query(JobHistory).filter(JobHistory.job_id == job_id).first()
        if job_record:
            job_record.status = JobStatus.PROCESSING
            db.commit()
        
        # Initialize weather service
        weather_service = WeatherService()
        
        # Track failed cities for retry
        failed_cities = {}
        successful_count = 0
        max_retries = 3
        
        # First attempt for all cities
        logger.info(f"[Job {job_id}] First attempt for all cities")
        for city_name, coords in cities_config.items():
            weather_data = weather_service.fetch_current_weather(
                latitude=coords["latitude"],
                longitude=coords["longitude"],
                city_name=city_name
            )
            
            if weather_data:
                # Upsert weather data
                upsert_weather_data(db, city_name, coords, weather_data)
                successful_count += 1
                logger.info(f"[Job {job_id}] ✓ {city_name} - Success")
            else:
                failed_cities[city_name] = coords
                logger.warning(f"[Job {job_id}] ✗ {city_name} - Failed, will retry")
        
        # Retry logic for failed cities
        retry_attempt = 1
        while failed_cities and retry_attempt <= max_retries:
            logger.info(f"[Job {job_id}] Retry attempt {retry_attempt}/{max_retries} "
                       f"for {len(failed_cities)} cities")
            
            cities_to_retry = failed_cities.copy()
            failed_cities.clear()
            
            for city_name, coords in cities_to_retry.items():
                weather_data = weather_service.fetch_current_weather(
                    latitude=coords["latitude"],
                    longitude=coords["longitude"],
                    city_name=city_name
                )
                
                if weather_data:
                    upsert_weather_data(db, city_name, coords, weather_data)
                    successful_count += 1
                    logger.info(f"[Job {job_id}] ✓ {city_name} - Success on retry {retry_attempt}")
                else:
                    failed_cities[city_name] = coords
                    logger.warning(f"[Job {job_id}] ✗ {city_name} - Failed retry {retry_attempt}")
            
            retry_attempt += 1
        
        # Update job status
        if job_record:
            job_record.completed_at = datetime.now(timezone.utc)
            
            if failed_cities:
                job_record.status = JobStatus.FAILED
                failed_city_names = ", ".join(failed_cities.keys())
                job_record.error_message = f"Failed to fetch data for: {failed_city_names}"
                logger.error(f"[Job {job_id}] Completed with failures. "
                           f"Success: {successful_count}/{len(cities_config)}")
            else:
                job_record.status = JobStatus.COMPLETED
                logger.info(f"[Job {job_id}] Completed successfully. "
                          f"All {successful_count} cities updated")
            
            db.commit()
        
        logger.info(f"[Job {job_id}] Job finished. Success: {successful_count}, "
                   f"Failed: {len(failed_cities)}")
        
    except Exception as e:
        logger.error(f"[Job {job_id}] Critical error: {str(e)}", exc_info=True)
        
        # Update job status to failed
        if job_record:
            job_record.status = JobStatus.FAILED
            job_record.completed_at = datetime.now(timezone.utc)
            job_record.error_message = str(e)[:500]
            db.commit()
        
        raise
    
    finally:
        db.close()


def upsert_weather_data(
    db: Session,
    city_name: str,
    coords: Dict[str, float],
    weather_data: WeatherResult,
):
    """
    Upsert weather data for a city (insert or update if exists).
    
    Args:
        db: Database session
        city_name: Name of the city
        coords: Dictionary with latitude and longitude
        weather_data: Dictionary with temperature, wind_speed, and timestamp
    """
    stmt = insert(WeatherData).values(
        city=city_name,
        latitude=coords["latitude"],
        longitude=coords["longitude"],
        temperature=weather_data["temperature"],
        wind_speed=weather_data["wind_speed"],
        last_updated=weather_data["timestamp"]
    )
    
    # On conflict, update all fields except city
    stmt = stmt.on_conflict_do_update(
        index_elements=['city'],
        set_={
            'temperature': stmt.excluded.temperature,
            'wind_speed': stmt.excluded.wind_speed,
            'last_updated': stmt.excluded.last_updated
        }
    )
    
    db.execute(stmt)
    db.commit()