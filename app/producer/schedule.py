import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from redis import Redis
from rq import Queue
import logging
import time
from datetime import datetime

from app.configuration import get_settings
from app.database import SessionLocal
from app.models import JobHistory, JobStatus, JobTrigger

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()


def create_scheduled_job(queue: Queue, db_session: SessionLocal):
    """
    Create a scheduled job to fetch weather data for all standard cities.
    """
    try:
        # Get all cities configuration
        cities_to_fetch = settings.CITIES.copy()
        
        logger.info(f"Creating scheduled job for cities: {list(cities_to_fetch.keys())}")
        
        # Enqueue job
        job = queue.enqueue(
            'worker.worker.fetch_and_store_weather',
            cities_to_fetch,
            job_timeout='5m'
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
    logger.info("Starting Weather Job Scheduler...")
    logger.info(f"Schedule: Every 60 seconds")
    logger.info(f"Cities: {', '.join(settings.CITIES.keys())}")
    logger.info(f"Connecting to Redis: {settings.REDIS_URL.split('@')[-1]}")
    
    # Connect to Redis
    redis_conn = Redis.from_url(settings.REDIS_URL)
    queue = Queue(connection=redis_conn)
    
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
                logger.info(f"Next job scheduled in 60 seconds...")
            else:
                logger.warning(f"Failed to create job, will retry in 60 seconds...")
            
            # Wait 60 seconds before next job
            time.sleep(60)
            
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Scheduler error: {str(e)}", exc_info=True)
    finally:
        db.close()
        logger.info("Scheduler shut down")


if __name__ == '__main__':
    main()