from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from backend.api.routes import players_router, projections_router
from backend.database import Base, engine
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
    openapi_url="/openapi.json",
    contact={
        "name": "API Support",
        "email": "api-support@example.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    }
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    players_router, 
    prefix="/api/players", 
    tags=["players"]
)
app.include_router(
    projections_router, 
    prefix="/api/projections", 
    tags=["projections"]
)

# Ensure data directory exists
data_dir = Path("data")
data_dir.mkdir(exist_ok=True)

# Create database tables
Base.metadata.create_all(bind=engine)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
        
    openapi_schema = get_openapi(
        title="Fantasy Football Projections API",
        version="0.1.0",
        description=app.description,
        routes=app.routes,
    )
    
    # Add security schemes if needed in the future
    # openapi_schema["components"]["securitySchemes"] = {...}
    
    # Add global responses
    openapi_schema["components"]["responses"] = {
        "HTTPValidationError": {
            "description": "Validation Error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Validation error description",
                        "code": "VALIDATION_ERROR"
                    }
                }
            }
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": app.version,
        "environment": "development"
    }

@app.on_event("startup")
async def startup_event():
    """Initialize application resources on startup."""
    logger.info("Starting Fantasy Football Projections API")
    try:
        # Verify database connection
        Base.metadata.create_all(bind=engine)
        logger.info("Database connection verified")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("Shutting down Fantasy Football Projections API")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)