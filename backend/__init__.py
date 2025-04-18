"""
Fantasy Football Projections Backend Package.

This package contains all the backend components for the Fantasy Football Projections application.
"""

# Import key components for easy access
from backend.database.database import Base, engine, get_db, SessionLocal
from backend.database import models
from backend.services.data_service import DataService
from backend.services.projection_service import ProjectionService
from backend.services.team_stat_service import TeamStatService
from backend.services.override_service import OverrideService
from backend.services.scenario_service import ScenarioService
from backend.services.draft_service import DraftService
from backend.services.cache_service import CacheService, get_cache

__version__ = "0.1.0"

__all__ = [
    # Database components
    "Base", 
    "engine",
    "get_db",
    "SessionLocal",
    "models",
    
    # Services
    "DataService",
    "ProjectionService",
    "TeamStatService",
    "OverrideService",
    "ScenarioService",
    "DraftService",
    "CacheService",
    "get_cache",
    
    # Version
    "__version__",
]
