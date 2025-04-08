from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager
from backend.api.routes import players_router, projections_router, overrides_router, scenarios_router
from backend.api.routes.batch import router as batch_router
from backend.api.routes.draft import router as draft_router
from backend.api.routes.performance import router as performance_router
from backend.database import Base, engine
from backend.services import TeamStatService
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define the lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize application resources on startup and shutdown."""
    # Startup
    logger.info("Starting Fantasy Football Projections API")
    try:
        # Verify database connection
        Base.metadata.create_all(bind=engine)
        logger.info("Database connection verified")
        
        # Ensure rookies.json exists
        rookie_file = Path("data") / "rookies.json"
        if not rookie_file.exists():
            logger.warning("rookies.json not found in data directory")
        
        # Initialize cache service
        from backend.services.cache_service import get_cache
        cache = get_cache(ttl_seconds=300)  # 5 minute default TTL
        logger.info(f"Cache service initialized")
            
    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}")
        raise
    
    yield  # App runs here
    
    # Shutdown
    logger.info("Shutting down Fantasy Football Projections API")

# Create the FastAPI app with lifespan manager
app = FastAPI(
    title="Fantasy Football Projections API",
    description="""
    The Fantasy Football Projections API provides comprehensive endpoints for managing 
    player data, statistics, and projections. This API supports fantasy football analysis 
    with features including:
    
    * Player statistics and metadata
    * Statistical projections
    * Manual overrides and adjustments
    * Scenario planning and comparison
    * Team-level adjustments
    * Historical data analysis
    
    For detailed documentation, visit the /docs endpoint.
    """,
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(players_router, prefix="/api/players", tags=["players"])
app.include_router(projections_router, prefix="/api/projections", tags=["projections"])
app.include_router(overrides_router, prefix="/api/overrides", tags=["overrides"])
app.include_router(scenarios_router, prefix="/api/scenarios", tags=["scenarios"])
app.include_router(batch_router, prefix="/api/batch", tags=["batch operations"])
app.include_router(draft_router, prefix="/api/draft", tags=["draft tools"])
app.include_router(performance_router, prefix="/api/performance", tags=["performance"])

# Ensure data directory exists
data_dir = Path("data")
data_dir.mkdir(exist_ok=True)

# Create database tables
Base.metadata.create_all(bind=engine)

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": app.version,
        "environment": "development"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)