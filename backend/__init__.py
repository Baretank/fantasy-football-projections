"""
Fantasy Football Projections Backend Package.
"""
from backend.database.database import Base, engine, get_db, SessionLocal
from backend.services.data_service import DataService
from backend.services.projection_service import ProjectionService

__version__ = "0.1.0"

__all__ = [
    'Base',
    'engine',
    'get_db',
    'SessionLocal',
    'DataService',
    'ProjectionService',
    '__version__'
]