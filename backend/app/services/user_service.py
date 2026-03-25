import logging

from typing import Optional, Dict, Any
from datetime import timedelta

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings
from app.models.user import UserCreate, UserInDB
from app.core.security import (
    get_password_hash, verify_password, create_access_token
)


logger = logging.getLogger(__name__)


class UserService:
    """
    Service layer for user management.
    Handles user creation, authentication, token generation,
    and quota management.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize the service with a MongoDB database connection.

        Args:
            db: AsyncIOMotorDatabase instance (from the database connection).
        """
        self.db = db
        self.collection = db.users

    async def create_user(self, user_create: UserCreate) -> UserInDB:
        """
        Create a new user document in MongoDB.

        Validates uniqueness of username and email, hashes the password,
        and stores the user. Returns the created UserInDB instance.

        Raises:
            HTTPException: If username or email already exists (status 400).
        """
        # Check username uniqueness
        existing = await self.collection.find_one({"username": user_create.username})
        if existing:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )

        # Check email uniqueness
        existing_email = await self.collection.find_one({"email": user_create.email})
        if existing_email:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Hash password and create user document
        hashed_password = get_password_hash(user_create.password)
        user_doc = UserInDB(
            username=user_create.username,
            email=user_create.email,
            hashed_password=hashed_password
        )

        # Insert into database
        await self.collection.insert_one(user_doc.model_dump(by_alias=True))
        logger.info(f"User created: {user_doc.username} (id: {user_doc.id})")
        return user_doc

    async def get_user_by_username(self, username: str) -> Optional[UserInDB]:
        """
        Retrieve a user by username. Returns UserInDB if found, else None.
        """
        user_doc = await self.collection.find_one({"username": username})
        if user_doc:
            logger.debug(f"Retrieved user by username: {username}")
            return UserInDB(**user_doc)
        return None

    async def get_user_by_id(self, user_id: str) -> Optional[UserInDB]:
        """
        Retrieve a user by its _id field.
        Assumes _id is a string (UUID) – if ObjectId, adjust accordingly.
        """
        user_doc = await self.collection.find_one({"_id": user_id})
        if user_doc:
            logger.debug(f"Retrieved user by id: {user_id}")
            return UserInDB(**user_doc)
        return None

    async def authenticate_user(self, username: str, password: str) -> Optional[UserInDB]:
        """
        Verify credentials and return the user if valid, otherwise None.
        """
        user = await self.get_user_by_username(username)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        logger.debug(f"User authenticated: {username}")
        return user

    def create_access_token(self, user: UserInDB) -> str:
        """
        Generate a JWT access token for the user.

        Args:
            user: The authenticated UserInDB instance.

        Returns:
            Encoded JWT string.
        """
        token = create_access_token(data={"sub": user.username})
        logger.debug(f"Access token created for user: {user.username}")
        return token

    async def update_user_quotas(
        self,
        user_id: str,
        max_cpu: Optional[float] = None,
        max_memory: Optional[str] = None,
        max_timeout: Optional[int] = None,
        max_concurrent_tasks: Optional[int] = None
    ) -> Optional[UserInDB]:
        """
        Update user resource quotas.
        Only fields provided will be updated.

        Returns:
            Updated UserInDB if user exists, else None.
        """
        update_fields = {}
        if max_cpu is not None:
            update_fields["max_cpu"] = max_cpu
        if max_memory is not None:
            update_fields["max_memory"] = max_memory
        if max_timeout is not None:
            update_fields["max_timeout"] = max_timeout
        if max_concurrent_tasks is not None:
            update_fields["max_concurrent_tasks"] = max_concurrent_tasks

        if not update_fields:
            return await self.get_user_by_id(user_id)

        result = await self.collection.find_one_and_update(
            {"_id": user_id},
            {"$set": update_fields},
            return_document=True  # returns the updated document
        )
        if result:
            logger.info(f"Updated quotas for user: {user_id}")
            return UserInDB(**result)
        logger.warning(f"User not found for quota update: {user_id}")
        return None

    async def increment_concurrent_tasks(self, user_id: str) -> bool:
        """
        Increment the number of concurrent tasks for a user.
        Returns True if successful, False if user not found.
        """
        result = await self.collection.update_one(
            {"_id": user_id},
            {"$inc": {"current_concurrent_tasks": 1}}
        )
        if result.modified_count:
            logger.debug(f"Incremented concurrent tasks for user {user_id}")
            return True
        return False

    async def decrement_concurrent_tasks(self, user_id: str) -> bool:
        """
        Decrement the number of concurrent tasks for a user.
        Returns True if successful, False if user not found.
        """
        result = await self.collection.update_one(
            {"_id": user_id},
            {"$inc": {"current_concurrent_tasks": -1}}
        )
        if result.modified_count:
            logger.debug(f"Decremented concurrent tasks for user {user_id}")
            return True
        return False

