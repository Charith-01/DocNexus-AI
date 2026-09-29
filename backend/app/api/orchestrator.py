"""Authenticated query-routing API."""

from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.agents.orchestrator import QueryRouter
from app.auth.authorization import can_access_document
from app.auth.dependencies import get_current_user
from app.db.mongodb import documents_collection
from app.schemas.orchestrator import QueryRouteRequest, QueryRouteResponse


router = APIRouter(prefix="/orchestrator", tags=["Orchestrator"])
query_router = QueryRouter()


@router.post("/route", response_model=QueryRouteResponse)
def route_query(
    payload: QueryRouteRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> QueryRouteResponse:
    """Validate document scope and return the next agent workflow."""

    for document_id in payload.document_ids:
        if not ObjectId.is_valid(document_id):
            raise HTTPException(status_code=403, detail="Document access denied")
        document = documents_collection.find_one({"_id": ObjectId(document_id)})
        if document is None or not can_access_document(document, current_user["_id"]):
            raise HTTPException(status_code=403, detail="Document access denied")

    _message, response = query_router.route(payload, str(current_user["_id"]))
    return response
