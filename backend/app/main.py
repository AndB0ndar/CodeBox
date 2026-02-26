from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.api import tasks
from app.core.config import settings
from app.core.redis_pubsub import pubsub_manager
from app.core.database import connect_to_mongo, close_mongo_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    await pubsub_manager.connect()

    yield

    # Shutdown
    await close_mongo_connection()
    await pubsub_manager.close()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)


app.include_router(tasks.router, prefix="/api", tags=["tasks"])


@app.get("/health")
async def root():
    return {"status": "Ok!!1!"}

