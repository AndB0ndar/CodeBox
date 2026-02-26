import os

from rq import Worker, Queue
from redis import Redis

from .core.config import config
from .core.mongo import connect_to_mongo


connect_to_mongo()


if __name__ == '__main__':
    redis_conn = Redis.from_url(config.REDIS_URL)

    queue = Queue('default', connection=redis_conn)

    worker = Worker([queue], connection=redis_conn)
    worker.work()

