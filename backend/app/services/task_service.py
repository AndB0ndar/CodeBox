import re
import json
import time
import logging

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, AsyncGenerator

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
        self.collection = self.db.tasks
        self.users_collection = self.db.users
        self.minio = minio
        self.pubsub = pubsub
        self.task_queue = task_queue


    async def _check_user_quotas(self, user_id: str, task_create: TaskCreate) -> None:
        user = await self._get_user(user_id)
        if not user:
            raise ValueError("User not found")
        return  # TODO

        # 1. count tasks
        active_count = await self.collection.count_documents({
            "user_id": user_id,
            "status": {"$in": [TaskStatus.QUEUED.value, TaskStatus.RUNNING.value]}
        })
        max_concurrent = user.get("max_concurrent_tasks", 3)
        if active_count >= max_concurrent:
            raise ValueError(f"Too many concurrent tasks (limit: {max_concurrent})")

        # 2. CPU
        max_cpu = user.get("max_cpu", 2.0)
        if task_create.cpu_limit > max_cpu:
            raise ValueError(f"CPU limit {task_create.cpu_limit} exceeds quota {max_cpu}")

        # 3. Memory
        max_memory = user.get("max_memory", 1024)  # MB
        memory_mb = task_create.memory_limit
        if isinstance(memory_mb, str):
            # пример: "512Mi" -> 512
            memory_mb = int(memory_mb.rstrip("Mi"))
        if memory_mb > max_memory:
            raise ValueError(f"Memory limit {memory_mb} MB exceeds quota {max_memory} MB")

        # 4. Timeout
        max_timeout = user.get("max_timeout", 300)
        if task_create.timeout > max_timeout:
            raise ValueError(f"Timeout {task_create.timeout} sec exceeds quota {max_timeout} sec")

    async def _get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        return await self.users_collection.find_one({"_id": user_id})

    async def create_task(self, user_id: str, task_create: TaskCreate) -> str:
        """
        Create a new task document in MongoDB and enqueue it for execution.
        Returns the generated task ID.
        """
        await self._check_user_quotas(user_id, task_create)

        # Create task
        task_doc = TaskInDB(
            **task_create.dict(),
            user_id=user_id,
            created_at=datetime.utcnow(),
            status=TaskStatus.QUEUED.value,
        )
        # Insert in MongoDB
        result = await self.collection.insert_one(task_doc.model_dump(by_alias=True))
        task_id = str(result.inserted_id)

        # Enqueue the task in RQ
        self.task_queue.enqueue('app.tasks.run_task', task_id)
        logger.info(f"Task {task_id} created for user {user_id}")
        return task_id

    async def get_task(self, task_id: str, user_id: Optional[str] = None, is_admin: bool = False) -> Optional[Dict[str, Any]]:
        """Retrieve a task by its ID. Returns None if not found."""
        query = {"_id": task_id}
        if not is_admin and user_id:
            query["user_id"] = user_id
        task = await self.collection.find_one(query)
        if task:
            logger.debug(f"Retrieved task: {task_id}")
        return task

    async def list_tasks(self, user_id: Optional[str] = None, is_admin: bool = False, limit: int = 10) -> List[Dict[str, Any]]:
        """Return a list of recent tasks, sorted by creation date descending."""
        query = {}
        if not is_admin and user_id:
            query["user_id"] = user_id
        cursor = self.collection.find(query).sort("created_at", -1).limit(limit)
        tasks = await cursor.to_list(length=limit)
        logger.info(f"Listed {len(tasks)} tasks for user {user_id or 'all'}")
        return tasks

    async def get_task_logs_url(self, task_id: str, user_id: Optional[str] = None, is_admin: bool = False, expires_seconds: int = 300) -> Optional[str]:
        """
        Generate a presigned URL to download task logs from MinIO.
        Returns None if the task or logs object does not exist.
        Raises an exception if MinIO operation fails.
        """
        task = await self.get_task(task_id, user_id, is_admin)
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
            logger.debug(f"Generated logs URL for task {task_id}")
            return url
        except Exception as e:
            logger.error(f"Error generating logs URL for task {task_id}: {e}")
            raise  # Let the caller decide how to handle (e.g., convert to HTTPException)

    async def get_task_metrics(self, task_id: str, user_id: Optional[str] = None, is_admin: bool = False) -> Optional[Dict[str, Any]]:
        """Retrieve the metrics object for a task. Returns None if task or metrics missing."""
        task = await self.get_task(task_id, user_id, is_admin)
        if not task:
            return None
        return task.get("metrics")

    async def status_event_generator(
        self, task_id: str, user_id: Optional[str] = None, is_admin: bool = False
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

        task = await self.get_task(task_id, user_id, is_admin)
        if not task:
            yield {"event": "error", "data": f"Task {task_id} not found or access denied"}
            return

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

