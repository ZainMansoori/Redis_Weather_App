import logging
import time
from datetime import datetime
from typing import Dict

from redis import Redis
from rq import Queue
from sqlalchemy.orm import Session

from app.configuration import get_settings
from app.database import SessionLocal
from app.models import JobHistory, JobStatus, JobTrigger


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()

QUEUE_NAME = "weather-jobs"
JOB_TIMEOUT = "5m"


def create_scheduled_job(queue: Queue, db_session: Session):
    """
    Create a scheduled job to fetch weather data for all standard cities.
    """
    try:
        # Get all cities configuration
        cities_to_fetch: Dict[str, Dict[str, float]] = settings.CITIES.copy()
        
        logger.info(f"Creating scheduled job for cities: {list(cities_to_fetch.keys())}")
        
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
            trigger=JobTrigger.SCHEDULED
        )
        db_session.add(job_history)
        db_session.commit()
        
        logger.info(f"✓ Scheduled job created: {job.id}")
        return job.id
        
    except Exception as e:
        logger.error(f"✗ Error creating scheduled job: {str(e)}", exc_info=True)
        db_session.rollback()
        return None


def main():
    """
    Main scheduler loop.
    Creates a new weather fetch job every 60 seconds.
    """
    interval = settings.SCHEDULER_INTERVAL_SECONDS
    logger.info("Starting Weather Job Scheduler...")
    logger.info("Schedule: every %s seconds", interval)
    logger.info(f"Cities: {', '.join(settings.CITIES.keys())}")
    logger.info(f"Connecting to Redis: {settings.REDIS_URL.split('@')[-1]}")
    
    # Connect to Redis
    redis_conn = Redis.from_url(settings.REDIS_URL)
    queue = Queue(name=QUEUE_NAME, connection=redis_conn)
    
    # Database session
    db = SessionLocal()
    
    try:
        iteration = 0
        while True:
            iteration += 1
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            logger.info(f"[{current_time}] Scheduler iteration #{iteration}")
            
            # Create scheduled job
            job_id = create_scheduled_job(queue, db)
            
            if job_id:
                logger.info("Next job scheduled in %s seconds...", interval)
            else:
                logger.warning("Failed to create job, will retry in %s seconds...", interval)
            
            # Wait before next job
            time.sleep(interval)
            
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Scheduler error: {str(e)}", exc_info=True)
    finally:
        db.close()
        logger.info("Scheduler shut down")


if __name__ == '__main__':
    main()