import os

from dotenv import load_dotenv


load_dotenv()


class Config:
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
    MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', 'taskrunner')
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
    DOCKER_HOST = os.getenv('DOCKER_HOST', 'unix://var/run/docker.sock')

    MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
    MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
    MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'minioadmin')
    MINIO_BUCKET = os.getenv('MINIO_BUCKET', 'task-logs')
    MINIO_USE_SSL = os.getenv('MINIO_USE_SSL', 'false')


config = Config()

