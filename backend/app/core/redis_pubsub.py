import asyncio
import logging
import aioredis
from typing import Optional, Set

from app.core.config import settings


logger = logging.getLogger(__name__)


class RedisPubSubManager:
    """
    Manages Redis pub/sub connections with auto-reconnect and error handling.
    Provides methods to subscribe, unsubscribe, and iterate over messages.
    """

    def __init__(self, reconnect_attempts: int = 5, reconnect_delay: float = 1.0):
        self.redis: Optional[aioredis.Redis] = None
        self.pubsub: Optional[aioredis.client.PubSub] = None

        self._reconnect_attempts = reconnect_attempts
        self._reconnect_delay = reconnect_delay
        self._subscriptions: Set[str] = set()  # track channels we are subscribed to
        self._closed = False

    async def connect(self) -> None:
        """Establish connection to Redis with retries."""
        attempt = 0
        while attempt < self._reconnect_attempts:
            try:
                self.redis = await aioredis.from_url(
                    settings.REDIS_URL, decode_responses=True
                )
                self.pubsub = self.redis.pubsub()
                logger.info("Redis pub/sub manager connected.")
                return
            except Exception as e:
                attempt += 1
                logger.warning(
                    f"Failed to connect to Redis (attempt {attempt}/{self._reconnect_attempts}): {e}"
                )
                if attempt < self._reconnect_attempts:
                    await asyncio.sleep(self._reconnect_delay)
                else:
                    logger.error("Could not connect to Redis after multiple attempts.")
                    raise

    async def subscribe(self, channel: str) -> None:
        """
        Subscribe to a Redis channel.
        If not connected, raises an exception.
        """
        if not self.pubsub:
            raise RuntimeError("Redis not connected. Call connect() first.")
        await self.pubsub.subscribe(channel)
        self._subscriptions.add(channel)
        logger.debug(f"Subscribed to channel: {channel}")

    async def unsubscribe(self, channel: str) -> None:
        """Unsubscribe from a Redis channel."""
        if self.pubsub:
            await self.pubsub.unsubscribe(channel)
        self._subscriptions.discard(channel)
        logger.debug(f"Unsubscribed from channel: {channel}")

    async def get_message(self, timeout: float = 0.0):
        """
        Retrieve a single message (non‑blocking or with timeout).
        If timeout > 0, waits up to `timeout` seconds for a message.
        Returns None if no message within timeout.
        """
        if not self.pubsub:
            raise RuntimeError("Redis not connected.")
        try:
            if timeout > 0:
                async with asyncio.timeout(timeout):
                    return await self.pubsub.get_message(ignore_subscribe_messages=True)
            else:
                return await self.pubsub.get_message(ignore_subscribe_messages=True)
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            logger.error(f"Error getting message from Redis: {e}")
            await self._handle_connection_loss()
            return None

    async def listens(self):
        """
        Asynchronous generator that yields messages from subscribed channels.
        Automatically reconnects if connection is lost.
        """
        if not self.pubsub:
            raise RuntimeError("Redis not connected.")

        while not self._closed:
            try:
                async for message in self.pubsub.listen():
                    if self._closed:
                        break
                    if message['type'] == 'message':
                        yield message
            except asyncio.CancelledError:
                logger.debug("Listens task cancelled.")
                break
            except Exception as e:
                logger.error(f"Error in Redis pubsub listen: {e}")
                await self._handle_connection_loss()
                if self.pubsub is None:
                    logger.error("Failed to reconnect Redis, stopping listener.")
                    break

    async def _handle_connection_loss(self):
        """Handle disconnection by attempting to reconnect and resubscribe."""
        logger.warning("Redis connection lost. Attempting to reconnect...")
        await self._close_internal()
        try:
            await self.connect()
            for channel in self._subscriptions:
                await self.pubsub.subscribe(channel)
                logger.debug(f"Resubscribed to {channel} after reconnect.")
        except Exception as e:
            logger.error(f"Failed to reconnect to Redis: {e}")
            self.pubsub = None
            self.redis = None

    async def _close_internal(self):
        """Close pubsub and redis without resetting subscription set."""
        if self.pubsub:
            try:
                await self.pubsub.close()
            except Exception:
                pass
            finally:
                self.pubsub = None
        if self.redis:
            try:
                await self.redis.close()
            except Exception:
                pass
            finally:
                self.redis = None

    async def close(self):
        """Cleanly close the pub/sub manager."""
        self._closed = True
        await self._close_internal()
        self._subscriptions.clear()
        logger.info("Redis pub/sub manager closed.")

    def is_connected(self) -> bool:
        """Return True if the Redis connection is active."""
        return self.redis is not None and self.pubsub is not None


pubsub_manager = RedisPubSubManager()

