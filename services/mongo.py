import os
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017")
DB_NAME = os.getenv("MONGO_DB", "hkt_mia")

_client = None


def get_db():
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI)
    return _client[DB_NAME]


def get_collection(zone: str):
    """Return a MongoDB collection for the given zone: raw_zone, clean_zone, curated_zone."""
    return get_db()[zone]
