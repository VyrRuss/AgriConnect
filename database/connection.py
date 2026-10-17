import os
from functools import lru_cache
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from dotenv import load_dotenv

load_dotenv()


@lru_cache(maxsize=1)
def _client():
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    # A short timeout prevents the site from hanging for a long time if MongoDB is off.
    return MongoClient(uri, serverSelectionTimeoutMS=2000)


def get_database():
    """Return the configured MongoDB database, or None if MongoDB is unavailable."""
    try:
        client = _client()
        client.admin.command("ping")
        return client[os.getenv("MONGO_DB_NAME", "agriconnect")]
    except (PyMongoError, OSError):
        return None
