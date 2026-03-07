import logging

from motor.motor_asyncio import AsyncIOMotorClient

from .config import settings


logger = logging.getLogger(__name__)


class MongoDB:
    """MongoDB connection holder."""
    client: AsyncIOMotorClient = None
    db = None


mongodb = MongoDB()


async def connect_to_mongo():
    """Create MongoDB connection and store it in the global `mongodb` object."""
    mongodb.client = AsyncIOMotorClient(settings.MONGO_URI)
    mongodb.db = mongodb.client[settings.MONGO_DB_NAME]
    logger.info("Connected to MongoDB.")


async def close_mongo_connection():
    """Close the MongoDB connection."""
    if mongodb.client:
        mongodb.client.close()
        logger.info("Disconnected from MongoDB.")


async def ensure_indexes():
    """
    Create necessary indexes for the tasks collection to optimize queries.
    Called automatically on startup.
    """
    tasks_collection = mongodb.db.tasks

    await tasks_collection.create_index("status", name="status_idx")

    await tasks_collection.create_index("created_at", name="created_at_idx")

    await tasks_collection.create_index(
        [("status", 1), ("created_at", -1)],
        name="status_created_at_idx"
    )

    # TTL index for automatic deletion of old tasks after N days
    from pymongo import ASCENDING
    await tasks_collection.create_index(
        "created_at",
        name="ttl_idx",
        expireAfterSeconds=7 * 24 * 60 * 60  # 7 days
    )

    logger.info("MongoDB indexes ensured for tasks collection.")

