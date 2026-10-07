from __future__ import annotations

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "lenquant",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend or settings.celery_broker_url,
    include=["app.core.tasks"],
)

celery_app.conf.update(
    task_default_queue=settings.celery_default_queue,
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=True,
    timezone="UTC",
    enable_utc=True,
    # Use solo pool to avoid asyncio event loop issues with forked workers
    # The default 'prefork' pool causes RuntimeError: Event loop is closed
    # when tasks use asyncio (via _run helper in tasks.py)
    worker_pool="solo",
    worker_concurrency=1,
)
