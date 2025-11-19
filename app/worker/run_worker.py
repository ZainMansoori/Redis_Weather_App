import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from redis import Redis
from rq import Worker, Queue, Connection
import logging

from app.configuration import get_settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()


def main():
    """Run RQ worker"""
    logger.info("Starting RQ Worker...")
    logger.info(f"Connecting to Redis: {settings.REDIS_URL.split('@')[-1]}")
    
    redis_conn = Redis.from_url(settings.REDIS_URL)
    
    with Connection(redis_conn):
        worker = Worker(['default'], connection=redis_conn)
        logger.info("Worker started and listening for jobs...")
        worker.work(with_scheduler=False)


if __name__ == '__main__':
    main()