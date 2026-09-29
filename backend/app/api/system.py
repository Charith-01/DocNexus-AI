"""System information and health routes."""

from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from app.db.mongodb import ping_database


router = APIRouter(tags=["System"])


@router.get("/")
async def root() -> dict[str, str]:
    """Return basic API information."""

    return {
        "message": "DocNexus AI API is running",
        "version": "0.1.0",
    }


@router.get("/health")
async def health() -> dict[str, str]:
    """Report application and MongoDB health without connection details."""

    if await run_in_threadpool(ping_database):
        return {"status": "healthy", "database": "connected"}
    return {"status": "degraded", "database": "unavailable"}
