"""FastAPI application entry point for DocNexus AI."""

from fastapi import FastAPI


app = FastAPI(
    title="DocNexus AI API",
    version="0.1.0",
    description="The initial API foundation for the DocNexus AI document management platform.",
)


@app.get("/")
async def root() -> dict[str, str]:
    """Return basic API information."""
    return {
        "message": "DocNexus AI API is running",
        "version": "0.1.0",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    """Return the current API health status."""
    return {"status": "healthy"}
