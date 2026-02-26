import aioredis

from app.core.config import settings


class RedisPubSubManager:
    def __init__(self):
        self.redis = None
        self.pubsub = None

    async def connect(self):
        self.redis = await aioredis.from_url(
            settings.REDIS_URL, decode_responses=True
        )
        self.pubsub = self.redis.pubsub()

    async def subscribe(self, channel: str):
        await self.pubsub.subscribe(channel)

    async def unsubscribe(self, channel: str):
        await self.pubsub.unsubscribe(channel)

    async def get_message(self):
        return await self.pubsub.get_message(ignore_subscribe_messages=True)

    async def close(self):
        if self.pubsub:
            await self.pubsub.close()
        if self.redis:
            await self.redis.close()


pubsub_manager = RedisPubSubManager()

