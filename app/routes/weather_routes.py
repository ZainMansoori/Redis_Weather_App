from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from redis import Redis
from rq import Queue
from typing import List
import logging

from app.database import get_db
from app.configuration import get_settings
from app.constants import JOB_TIMEOUT, QUEUE_NAME
from app.models import WeatherData, JobHistory, JobStatus, JobTrigger
from app.schema import (
    JobCreate, 
    JobResponse, 
    WeatherListResponse, 
    WeatherDataResponse,
    JobHistoryResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


def get_redis_queue():
    """Get Redis Queue instance"""
    redis_conn = Redis.from_url(settings.REDIS_URL)
    return Queue(name=QUEUE_NAME, connection=redis_conn)


@router.post("/job", response_model=JobResponse)
async def create_weather_job(
    job_data: JobCreate = JobCreate(),
    db: Session = Depends(get_db)
):
    """
    Create a new weather fetching job (manual trigger).
    Enqueues a job to fetch weather data for specified cities.
    """
    try:
        # Get Redis queue
        queue = get_redis_queue()
        
        # Prepare cities configuration
        cities_to_fetch = {}
        for city_name in job_data.cities:
            if city_name in settings.CITIES:
                cities_to_fetch[city_name] = settings.CITIES[city_name]
        
        if not cities_to_fetch:
            raise HTTPException(
                status_code=400, 
                detail="No valid cities provided"
            )
        
        # Enqueue job
        job = queue.enqueue(
            "app.worker.rq_worker.fetch_and_store_weather",
            cities_to_fetch,
            job_timeout=JOB_TIMEOUT,
        )
        
        # Create job history record
        job_history = JobHistory(
            job_id=job.id,
            status=JobStatus.PENDING,
            trigger=JobTrigger.MANUAL
        )
        db.add(job_history)
        db.commit()
        
        logger.info(f"Created manual job {job.id} for cities: {list(cities_to_fetch.keys())}")
        
        return JobResponse(
            job_id=job.id,
            status="queued",
            message=f"Weather fetch job created for {len(cities_to_fetch)} cities"
        )
        
    except Exception as e:
        logger.error(f"Error creating job: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create job: {str(e)}")


@router.get("/weather", response_model=WeatherListResponse)
async def get_weather_data(db: Session = Depends(get_db)):
    """
    Get current weather data for all cities.
    Returns the latest weather information and last sync timestamp.
    """
    try:
        # Fetch all weather data
        weather_records = db.query(WeatherData).all()
        
        if not weather_records:
            return WeatherListResponse(data=[], last_sync=None)
        
        # Get the most recent update timestamp
        last_sync = db.query(func.max(WeatherData.last_updated)).scalar()
        
        return WeatherListResponse(
            data=[WeatherDataResponse.from_orm(record) for record in weather_records],
            last_sync=last_sync
        )
        
    except Exception as e:
        logger.error(f"Error fetching weather data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch weather data: {str(e)}")


@router.get("/jobs", response_model=List[JobHistoryResponse])
async def get_job_history(
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get recent job history.
    Returns the most recent job records for display on dashboard.
    """
    try:
        jobs = db.query(JobHistory)\
            .order_by(JobHistory.created_at.desc())\
            .limit(limit)\
            .all()
        
        return [JobHistoryResponse.from_orm(job) for job in jobs]
        
    except Exception as e:
        logger.error(f"Error fetching job history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch job history: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "weather-api"}