"""FastAPI application entry point for DocNexus AI."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError
from starlette.requests import Request

from app.api import auth, documents, intelligence, orchestrator, system
from app.core.config import settings
from app.db.mongodb import close_database, create_indexes


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Initialize MongoDB indexes and close its client on shutdown."""

    try:
        create_indexes()
    except PyMongoError:
        logger.warning("MongoDB is unavailable; indexes were not verified.")
    try:
        yield
    finally:
        close_database()


app = FastAPI(
    title="DocNexus AI API",
    version="0.1.0",
    description="The initial API foundation for the DocNexus AI document management platform.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(PyMongoError)
async def mongodb_error_handler(_: Request, __: PyMongoError) -> JSONResponse:
    """Return a safe response when MongoDB is unavailable."""

    return JSONResponse(status_code=503, content={"detail": "Database unavailable"})


app.include_router(system.router)
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(intelligence.router)
app.include_router(orchestrator.router)
