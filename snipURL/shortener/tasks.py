"""
Celery tasks for background processing.

Optional: Configure Celery to run these tasks periodically.
If not using Celery, use the management commands with cron instead.
"""
from celery import shared_task
from django.db import transaction
from .models import URLStats
from .cache import read_and_clear_clicks_atomic


@shared_task
def flush_clicks_to_db():
    """
    Celery task to flush buffered clicks from Redis to database.

    Configure in celerybeat schedule:
        CELERY_BEAT_SCHEDULE = {
            'flush-clicks': {
                'task': 'shortener.tasks.flush_clicks_to_db',
                'schedule': crontab(minute='*/5'),  # Every 5 minutes
            },
        }
    """
    # Atomically read and clear buffered clicks
    buffered_clicks = read_and_clear_clicks_atomic()

    if not buffered_clicks:
        return {'status': 'no_clicks', 'updated': 0}

    updated_count = 0
    total_clicks = sum(buffered_clicks.values())

    with transaction.atomic():
        for url_id, clicks in buffered_clicks.items():
            try:
                stats, created = URLStats.objects.get_or_create(
                    url_id=url_id,
                    defaults={'total_clicks': 0}
                )

                stats.total_clicks += clicks
                stats.save()
                updated_count += 1

            except Exception as e:
                # Log error but continue processing
                print(f"Error flushing clicks for URL {url_id}: {str(e)}")

    return {
        'status': 'success',
        'updated': updated_count,
        'total_clicks': total_clicks
    }
