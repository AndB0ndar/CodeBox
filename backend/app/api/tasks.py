import json
import asyncio
import logging
from typing import List

from fastapi.responses import StreamingResponse
from fastapi import APIRouter, Request, HTTPException, Depends, Query

from app.main import limiter
from app.models.task import TaskCreate, TaskInDB
from app.models.user import UserInDB
from app.api.dependencies import get_task_service, get_current_active_user
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
@limiter.limit("5/minute")
async def create_task(
    request: Request,
    task: TaskCreate,
    current_user: UserInDB = Depends(get_current_active_user),
    service: TaskService = Depends(get_task_service),
):
    """Create a task and add it to the queue, with user quota checks."""
    try:
        task_id = await service.create_task(current_user["_id"], task)
    except ValueError as e:
        raise HTTPException(status_code=400 if "exceeds quota" in str(e) or "Too many concurrent" in str(e) else 400, detail=str(e))
    except Exception as e:
        logger.error(f"Task creation failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    return {"task_id": task_id}



@router.get(
    "/{task_id}",
    response_model=TaskInDB,
    summary="Get task details",
    description="Retrieve a task document by its ID.",
    responses={
        404: {"description": "Task not found"},
        403: {"description": "Not authorized to view this task"},
    },
)
@limiter.limit("5/minute")
async def get_task(
    request: Request,
    task_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
    service: TaskService = Depends(get_task_service),
):
    """Fetch a single task from MongoDB, with authorization."""
    task = await service.get_task(
        task_id,
        user_id=current_user["_id"],
        is_admin=current_user.get("is_admin", False)
    )
    if not task:
        exists = await service.get_task(task_id)
        if not exists:
            raise HTTPException(status_code=404, detail="Task not found")
        else:
            raise HTTPException(status_code=403, detail="Not authorized to view this task")
    return task


@router.get(
    "/",
    response_model=List[TaskInDB],
    summary="List tasks",
    description="Return a list of recent tasks, sorted by creation date descending.",
)
@limiter.limit("5/minute")
async def list_tasks(
    request: Request,
    limit: int = Query(10, ge=1, le=100, description="Maximum number of tasks to return"),
    current_user: UserInDB = Depends(get_current_active_user),
    service: TaskService = Depends(get_task_service),
):
    """Fetch tasks with user-based filtering."""
    tasks = await service.list_tasks(
        user_id=current_user["_id"],
        is_admin=current_user.get("is_admin", False),
        limit=limit
    )
    return tasks


@router.get(
    "/{task_id}/logs",
    summary="Get task logs URL",
    description="Generate a pre‑signed URL to download the task logs from MinIO.",
    responses={
        404: {"description": "Task or logs not found"},
        403: {"description": "Not authorized"},
        500: {"description": "MinIO error"},
    },
)
@limiter.limit("5/minute")
async def get_task_logs(
    request: Request,
    task_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
    service: TaskService = Depends(get_task_service),
):
    """Return a temporary URL (valid for 5 minutes) for logs."""
    try:
        url = await service.get_task_logs_url(
            task_id,
            user_id=current_user["_id"],
            is_admin=current_user.get("is_admin", False)
        )
    except Exception as e:
        logger.error(f"MinIO error for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate logs URL")

    if url is None:
        task = await service.get_task(
            task_id,
            user_id=current_user["_id"],
            is_admin=current_user.get("is_admin", False)
        )
        if not task:
            exists = await service.get_task(task_id)
            if not exists:
                raise HTTPException(status_code=404, detail="Task not found")
            else:
                raise HTTPException(status_code=403, detail="Not authorized")
        else:
            raise HTTPException(status_code=404, detail="Logs not available yet")

    return {"url": url}


@router.get(
    "/{task_id}/metrics",
    summary="Get task metrics",
    description="Retrieve execution metrics (CPU, memory, etc.) for a completed task.",
    responses={
        404: {"description": "Task or metrics not found"},
        403: {"description": "Not authorized"},
    },
)
@limiter.limit("5/minute")
async def get_task_metrics(
    request: Request,
    task_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
    service: TaskService = Depends(get_task_service),
):
    """Return the metrics object stored with the task."""
    metrics = await service.get_task_metrics(
        task_id,
        user_id=current_user["_id"],
        is_admin=current_user.get("is_admin", False)
    )
    if metrics is None:
        # Проверяем доступность задачи
        task = await service.get_task(
            task_id,
            user_id=current_user["_id"],
            is_admin=current_user.get("is_admin", False)
        )
        if not task:
            exists = await service.get_task(task_id)
            if not exists:
                raise HTTPException(status_code=404, detail="Task not found")
            else:
                raise HTTPException(status_code=403, detail="Not authorized")
        else:
            raise HTTPException(status_code=404, detail="Metrics not available")
    return metrics


async def _stream_wrapper(
    request: Request,
    service: TaskService,
    task_id: str,
    user_id: str,
    is_admin: bool
):
    """Wrapper for SSE generator that includes user context."""
    try:
        async for event in service.status_event_generator(task_id, user_id, is_admin):
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
        200: {"description": "Server‑Sent Events stream", "content": {"text/event-stream": {}}},
        404: {"description": "Task not found"},
        403: {"description": "Not authorized"},
    },
)
async def stream_task_status(
    request: Request,
    task_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
    service: TaskService = Depends(get_task_service),
):
    """Subscribe to Redis pub/sub and stream task status updates with authorization."""
    # Проверка существования и доступа перед началом стрима
    task = await service.get_task(
        task_id,
        user_id=current_user["_id"],
        is_admin=current_user.get("is_admin", False)
    )
    if not task:
        exists = await service.get_task(task_id)
        if not exists:
            raise HTTPException(status_code=404, detail="Task not found")
        else:
            raise HTTPException(status_code=403, detail="Not authorized to view this task")

    logger.info(f"Starting status stream for task {task_id}")
    return StreamingResponse(
        _stream_wrapper(request, service, task_id, current_user["_id"], current_user.get("is_admin", False)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

