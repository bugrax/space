"""
Celery application configuration for scheduled Twitter crawling.
"""
from celery import Celery
from celery.schedules import crontab
import os

# Redis URL (default to localhost)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "saas_finder",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["saas_finder.tasks"]
)

# Celery configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # Timezone
    timezone="UTC",
    enable_utc=True,
    
    # Task settings
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    task_soft_time_limit=240,  # Soft limit at 4 minutes
    
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_concurrency=2,
    
    # Beat schedule - periodic tasks
    beat_schedule={
        # Scan Twitter every 30 minutes for revenue tweets
        "scan-revenue-tweets-every-30-min": {
            "task": "saas_finder.tasks.scan_revenue_tweets",
            "schedule": crontab(minute="*/30"),
            "args": (),
            "options": {"queue": "twitter"}
        },
        
        # Scan hashtags every hour
        "scan-hashtags-hourly": {
            "task": "saas_finder.tasks.scan_hashtags",
            "schedule": crontab(minute=0),  # Every hour at :00
            "args": (["buildinpublic", "indiehackers", "saas", "microsaas"],),
            "options": {"queue": "twitter"}
        },
        
        # Deep scan once a day at 3 AM
        "deep-scan-daily": {
            "task": "saas_finder.tasks.deep_scan",
            "schedule": crontab(hour=3, minute=0),
            "args": (),
            "options": {"queue": "twitter"}
        },
        
        # Cleanup old data weekly
        "cleanup-weekly": {
            "task": "saas_finder.tasks.cleanup_old_data",
            "schedule": crontab(hour=4, minute=0, day_of_week=0),  # Sunday 4 AM
            "args": (),
            "options": {"queue": "maintenance"}
        },
        
        # Update scores every 6 hours
        "rescore-ideas-every-6h": {
            "task": "saas_finder.tasks.rescore_ideas",
            "schedule": crontab(minute=0, hour="*/6"),
            "args": (),
            "options": {"queue": "scoring"}
        },
    },
    
    # Task routing
    task_routes={
        "saas_finder.tasks.scan_*": {"queue": "twitter"},
        "saas_finder.tasks.deep_scan": {"queue": "twitter"},
        "saas_finder.tasks.rescore_*": {"queue": "scoring"},
        "saas_finder.tasks.cleanup_*": {"queue": "maintenance"},
    },
    
    # Default queue
    task_default_queue="default",
)

# Optional: Configure logging
celery_app.conf.update(
    worker_hijack_root_logger=False,
    worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
    worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s",
)


if __name__ == "__main__":
    celery_app.start()
