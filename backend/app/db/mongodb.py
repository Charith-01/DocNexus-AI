"""Shared MongoDB client, collections, indexes, and health helpers."""

from typing import Any

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError

from app.core.config import settings


client: MongoClient[dict[str, Any]] = MongoClient(
    settings.MONGODB_URI.get_secret_value(),
    serverSelectionTimeoutMS=5_000,
    tz_aware=True,
)
database: Database[dict[str, Any]] = client[settings.MONGODB_DB_NAME]

users_collection = database["users"]
documents_collection = database["documents"]
document_permissions_collection = database["document_permissions"]


def create_indexes() -> None:
    """Create the indexes owned by the Member 1 backend."""

    users_collection.create_index("email", unique=True, name="users_email_unique")

    documents_collection.create_index("owner_id", name="documents_owner_id")
    documents_collection.create_index("status", name="documents_status")
    documents_collection.create_index(
        [("created_at", DESCENDING)], name="documents_created_at"
    )

    document_permissions_collection.create_index(
        [("document_id", ASCENDING), ("user_id", ASCENDING)],
        unique=True,
        name="document_permissions_document_user_unique",
    )


def ping_database() -> bool:
    """Return whether MongoDB responds without exposing connection details."""

    try:
        database.command("ping")
    except PyMongoError:
        return False
    return True


def close_database() -> None:
    """Close the shared MongoDB client."""

    client.close()
