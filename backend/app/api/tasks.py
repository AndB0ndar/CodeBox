import json
import asyncio
import urllib.parse

from typing import List, Optional
from datetime import datetime, timedelta

from rq import Queue
from redis import Redis
from sse_starlette.sse import EventSourceResponse

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.core.database import mongodb
from app.core.minio import minio_client
from app.core.redis_pubsub import pubsub_manager
from app.models.task import TaskCreate, TaskInDB


router = APIRouter()

redis_conn = Redis.from_url(settings.REDIS_URL)
task_queue = Queue(connection=redis_conn)


@router.post("/tasks", response_model=dict)
async def create_task(task: TaskCreate):
    task_doc = TaskInDB(**task.dict())
    await mongodb.db.tasks.insert_one(task_doc.model_dump(by_alias=True))
    task_queue.enqueue('app.tasks.run_task', task_doc.id)
    return {"task_id": task_doc.id}


@router.get("/{task_id}", response_model=TaskInDB)
async def get_task(task_id: str):
    task = await mongodb.db.tasks.find_one({"_id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/", response_model=List[TaskInDB])
async def list_tasks(limit: int = 10):
    cursor = mongodb.db.tasks.find().sort("created_at", -1).limit(limit)
    tasks = await cursor.to_list(length=limit)
    return tasks


@router.get("/{task_id}/logs")
async def get_task_logs(task_id: str):
    task = await mongodb.db.tasks.find_one({"_id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not task.get("logs_object"):
        raise HTTPException(status_code=404, detail="Logs not available yet")
    
    try:
        url = minio_client.presigned_get_object(
            bucket_name=settings.MINIO_BUCKET,
            object_name=task["logs_object"],
            expires=timedelta(seconds=5*60)
        )
        return {"url": url}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating logs URL: {str(e)}"
        )


@router.get("/{task_id}/metrics")
async def get_task_metrics(task_id: str):
    task = await mongodb.db.tasks.find_one({"_id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    metrics = task.get("metrics")
    if metrics is None:
        raise HTTPException(status_code=404, detail="Metrics not available")
    return metrics


@router.get("/{task_id}/stream")
async def stream_task_status(task_id: str):
    task = await mongodb.db.tasks.find_one({"_id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_generator():
        status = task.get("status")
        f_finished = status in ['completed', 'failed', 'timeout']
        initial_data = {"task_id": task_id, "status": status}
        if f_finished:
            initial_data["exit_code"] = task.get("exit_code")
        yield {"event": "status_update", "data": json.dumps(initial_data)}
        if f_finished:
            return


        channel = f"task:{task_id}"
        await pubsub_manager.subscribe(channel)
        try:
            while True:
                try:
                    message = await asyncio.wait_for(
                        pubsub_manager.get_message(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                if message and message.get('type') == 'message':
                    data = json.loads(message['data'])
                    yield {
                        "event": "status_update",
                        "data": json.dumps(data)
                    }
                    if data.get('status') in ['completed', 'failed', 'timeout']:
                        break

        except asyncio.CancelledError:
            pass

        finally:
            await pubsub_manager.unsubscribe(channel)

    return EventSourceResponse(event_generator())

