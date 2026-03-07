import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.redis_pubsub import pubsub_manager
from app.core.database import connect_to_mongo, close_mongo_connection

from app.middleware.logging import LoggingMiddleware


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages application startup and shutdown events.
    Connects to MongoDB and Redis on startup, closes connections on shutdown.
    """
    # Startup
    logger.info("Starting up...")
    try:
        await connect_to_mongo()
        await pubsub_manager.connect()
    except Exception as e:
        logger.critical(f"Failed to start due to: {e}")
        raise
    logger.info("Startup complete.")
    yield
    # Shutdown
    logger.info("Shutting down...")
    await close_mongo_connection()
    await pubsub_manager.close()
    logger.info("Shutdown complete.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",          # Swagger UI
    redoc_url="/redoc",        # ReDoc
)

app.add_middleware(LoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from app.api import tasks
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])


@app.get(
    "/health",
    summary="Health check",
    description="Returns OK if the service is running."
)
async def root():
    """Simple health check endpoint."""
    logger.debug("Health check called")
    return {"status": "Ok!!1!"}

