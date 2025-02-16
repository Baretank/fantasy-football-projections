from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from backend.api.routes import players_router, projections_router
from backend.database import Base, engine
from backend.services import TeamStatsService  # Add new import
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create the FastAPI app
app = FastAPI(
    title="Fantasy Football Projections API",
    description="""
    The Fantasy Football Projections API provides comprehensive endpoints for managing 
    player data, statistics, and projections. This API supports fantasy football analysis 
    with features including:
    
    * Player statistics and metadata
    * Statistical projections
    * Scenario planning
    * Team-level adjustments
    * Historical data analysis
    
    For detailed documentation, visit the /docs endpoint.
    """,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
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

# Ensure data directory exists
data_dir = Path("data")
data_dir.mkdir(exist_ok=True)

# Create database tables
Base.metadata.create_all(bind=engine)

@app.on_event("startup")
async def startup_event():
    """Initialize application resources on startup."""
    logger.info("Starting Fantasy Football Projections API")
    try:
        # Verify database connection
        Base.metadata.create_all(bind=engine)
        logger.info("Database connection verified")
        
        # Ensure rookies.json exists
        rookie_file = data_dir / "rookies.json"
        if not rookie_file.exists():
            logger.warning("rookies.json not found in data directory")
            
    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}")
        raise

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