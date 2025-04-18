"""
API Package for Fantasy Football Projections.

This package contains all the API routes and schemas for the application.
"""

from fastapi import APIRouter
from backend.api.routes import (
    players_router,
    projections_router,
    overrides_router,
    scenarios_router,
    draft_router,
    performance_router,
    batch_router
)

api_router = APIRouter()
api_router.include_router(players_router, prefix="/players", tags=["players"])
api_router.include_router(projections_router, prefix="/projections", tags=["projections"])
api_router.include_router(overrides_router, prefix="/overrides", tags=["overrides"])
api_router.include_router(scenarios_router, prefix="/scenarios", tags=["scenarios"])
api_router.include_router(draft_router, prefix="/draft", tags=["draft"])
api_router.include_router(performance_router, prefix="/performance", tags=["performance"])
api_router.include_router(batch_router, prefix="/batch", tags=["batch"])

__all__ = [
    "api_router",
    "players_router",
    "projections_router",
    "overrides_router",
    "scenarios_router",
    "draft_router",
    "performance_router",
    "batch_router",
]
