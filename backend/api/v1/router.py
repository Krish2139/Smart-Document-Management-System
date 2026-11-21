"""
API v1 Router definitions
"""
from fastapi import APIRouter
from backend.api.v1.endpoints import (
    health,
    documents,
    categories,
    dashboard,
    activities,
    settings,
    auth
)

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(documents.router)
api_v1_router.include_router(categories.router)
api_v1_router.include_router(dashboard.router)
api_v1_router.include_router(activities.router)
api_v1_router.include_router(settings.router)
