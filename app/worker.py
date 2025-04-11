import os
from celery import Celery
from loguru import logger

# Configure Celery
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = os.getenv("REDIS_PORT", 6379)
redis_url = f"redis://{redis_host}:{redis_port}/0"

celery_app = Celery(
    "bittensor_api",
    broker=redis_url,
    backend=redis_url
)

# Configure Celery settings
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_routes={
        "app.tasks.analyze_sentiment_and_stake": {"queue": "blockchain"}
    }
)

# Optional: Configure Celery logging
@celery_app.on_after_configure.connect
def setup_celery_logging(sender, **kwargs):
    logger.info("Celery worker started")

if __name__ == "__main__":
    celery_app.start()