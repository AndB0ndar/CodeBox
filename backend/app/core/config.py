import os

from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    All variables have sensible defaults for local development.
    """
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='forbid'
    )


    # MongoDB
    MONGO_URI: str = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection URI"
    )
    """MongoDB connection URI."""

    MONGO_DB_NAME: str = Field(
        default="taskrunner",
        description="MongoDB database name"
    )
    """Name of the MongoDB database to use."""

    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379",
        description="Redis URL (used for RQ and pub/sub)"
    )
    """Redis connection URL (used for RQ queue and pub/sub)."""

    # MinIO
    MINIO_ENDPOINT: str = Field(
        default="localhost:9000",
        description="MinIO endpoint (host:port)"
    )
    """MinIO server endpoint (host:port)."""

    MINIO_ACCESS_KEY: str = Field(
        default="minioadmin",
        description="MinIO access key"
    )
    """MinIO access key (username)."""

    MINIO_SECRET_KEY: str = Field(
        default="minioadmin",
        description="MinIO secret key"
    )
    """MinIO secret key (password)."""

    MINIO_BUCKET: str = Field(
        default="task-logs",
        description="MinIO bucket for task logs"
    )
    """MinIO bucket name where task logs are stored."""

    MINIO_USE_SSL: bool = Field(
        default=False,
        description="Use SSL for MinIO connections"
    )
    """Whether to use SSL for MinIO connections."""

    # API
    PROJECT_NAME: str = Field(
        default="Task Runner API",
        description="Name of the FastAPI application"
    )
    """Name of the FastAPI application."""

    VERSION: str = Field(
        default="0.1.0",
        description="API version"
    )
    """API version."""

    # CORS
    ALLOWED_ORIGINS: List[str] = Field(
        default=["*"],
        description="List of allowed CORS origins"
    )
    """List of allowed CORS origins."""


    # ---------- Validation ----------
    @field_validator("REDIS_URL")
    def validate_redis_url(cls, v: str) -> str:
        """Making sure that the Redis URL starts with redis://."""
        if not v.startswith("redis://"):
            raise ValueError('REDIS_URL must start with "redis://"')
        return v

    @field_validator("MINIO_ENDPOINT")
    def validate_minio_endpoint(cls, v: str) -> str:
        """We check that the port (host:port) is specified."""
        if ":" not in v:
            raise ValueError(
                'MINIO_ENDPOINT must include port (e.g., "localhost:9000")'
            )
        return v

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v):
        """
        Converts a string from an environment variable
        (separated by commas) to a list.
        If the value is already a list, it leaves it as it is.
        """
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("MINIO_USE_SSL", mode="before")
    @classmethod
    def parse_bool(cls, v):
        """
        Converts string values 'true'/'false' to a Boolean type.
        Pydantic does this automatically for bool,
        but we'll leave it for reliability.
        """
        if isinstance(v, str):
            return v.lower() == "true"
        return bool(v)


settings = Settings()

