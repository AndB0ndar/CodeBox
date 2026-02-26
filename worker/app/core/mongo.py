from pymongo import MongoClient

from .config import config


class MongoDB:
    client: MongoClient = None
    db = None


mongodb = MongoDB()


def connect_to_mongo():
    mongodb.client = MongoClient(config.MONGO_URI)
    mongodb.db = mongodb.client[config.MONGO_DB_NAME]
    print("Worker connected to MongoDB.")


def close_mongo_connection():
    if mongodb.client:
        mongodb.client.close()
        print("Worker disconnected from MongoDB.")

