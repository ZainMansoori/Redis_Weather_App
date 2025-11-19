import logging

from redis import Redis
from rq import Connection, Worker

from app.configuration import get_settings
from app.constants import QUEUE_NAME

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
        worker = Worker([QUEUE_NAME], connection=redis_conn)
        logger.info("Worker listening on queue '%s'...", QUEUE_NAME)
        worker.work(with_scheduler=False)


if __name__ == '__main__':
    main()