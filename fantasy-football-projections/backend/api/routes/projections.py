from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from ..schemas import (
    ProjectionResponse,
    AdjustmentRequest,
    ScenarioRequest,
    ScenarioResponse,
    ErrorResponse,
    SuccessResponse
)
from ..database import get_db
from ..services import ProjectionService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get(
    "/player/{player_id}",
    response_model=List[ProjectionResponse],
    responses={
        200: {
            "description": "List of projections for the player",
            "content": {
                "application/json": {
                    "example": [{
                        "projection_id": "123e4567-e89b-12d3-a456-426614174000",
                        "player_id": "789e0123-e89b-12d3-a456-426614174000",
                        "season": 2024,
                        "games": 17,
                        "half_ppr": 280.5,
                        "pass_attempts": 580,
                        "completions": 375,
                        "pass_yards": 4500,
                        "pass_td": 35,
                        "interceptions": 12
                    }]
                }
            }
        },
        404: {
            "model": ErrorResponse,
            "description": "Player not found"
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error"
        }
    }
)
async def get_player_projections(
    player_id: str,
    scenario_id: Optional[str] = Query(
        None, 
        description="Filter projections by scenario ID",
        example="abc123-scenario-id"
    ),
    db: Session = Depends(get_db)
):
    """
    Retrieve all projections for a specific player.
    
    Parameters:
    - **player_id**: Unique identifier for the player
    - **scenario_id**: Optional scenario ID to filter projections
    
    Returns a list of projections including baseline and scenario-specific projections.
    """
    try:
        projection_service = ProjectionService(db)
        projections = await projection_service.get_player_projections(
            player_id=player_id,
            scenario_id=scenario_id
        )
        return projections
    except Exception as e:
        logger.error(f"Error retrieving projections for player {player_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving projections"
        )

@router.post(
    "/player/{player_id}/base",
    response_model=ProjectionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Base projection created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "projection_id": "123e4567-e89b-12d3-a456-426614174000",
                        "player_id": "789e0123-e89b-12d3-a456-426614174000",
                        "season": 2024,
                        "games": 17,
                        "half_ppr": 280.5
                    }
                }
            }
        },
        400: {
            "model": ErrorResponse,
            "description": "Invalid request or unable to create projection"
        },
        404: {
            "model": ErrorResponse,
            "description": "Player not found"
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error"
        }
    }
)
async def create_base_projection(
    player_id: str,
    season: int = Query(
        ..., 
        description="Season to project",
        example=2024,
        ge=2020,
        le=2030
    ),
    db: Session = Depends(get_db)
):
    """
    Create a new baseline projection for a player.
    
    Parameters:
    - **player_id**: Unique identifier for the player
    - **season**: NFL season year to project
    
    Creates a baseline projection using historical data and team context.
    """
    try:
        projection_service = ProjectionService(db)
        projection = await projection_service.create_base_projection(
            player_id=player_id,
            season=season
        )
        if not projection:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not create base projection"
            )
        return projection
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating base projection for player {player_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating projection"
        )

@router.put(
    "/{projection_id}",
    response_model=ProjectionResponse,
    responses={
        200: {
            "description": "Projection updated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "projection_id": "123e4567-e89b-12d3-a456-426614174000",
                        "player_id": "789e0123-e89b-12d3-a456-426614174000",
                        "season": 2024,
                        "games": 17,
                        "half_ppr": 295.2,
                        "adjustments": {
                            "snap_share": 1.1,
                            "target_share": 1.05
                        }
                    }
                }
            }
        },
        404: {
            "model": ErrorResponse,
            "description": "Projection not found"
        },
        422: {
            "model": ErrorResponse,
            "description": "Invalid adjustment values"
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error"
        }
    }
)
async def update_projection(
    projection_id: str,
    request: AdjustmentRequest,
    db: Session = Depends(get_db)
):
    """
    Update a projection with adjustments.
    
    Parameters:
    - **projection_id**: Unique identifier for the projection
    - **request**: Adjustment factors for various metrics
    
    Adjustments can modify usage rates, efficiency metrics, and scoring rates.
    All adjustments are validated for reasonableness before applying.
    """
    try:
        projection_service = ProjectionService(db)
        projection = await projection_service.update_projection(
            projection_id=projection_id,
            adjustments=request.adjustments
        )
        if not projection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Projection not found or update failed"
            )
        return projection
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating projection {projection_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating projection"
        )

@router.post(
    "/scenarios",
    response_model=ScenarioResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Scenario created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "scenario_id": "abc123-scenario-id",
                        "name": "High Usage Scenario",
                        "description": "Increased snap counts and target share",
                        "created_at": "2024-02-15T12:00:00Z"
                    }
                }
            }
        },
        400: {
            "model": ErrorResponse,
            "description": "Invalid request"
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error"
        }
    }
)
async def create_scenario(
    request: ScenarioRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new projection scenario.
    
    Parameters:
    - **name**: Name of the scenario
    - **description**: Optional description of the scenario
    - **base_scenario_id**: Optional ID of the parent scenario
    
    Scenarios allow for what-if analysis and alternative projection modeling.
    """
    try:
        projection_service = ProjectionService(db)
        scenario_id = await projection_service.create_scenario(
            name=request.name,
            description=request.description,
            base_scenario_id=request.base_scenario_id
        )
        if not scenario_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not create scenario"
            )
        return {"scenario_id": scenario_id}
    except Exception as e:
        logger.error(f"Error creating scenario: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating scenario"
        )

@router.put(
    "/team/{team}/adjustments",
    response_model=SuccessResponse,
    responses={
        200: {
            "description": "Team adjustments applied successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "updated_count": 5,
                        "message": "Team adjustments applied successfully"
                    }
                }
            }
        },
        400: {
            "model": ErrorResponse,
            "description": "Invalid adjustments"
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error"
        }
    }
)
async def apply_team_adjustments(
    team: str = Query(..., description="Team abbreviation", example="KC"),
    season: int = Query(
        ..., 
        description="Season to adjust",
        example=2024,
        ge=2020,
        le=2030
    ),
    request: AdjustmentRequest = None,
    db: Session = Depends(get_db)
):
    """
    Apply team-level adjustments to all affected players.
    
    Parameters:
    - **team**: Team abbreviation
    - **season**: Season to adjust
    - **request**: Adjustment factors to apply
    
    Team adjustments maintain mathematical consistency across all affected players.
    """
    try:
        projection_service = ProjectionService(db)
        updated = await projection_service.apply_team_adjustments(
            team=team,
            season=season,
            adjustments=request.adjustments
        )
        return SuccessResponse(
            status="success",
            message="Team adjustments applied successfully",
            data={"updated_count": len(updated)}
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error applying team adjustments for {team}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error applying team adjustments"
        )