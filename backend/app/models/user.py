import re
import uuid

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, validator


class UserCreate(BaseModel):
    """
    Request model for creating a new user.
    """
    username: str = Field(
        ...,
        description="Unique username",
        examples=["john_doe", "alice_smith"],
    )
    email: EmailStr = Field(
        ...,
        description="Valid email address",
        examples=["user@example.com"],
    )
    password: str = Field(
        ...,
        description="Plain text password (will be hashed before storage)",
        examples=["SecurePass123!"],
        #min_length=6,
    )


class UserInDB(BaseModel):
    """
    User document stored in MongoDB.
    """
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        alias="_id",
        description="Unique user identifier"
    )
    username: str = Field(..., description="Unique username")
    email: EmailStr = Field(..., description="User email address")
    hashed_password: str = Field(..., description="Bcrypt (or similar) hash of the password")
    is_active: bool = Field(
        default=True,
        description="Whether the account is active (soft delete)",
    )
    is_admin: bool = Field(
        default=False,
        description="Whether the user has administrative privileges",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when user was created",
    )
    # User quotas (resource limits for tasks)
    max_cpu: float = Field(
        2.0,
        description="Maximum CPU cores allowed per task",
        examples=[1.0, 2.0, 4.0],
    )
    max_memory: str = Field(
        "1g",
        description="Maximum memory limit per task (e.g., 256m, 1g)",
        examples=["512m", "1g", "2g"],
    )
    max_timeout: int = Field(
        300,
        description="Maximum allowed execution timeout in seconds",
        examples=[60, 300, 600],
    )
    max_concurrent_tasks: int = Field(
        3,
        description="Maximum number of tasks that can run concurrently for this user",
        examples=[1, 3, 5],
    )

    @validator('max_memory')
    def validate_memory_limit(cls, v):
        """
        Ensure max_memory follows Kubernetes‑like format (e.g., 256m, 1g, 512).
        """
        if not re.match(r'^\d+(\.\d+)?[bBkKmMgG]?$', v):
            raise ValueError('max_memory must be like 256m, 1g, 512')
        return v

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "123e4567-e89b-12d3-a456-426614174000",
                "username": "john_doe",
                "email": "john@example.com",
                "hashed_password": "$2b$12$...",
                "is_active": True,
                "is_admin": False,
                "created_at": "2023-01-01T00:00:00",
                "max_cpu": 2.0,
                "max_memory": "1g",
                "max_timeout": 300,
                "max_concurrent_tasks": 3,
            }
        }


class UserLogin(BaseModel):
    """
    Request model for user authentication.
    """
    username: str = Field(
        ...,
        description="Registered username",
        examples=["john_doe"],
    )
    password: str = Field(
        ...,
        description="Plain text password",
        examples=["SecurePass123!"],
    )


class Token(BaseModel):
    """
    Response model for successful authentication.
    """
    access_token: str = Field(
        ...,
        description="JWT access token",
        examples=["eyJhbGciOiJIUzI1NiIs..."]
    )
    token_type: str = Field(
        default="bearer",
        description="Type of token (usually 'bearer')",
        examples=["bearer"],
    )

