from celery import Celery

celery_app = Celery(
    "video_tasks",
    broker="redis://localhost:6380/0", # <-- Update this port
    backend="redis://localhost:6380/0"  # <-- And this one
)

# Optional: Configuration for Celery to ensure task serialization
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata"
)