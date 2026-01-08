"""
Celery-based background worker for flushing Redis click buffer to PostgreSQL.

This is an alternative to worker.py that uses Celery for more advanced features like:
- Distributed task execution
- Task scheduling with celery beat
- Monitoring and retries
- Better scalability

Setup:
1. Install Redis or RabbitMQ as message broker (Redis already available in this project)
2. Start Celery worker: celery -A celery_worker worker --loglevel=info
3. Start Celery beat (scheduler): celery -A celery_worker beat --loglevel=info

Or run both together:
    celery -A celery_worker worker --beat --loglevel=info
"""

import os
import logging
from datetime import datetime, timezone
from celery import Celery
from celery.schedules import crontab
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from db import get_session, init_db
from models import URLStats
from cache import read_and_clear_clicks_atomic

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Celery configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
FLUSH_INTERVAL = int(os.getenv("FLUSH_INTERVAL", "60"))

# Initialize Celery app with Redis as both broker and result backend
celery_app = Celery(
    "url_shortener_worker",
    broker=REDIS_URL,
    backend=REDIS_URL
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes hard timeout
    task_soft_time_limit=25 * 60,  # 25 minutes soft timeout
)

# Configure periodic task schedule
celery_app.conf.beat_schedule = {
    'flush-clicks-every-minute': {
        'task': 'celery_worker.flush_clicks_task',
        'schedule': FLUSH_INTERVAL,  # Run every FLUSH_INTERVAL seconds
    },
}


@celery_app.task(name='celery_worker.flush_clicks_task', bind=True, max_retries=3)
def flush_clicks_task(self):
    """
    Celery task to flush buffered clicks from Redis to PostgreSQL.

    This task runs periodically based on the beat_schedule configuration.
    It has automatic retry on failure with exponential backoff.
    """
    session = None
    try:
        # Read and clear clicks from Redis atomically
        clicks_dict = read_and_clear_clicks_atomic()

        if not clicks_dict:
            logger.debug("No buffered clicks to flush")
            return {"status": "success", "urls_flushed": 0, "total_clicks": 0}

        logger.info(f"Flushing {len(clicks_dict)} URL click buffers to database")

        session = get_session()

        # Use PostgreSQL's INSERT ... ON CONFLICT for efficient upsert
        for url_id, click_count in clicks_dict.items():
            stmt = text("""
                INSERT INTO url_stats (url_id, total_clicks, last_flushed)
                VALUES (:url_id, :clicks, :now)
                ON CONFLICT (url_id)
                DO UPDATE SET
                    total_clicks = url_stats.total_clicks + :clicks,
                    last_flushed = :now
            """)

            session.execute(stmt, {
                "url_id": url_id,
                "clicks": click_count,
                "now": datetime.now(timezone.utc)
            })

        session.commit()

        total_clicks = sum(clicks_dict.values())
        logger.info(f"Successfully flushed {total_clicks} clicks for {len(clicks_dict)} URLs")

        return {
            "status": "success",
            "urls_flushed": len(clicks_dict),
            "total_clicks": total_clicks
        }

    except SQLAlchemyError as e:
        logger.error(f"Database error while flushing clicks: {e}")
        if session:
            session.rollback()
        # Retry the task with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

    except Exception as e:
        logger.error(f"Unexpected error while flushing clicks: {e}")
        if session:
            session.rollback()
        raise

    finally:
        if session:
            session.close()


@celery_app.task(name='celery_worker.cleanup_expired_urls', bind=True)
def cleanup_expired_urls_task(self):
    """
    Optional task to clean up expired URLs (useful for Task 12 in roadmap).

    This can be scheduled to run daily using celery beat.
    """
    session = None
    try:
        session = get_session()

        # Delete expired URLs
        stmt = text("""
            DELETE FROM urls
            WHERE expires_at IS NOT NULL
            AND expires_at < :now
            AND is_active = true
        """)

        result = session.execute(stmt, {"now": datetime.now(timezone.utc)})
        session.commit()

        deleted_count = result.rowcount
        logger.info(f"Cleaned up {deleted_count} expired URLs")

        return {"status": "success", "deleted_count": deleted_count}

    except Exception as e:
        logger.error(f"Error cleaning up expired URLs: {e}")
        if session:
            session.rollback()
        raise

    finally:
        if session:
            session.close()


if __name__ == "__main__":
    # Initialize database tables
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

    # Start Celery worker
    celery_app.start()
