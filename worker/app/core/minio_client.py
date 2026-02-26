from minio import Minio

from .config import config


def get_minio_client():
    client = Minio(
        config.MINIO_ENDPOINT,
        access_key=config.MINIO_ACCESS_KEY,
        secret_key=config.MINIO_SECRET_KEY,
        secure=config.MINIO_USE_SSL == "true"
    )
    return client

