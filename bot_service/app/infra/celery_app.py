from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "bot-service",
    broker=settings.RABBITMQ_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.llm_tasks"],
)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]

# Explicit import registers llm_request and prevents "Received unregistered task".
import app.tasks.llm_tasks  # noqa: E402, F401
