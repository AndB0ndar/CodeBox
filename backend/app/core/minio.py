import logging

from miniopy_async import Minio

from app.core.config import settings


logger = logging.getLogger(__name__)

minio_client = Minio(
    endpoint=settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_USE_SSL,
)
"""Async MinIO client instance for log storage operations."""

logger.debug(f"Async MinIO client initialized for endpoint {settings.MINIO_ENDPOINT}")
