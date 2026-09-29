"""Document authorization helpers reusable by later agents."""

from typing import Any

from bson import ObjectId

from app.db.mongodb import document_permissions_collection, documents_collection


def can_access_document(document: dict[str, Any], user_id: ObjectId) -> bool:
    """Return whether a user owns or may view a document."""

    if document.get("owner_id") == user_id:
        return True
    permission = document_permissions_collection.find_one(
        {
            "document_id": document["_id"],
            "user_id": user_id,
            "role": {"$in": ["owner", "viewer"]},
        }
    )
    return permission is not None


def get_authorized_document_ids(user_id: ObjectId) -> list[str]:
    """Return document IDs that retrieval may safely search for a user."""

    owned = documents_collection.find({"owner_id": user_id}, {"_id": 1})
    shared = document_permissions_collection.find(
        {"user_id": user_id, "role": {"$in": ["owner", "viewer"]}},
        {"document_id": 1},
    )
    ids = {str(item["_id"]) for item in owned}
    ids.update(str(item["document_id"]) for item in shared)
    return sorted(ids)
