import re
import uuid

from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class TaskStatus(str, Enum):
    """
    Enumeration of possible task execution statuses.
    """
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

    @classmethod
    def terminal_statuses(cls):
        """
        Return a set of statuses that indicate the task has finished execution.
        """
        return {cls.COMPLETED, cls.FAILED, cls.TIMEOUT}


class TaskCreate(BaseModel):
    """
    Request model for creating a new task.
    """
    code: str = Field(
        ...,
        description="Source code to execute",
        examples=['print("Hello, World!")', 'console.log("Hi");'],
    )
    language: str = Field(
        ...,
        description="Programming language (e.g., python, node)",
        examples=['python', 'node', 'go'],
    )

    cpu_limit: Optional[float] = Field(
        1.0, description="CPU limit in cores", examples=[0.5, 1.0, 2.0],
    )
    memory_limit: Optional[str] = Field(
        "256m",
        description="Memory limit (e.g., 256m, 1g)",
        examples=['128m', '256m', '512m', '1g'],
    )
    timeout: Optional[int] = Field(
        30,
        description="Execution timeout in seconds",
        examples=[10, 30, 60],
    )

    @validator('memory_limit')
    def validate_memory_limit(cls, v):
        """
        Ensure memory_limit follows
        Kubernetes‑like format (e.g., 256m, 1g, 512).
        """
        if not re.match(r'^\d+(\.\d+)?[bBkKmMgG]?$', v):
            raise ValueError('memory_limit must be like 256m, 1g, 512')
        return v


class TaskInDB(BaseModel):
    """
    Task document stored in MongoDB.
    """
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        alias="_id",
        description="Unique task identifier"
    )

    code: str = Field(..., description="Source code to execute")
    language: str = Field(..., description="Programming language")

    status: TaskStatus = Field(
        default=TaskStatus.QUEUED,
        description="Current task status"
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when task was created"
    )
    started_at: Optional[datetime] = Field(
        None, description="Timestamp when execution started"
    )
    finished_at: Optional[datetime] = Field(
        None, description="Timestamp when execution finished"
    )

    exit_code: Optional[int] = Field(
        None, description="Exit code of the process (if available)"
    )

    logs_object: Optional[str] = Field(
        None, description="MinIO object name where logs are stored"
    )
    logs_size: Optional[int] = Field(
        None, description="Size of logs in bytes"
    )

    metrics: Optional[Dict[str, Any]] = Field(
        None, description="Execution metrics (CPU, memory, etc.)"
    )

    cpu_limit: float = Field(
        1.0,
        description="CPU limit in cores"
    )
    memory_limit: str = Field(
        "256m",
        description="Memory limit (e.g., 256m, 1g)"
    )
    timeout: int = Field(
        30, 
        description="Execution timeout in seconds"
    )

    @property
    def is_finished(self) -> bool:
        """Return True if the task has reached a terminal status."""
        return self.status in TaskStatus.terminal_statuses()

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "123",
                "code": "print('hello')",
                "language": "python",
                "status": "completed",
                "created_at": "2023-01-01T00:00:00",
                "logs_object": "tasks/123.log",
                "cpu_limit": 1.0,
                "memory_limit": "256m",
                "timeout": 30,
            }
        }

