"""Health check API.

Endpoint for monitoring application health and status.
"""

from fastapi import APIRouter, Response

router = APIRouter()


@router.get("/health")
def health_check() -> dict:
    """Health check endpoint"""
    return {"status": "healthy"}
