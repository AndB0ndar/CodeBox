from rq import Queue
from redis import Redis

from jose import JWTError, jwt

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings
from app.core.database import mongodb
from app.core.minio import minio_client
from app.core.security import verify_password
from app.core.redis_pubsub import pubsub_manager

from app.services.task_service import TaskService
from app.services.user_service import UserService


# RQ queue setup
redis_conn = Redis.from_url(settings.REDIS_URL)
task_queue = Queue(connection=redis_conn)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def get_task_service() -> TaskService:
    """
    Dependency provider for TaskService.
    Uses the globally initialized MongoDB, MinIO, pubsub, and queue.
    """

    return TaskService(
        db=mongodb.db,
        minio=minio_client,
        pubsub=pubsub_manager,
        task_queue=task_queue,
    )


def get_user_service() -> UserService:
    """
    Dependency provider for UserService.
    Uses the globally initialized MongoDB.
    """
    return UserService(db=mongodb.db)


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = await mongodb.db.users.find_one({"username": username})
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user = Depends(get_current_user)):
    if not current_user.get("is_active", True):
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

