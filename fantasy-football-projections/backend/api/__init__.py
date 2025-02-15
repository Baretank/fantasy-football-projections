from fastapi import APIRouter
from .routes import players_router, projections_router

api_router = APIRouter()
api_router.include_router(players_router, prefix="/players", tags=["players"])
api_router.include_router(projections_router, prefix="/projections", tags=["projections"])

__all__ = ['api_router']