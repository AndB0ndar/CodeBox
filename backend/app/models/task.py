import uuid

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    code: str
    language: str


class TaskInDB(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")

    code: str
    language: str

    status: str = "queued"  # queued, running, completed, failed

    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    exit_code: Optional[int] = None

    logs_object: Optional[str] = None   # name obj in MinIO
    logs_size: Optional[int] = None     # size in bytes

    metrics: Optional[Dict[str, Any]] = None

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "123",
                "code": "print('hello')",
                "language": "python",
                "status": "completed",
                "created_at": "2023-01-01T00:00:00",
                "logs_object": "tasks/123.log"
            }
        }

