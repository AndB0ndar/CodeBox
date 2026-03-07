import json
import asyncio
import logging
from typing import List

from fastapi.responses import StreamingResponse
from fastapi import APIRouter, Request, HTTPException, Depends, Query

from app.models.task import TaskCreate, TaskInDB
from app.api.dependencies import get_task_service
from app.services.task_service import TaskService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/",
    response_model=dict,
    summary="Create a new task",
    description="Enqueue a task for execution. Returns the task ID immediately.",
    response_description="Task ID",
)
async def create_task(
    task: TaskCreate,
    service: TaskService = Depends(get_task_service),
):
    """Create a task and add it to the queue."""
    task_id = await service.create_task(task)
    return {"task_id": task_id}


@router.get(
    "/{task_id}",
    response_model=TaskInDB,
    summary="Get task details",
    description="Retrieve a task document by its ID.",
    responses={404: {"description": "Task not found"}},
)
async def get_task(
    task_id: str,
    service: TaskService = Depends(get_task_service),
):
    """Fetch a single task from MongoDB."""
    task = await service.get_task(task_id)
    if not task:
        logger.warning(f"Task not found: {task_id}")
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get(
    "/",
    response_model=List[TaskInDB],
    summary="List tasks",
    description="Return a list of recent tasks, sorted by creation date descending.",
)
async def list_tasks(
    limit: int = Query(
        10,
        ge=1,
        le=100,
        description="Maximum number of tasks to return",
        examples=[5, 10, 20],
    ),
    service: TaskService = Depends(get_task_service),
):
    """Fetch the most recent tasks."""
    tasks = await service.list_tasks(limit)
    return tasks


@router.get(
    "/{task_id}/logs",
    summary="Get task logs URL",
    description="Generate a pre‑signed URL to download the task logs from MinIO.",
    responses={
        404: {"description": "Task or logs not found"},
        500: {"description": "MinIO error"},
    },
)
async def get_task_logs(
    task_id: str,
    service: TaskService = Depends(get_task_service),
):
    """Return a temporary URL (valid for 5 minutes) for logs."""
    try:
        url = await service.get_task_logs_url(task_id)
    except Exception as e:
        logger.error(f"MinIO error for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate logs URL")

    if url is None:
        # Distinguish between task not found and logs not available
        task = await service.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        raise HTTPException(status_code=404, detail="Logs not available yet")

    return {"url": url}


@router.get(
    "/{task_id}/metrics",
    summary="Get task metrics",
    description="Retrieve execution metrics (CPU, memory, etc.) for a completed task.",
    responses={404: {"description": "Task or metrics not found"}},
)
async def get_task_metrics(
    task_id: str,
    service: TaskService = Depends(get_task_service),
):
    """Return the metrics object stored with the task."""
    metrics = await service.get_task_metrics(task_id)
    if metrics is None:
        task = await service.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        raise HTTPException(status_code=404, detail="Metrics not available")
    return metrics


async def _stream_wrapper(request: Request, service: TaskService, task_id: str):
    """
    Wraps the service's status_event_generator to format SSE and handle client disconnection.
    """
    try:
        async for event in service.status_event_generator(task_id):
            if await request.is_disconnected():
                logger.debug(f"Client disconnected from stream {task_id}")
                break

            if "event" in event:
                yield f"event: {event['event']}\ndata: {json.dumps(event['data'])}\n\n"
            else:
                yield f"data: {json.dumps(event['data'])}\n\n"
    except asyncio.CancelledError:
        logger.debug(f"Stream task {task_id} cancelled")
        pass


@router.get(
    "/{task_id}/stream",
    summary="Stream task status (SSE)",
    description="""
    Server‑Sent Events endpoint that pushes real‑time status updates for a task.
    Events are `data` (status update) and `done` (task finished).
    """,
    responses={
        200: {
            "description": "Server‑Sent Events stream",
            "content": {"text/event-stream": {}},
        },
        404: {"description": "Task not found"},
    },
)
async def stream_task_status(
    request: Request,
    task_id: str,
    service: TaskService = Depends(get_task_service),
):
    """Subscribe to Redis pub/sub and stream task status updates."""
    # Quick check that task exists
    # (service generator will also check, but we want early 404)
    task = await service.get_task(task_id)
    if not task:
        logger.warning(f"Task not found for streaming: {task_id}")
        raise HTTPException(status_code=404, detail="Task not found")

    logger.info(f"Starting status stream for task {task_id}")
    return StreamingResponse(
        _stream_wrapper(request, service, task_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
