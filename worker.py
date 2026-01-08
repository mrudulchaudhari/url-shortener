"""
Background worker to flush Redis click buffer to PostgreSQL.

This worker runs periodically (every 60 seconds by default) and:
1. Reads buffered clicks from Redis using read_and_clear_clicks_atomic()
2. Updates URLStats table in PostgreSQL with the click counts
3. Creates URLStats records if they don't exist

Run this as a separate process:
    python worker.py
"""

import os
import time
import logging
from datetime import datetime, timezone
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

# Flush interval in seconds
FLUSH_INTERVAL = int(os.getenv("FLUSH_INTERVAL", "60"))


def flush_clicks_to_db():
    """
    Read buffered clicks from Redis and persist them to PostgreSQL URLStats table.

    Uses INSERT ... ON CONFLICT DO UPDATE (upsert) to handle both new and existing records.
    """
    session = None
    try:
        # Read and clear clicks from Redis atomically
        clicks_dict = read_and_clear_clicks_atomic()

        if not clicks_dict:
            logger.debug("No buffered clicks to flush")
            return

        logger.info(f"Flushing {len(clicks_dict)} URL click buffers to database")

        session = get_session()

        # Use PostgreSQL's INSERT ... ON CONFLICT for efficient upsert
        for url_id, click_count in clicks_dict.items():
            # Upsert: insert if not exists, otherwise increment total_clicks
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

    except SQLAlchemyError as e:
        logger.error(f"Database error while flushing clicks: {e}")
        if session:
            session.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error while flushing clicks: {e}")
        if session:
            session.rollback()
        raise
    finally:
        if session:
            session.close()


def run_worker():
    """
    Main worker loop that flushes clicks every FLUSH_INTERVAL seconds.
    """
    logger.info(f"Starting click flush worker (interval: {FLUSH_INTERVAL}s)")

    # Ensure database tables exist
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return

    # Main loop
    while True:
        try:
            flush_clicks_to_db()
        except KeyboardInterrupt:
            logger.info("Worker interrupted by user, shutting down...")
            break
        except Exception as e:
            logger.error(f"Error in worker loop: {e}")
            # Continue running even if one flush fails

        # Sleep until next flush
        time.sleep(FLUSH_INTERVAL)


if __name__ == "__main__":
    run_worker()
