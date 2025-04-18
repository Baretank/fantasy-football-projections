from backend.api.routes.players import router as players_router
from backend.api.routes.projections import router as projections_router
from backend.api.routes.overrides import router as overrides_router
from backend.api.routes.scenarios import router as scenarios_router
from backend.api.routes.draft import router as draft_router
from backend.api.routes.performance import router as performance_router

__all__ = [
    "players_router",
    "projections_router",
    "overrides_router",
    "scenarios_router",
    "draft_router",
    "performance_router",
]
