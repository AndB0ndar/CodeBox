import uuid

from datetime import datetime
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any


class TaskCreate(BaseModel):
    code: str
    language: str

    cpu_limit: Optional[float] = 1.0
    memory_limit: Optional[str] = "256m"
    timeout: Optional[int] = 30

    @validator('memory_limit')
    def validate_memory_limit(cls, v):
        import re
        if not re.match(r'^\d+(\.\d+)?[bBkKmMgG]?$', v):
            raise ValueError('memory_limit must be like 256m, 1g, 512')
        return v


class TaskInDB(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")

    code: str
    language: str

    status: str = "queued"  # queued, running, completed, failed, timeout

    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    exit_code: Optional[int] = None

    logs_object: Optional[str] = None   # name obj in MinIO
    logs_size: Optional[int] = None     # size in bytes

    metrics: Optional[Dict[str, Any]] = None

    cpu_limit: float = 1.0
    memory_limit: str = "256m"
    timeout: int = 30

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

