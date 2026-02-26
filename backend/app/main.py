from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.api.v1 import tasks
from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    yield
    # Shutdown
    await close_mongo_connection()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)


app.include_router(tasks.router, prefix="/api/v1", tags=["tasks"])


@app.get("/")
async def root():
    return {"message": "Task Runner API"}

