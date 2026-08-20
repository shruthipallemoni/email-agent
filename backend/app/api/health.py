"""
A simple "is the server alive?" endpoint.

This is a standard practice: almost every production backend has a /health
route so that monitoring tools (or you, manually) can quickly check the
server is running, without needing to log in or do anything complicated.
"""

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter()


@router.get("/health")
def health_check():
    settings = get_settings()
    return {
        "status": "ok",
        "app_name": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
    }
