from rq import Queue
from redis import Redis

from app.core.config import settings
from app.core.database import mongodb
from app.core.minio import minio_client
from app.core.redis_pubsub import pubsub_manager

from app.services.task_service import TaskService

# RQ queue setup
redis_conn = Redis.from_url(settings.REDIS_URL)
task_queue = Queue(connection=redis_conn)


def get_task_service() -> TaskService:
    """
    Dependency provider for TaskService.
    Uses the globally initialized MongoDB, MinIO, pubsub, and queue.
    """

    return TaskService(
        db=mongodb.db,
        minio=minio_client,
        pubsub=pubsub_manager,
        task_queue=task_queue,
    )

