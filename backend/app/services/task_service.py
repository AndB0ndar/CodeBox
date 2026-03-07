import json
import time
import logging
from typing import List, Optional, Dict, Any, AsyncGenerator
from datetime import datetime, timedelta

from rq import Queue
from motor.motor_asyncio import AsyncIOMotorDatabase
from miniopy_async import Minio

from app.core.config import settings
from app.core.redis_pubsub import RedisPubSubManager
from app.models.task import TaskCreate, TaskInDB, TaskStatus

logger = logging.getLogger(__name__)


class TaskService:
    """
    Service layer for task management.
    Handles database operations, queue enqueuing,
    log URL generation, and status streaming.
    """

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        minio: Minio,
        pubsub: RedisPubSubManager,
        task_queue: Queue,
    ):
        self.db = db
        self.minio = minio
        self.pubsub = pubsub
        self.task_queue = task_queue

    async def create_task(self, task_create: TaskCreate) -> str:
        """
        Create a new task document in MongoDB and enqueue it for execution.
        Returns the generated task ID.
        """
        task_doc = TaskInDB(**task_create.dict())
        await self.db.tasks.insert_one(task_doc.model_dump(by_alias=True))
        # Enqueue the task in RQ
        self.task_queue.enqueue('app.tasks.run_task', task_doc.id)
        logger.info(f"Task created and enqueued: {task_doc.id}")
        return task_doc.id

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a task by its ID. Returns None if not found."""
        task = await self.db.tasks.find_one({"_id": task_id})
        if task:
            logger.debug(f"Retrieved task: {task_id}")
        return task

    async def list_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Return a list of recent tasks, sorted by creation date descending."""
        cursor = self.db.tasks.find().sort("created_at", -1).limit(limit)
        tasks = await cursor.to_list(length=limit)
        logger.info(f"Listed {len(tasks)} tasks")
        return tasks

    async def get_task_logs_url(self, task_id: str, expires_seconds: int = 300) -> Optional[str]:
        """
        Generate a presigned URL to download task logs from MinIO.
        Returns None if the task or logs object does not exist.
        Raises an exception if MinIO operation fails.
        """
        task = await self.get_task(task_id)
        if not task:
            return None
        logs_object = task.get("logs_object")
        if not logs_object:
            return None
        try:
            url = await self.minio.presigned_get_object(
                bucket_name=settings.MINIO_BUCKET,
                object_name=logs_object,
                expires=timedelta(seconds=expires_seconds)
            )
            logger.debug(f"Generated presigned URL for task {task_id}")
            return url
        except Exception as e:
            logger.error(f"Error generating logs URL for task {task_id}: {e}")
            raise  # Let the caller decide how to handle (e.g., convert to HTTPException)

    async def get_task_metrics(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve the metrics object for a task. Returns None if task or metrics missing."""
        task = await self.get_task(task_id)
        if not task:
            return None
        return task.get("metrics")

    async def status_event_generator(
        self, task_id: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Async generator that yields status events for a task.
        Each yielded item is a dictionary with optional keys:
          - 'data': a status update payload (dict)
          - 'event': an event name (e.g., 'done', 'error')
          - 'data' as string for error/done messages.
        The generator subscribes to the Redis channel and streams live updates.
        If the task is already finished, it yields the final status immediately.
        """
        TERMINAL_STATUSES = TaskStatus.terminal_statuses()
        channel = f"task:{task_id}"

        await self.pubsub.subscribe(channel)
        logger.debug(f"Subscribed to Redis channel {channel} for streaming")

        try:
            # Check initial task status
            task_doc = await self.get_task(task_id)
            if task_doc is None:
                yield {"event": "error", "data": f"Task {task_id} not found"}
                return

            current_status = TaskStatus(task_doc["status"])
            if current_status in TERMINAL_STATUSES:
                data = {
                    "task_id": task_id,
                    "status": current_status.value,
                    "exit_code": task_doc.get("exit_code"),
                    "timestamp": task_doc.get("finished_at", datetime.now()).isoformat()
                }
                yield {"data": data}
                yield {"event": "done", "data": f"Task finished with status {current_status.value}"}
                return

            # Stream live updates
            async for message in self.pubsub.listens():
                try:
                    msg_data = json.loads(message["data"])
                except json.JSONDecodeError:
                    continue

                status_str = msg_data.get("status", "unknown")
                try:
                    status_enum = TaskStatus(status_str)
                except ValueError:
                    status_enum = None

                response_data = {
                    "task_id": msg_data.get("task_id", task_id),
                    "status": status_str,
                    "exit_code": msg_data.get("exit_code"),
                    "timestamp": time.time()
                }
                yield {"data": response_data}

                if status_enum and status_enum in TERMINAL_STATUSES:
                    yield {"event": "done", "data": f"Task finished with status {status_str}"}
                    break

        finally:
            await self.pubsub.unsubscribe(channel)
            logger.debug(f"Unsubscribed from {channel}")

