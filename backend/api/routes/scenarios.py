from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from ..schemas import (
    ScenarioRequest,
    ScenarioResponse,
    ProjectionResponse,
    ScenarioComparisonRequest,
    ScenarioComparisonResponse,
    ErrorResponse,
    SuccessResponse
)
from backend.database.database import get_db
from backend.services.scenario_service import ScenarioService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post(
    "/",
    response_model=ScenarioResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Scenario created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "scenario_id": "123e4567-e89b-12d3-a456-426614174000",
                        "name": "High Usage Scenario",
                        "description": "Increased snap counts and target share",
                        "is_baseline": False,
                        "base_scenario_id": None,
                        "created_at": "2024-03-15T12:00:00Z",
                        "updated_at": "2024-03-15T12:00:00Z"
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
    - **is_baseline**: Whether this is a baseline scenario
    - **base_scenario_id**: Optional ID of a parent scenario
    
    Creates a new scenario for alternative projection modeling.
    Scenarios can be used for what-if analysis and comparing different projection approaches.
    """
    try:
        scenario_service = ScenarioService(db)
        scenario = await scenario_service.create_scenario(
            name=request.name,
            description=request.description,
            is_baseline=request.is_baseline
        )
        
        if not scenario:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not create scenario"
            )
            
        return scenario
        
    except Exception as e:
        logger.error(f"Error creating scenario: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating scenario"
        )

@router.get(
    "/",
    response_model=List[ScenarioResponse],
    responses={
        200: {
            "description": "List of all scenarios",
            "content": {
                "application/json": {
                    "example": [{
                        "scenario_id": "123e4567-e89b-12d3-a456-426614174000",
                        "name": "Baseline 2024",
                        "description": "Default statistical projection for 2024",
                        "is_baseline": True,
                        "base_scenario_id": None,
                        "created_at": "2024-03-01T12:00:00Z",
                        "updated_at": "2024-03-01T12:00:00Z"
                    }, {
                        "scenario_id": "456e7890-e89b-12d3-a456-426614174000",
                        "name": "High Passing Volume",
                        "description": "Increased passing across the league",
                        "is_baseline": False,
                        "base_scenario_id": "123e4567-e89b-12d3-a456-426614174000",
                        "created_at": "2024-03-15T12:00:00Z",
                        "updated_at": "2024-03-15T12:00:00Z"
                    }]
                }
            }
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error"
        }
    }
)
async def get_all_scenarios(
    db: Session = Depends(get_db)
):
    """
    Retrieve all projection scenarios.
    
    Returns a list of all available projection scenarios.
    """
    try:
        scenario_service = ScenarioService(db)
        scenarios = await scenario_service.get_all_scenarios()
        return scenarios
        
    except Exception as e:
        logger.error(f"Error retrieving scenarios: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving scenarios"
        )

@router.get(
    "/{scenario_id}",
    response_model=ScenarioResponse,
    responses={
        200: {
            "description": "Scenario details",
            "content": {
                "application/json": {
                    "example": {
                        "scenario_id": "123e4567-e89b-12d3-a456-426614174000",
                        "name": "Baseline 2024",
                        "description": "Default statistical projection for 2024",
                        "is_baseline": True,
                        "base_scenario_id": None,
                        "created_at": "2024-03-01T12:00:00Z",
                        "updated_at": "2024-03-01T12:00:00Z"
                    }
                }
            }
        },
        404: {
            "model": ErrorResponse,
            "description": "Scenario not found"
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error"
        }
    }
)
async def get_scenario(
    scenario_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieve a specific scenario.
    
    Parameters:
    - **scenario_id**: Scenario ID
    
    Returns the details of a specific projection scenario.
    """
    try:
        scenario_service = ScenarioService(db)
        scenario = await scenario_service.get_scenario(scenario_id)
        
        if not scenario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scenario not found"
            )
            
        return scenario
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving scenario {scenario_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving scenario"
        )

@router.get(
    "/{scenario_id}/projections",
    response_model=List[ProjectionResponse],
    responses={
        200: {
            "description": "Projections for the scenario",
            "content": {
                "application/json": {
                    "example": [{
                        "projection_id": "abc4567-e89b-12d3-a456-426614174000",
                        "player_id": "def0123-e89b-12d3-a456-426614174000",
                        "scenario_id": "123e4567-e89b-12d3-a456-426614174000",
                        "season": 2024,
                        "games": 17,
                        "half_ppr": 280.5,
                        "pass_attempts": 580,
                        "completions": 375,
                        "pass_yards": 4500,
                        "pass_td": 35
                    }]
                }
            }
        },
        404: {
            "model": ErrorResponse,
            "description": "Scenario not found"
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error"
        }
    }
)
async def get_scenario_projections(
    scenario_id: str,
    position: Optional[str] = Query(None, description="Filter by position"),
    team: Optional[str] = Query(None, description="Filter by team"),
    db: Session = Depends(get_db)
):
    """
    Retrieve all projections for a scenario.
    
    Parameters:
    - **scenario_id**: Scenario ID
    - **position**: Optional position filter (QB, RB, WR, TE)
    - **team**: Optional team filter
    
    Returns all projections associated with the specified scenario.
    Optional filters can be applied for position or team.
    """
    try:
        scenario_service = ScenarioService(db)
        
        # Verify scenario exists
        scenario = await scenario_service.get_scenario(scenario_id)
        if not scenario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scenario not found"
            )
            
        projections = await scenario_service.get_scenario_projections(
            scenario_id=scenario_id,
            position=position,
            team=team
        )
        
        return projections
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving projections for scenario {scenario_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving projections"
        )

@router.post(
    "/{scenario_id}/clone",
    response_model=ScenarioResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Scenario cloned successfully",
            "content": {
                "application/json": {
                    "example": {
                        "scenario_id": "789a1234-e89b-12d3-a456-426614174000",
                        "name": "Copy of Baseline 2024",
                        "description": "Clone of baseline scenario",
                        "is_baseline": False,
                        "base_scenario_id": "123e4567-e89b-12d3-a456-426614174000",
                        "created_at": "2024-03-20T12:00:00Z",
                        "updated_at": "2024-03-20T12:00:00Z"
                    }
                }
            }
        },
        400: {
            "model": ErrorResponse,
            "description": "Invalid request"
        },
        404: {
            "model": ErrorResponse,
            "description": "Source scenario not found"
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error"
        }
    }
)
async def clone_scenario(
    scenario_id: str,
    name: str = Query(..., description="Name for the new scenario"),
    description: Optional[str] = Query(None, description="Description for the new scenario"),
    db: Session = Depends(get_db)
):
    """
    Clone an existing scenario with all its projections.
    
    Parameters:
    - **scenario_id**: Source scenario ID to clone
    - **name**: Name for the new scenario
    - **description**: Optional description for the new scenario
    
    Creates a new scenario by copying all projections from an existing scenario.
    This allows users to create variations of existing scenarios for comparison.
    """
    try:
        scenario_service = ScenarioService(db)
        
        # Verify source scenario exists
        source_scenario = await scenario_service.get_scenario(scenario_id)
        if not source_scenario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source scenario not found"
            )
            
        # Clone the scenario
        new_scenario = await scenario_service.clone_scenario(
            source_scenario_id=scenario_id,
            new_name=name,
            new_description=description
        )
        
        if not new_scenario:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not clone scenario"
            )
            
        return new_scenario
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cloning scenario {scenario_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error cloning scenario"
        )

@router.delete(
    "/{scenario_id}",
    response_model=SuccessResponse,
    responses={
        200: {
            "description": "Scenario deleted successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Scenario deleted successfully"
                    }
                }
            }
        },
        404: {
            "model": ErrorResponse,
            "description": "Scenario not found"
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error"
        }
    }
)
async def delete_scenario(
    scenario_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a scenario and all its projections.
    
    Parameters:
    - **scenario_id**: Scenario ID to delete
    
    Permanently deletes a scenario and all projections associated with it.
    """
    try:
        scenario_service = ScenarioService(db)
        
        # Verify scenario exists
        scenario = await scenario_service.get_scenario(scenario_id)
        if not scenario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scenario not found"
            )
            
        # Delete the scenario
        success = await scenario_service.delete_scenario(scenario_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not delete scenario"
            )
            
        return SuccessResponse(
            status="success",
            message="Scenario deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting scenario {scenario_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting scenario"
        )

@router.post(
    "/compare",
    response_model=ScenarioComparisonResponse,
    responses={
        200: {
            "description": "Scenario comparison data",
            "content": {
                "application/json": {
                    "example": {
                        "scenarios": [
                            {"id": "123e4567-e89b-12d3-a456-426614174000", "name": "Baseline 2024"},
                            {"id": "456e7890-e89b-12d3-a456-426614174000", "name": "High Passing Volume"}
                        ],
                        "players": [
                            {
                                "player_id": "def0123-e89b-12d3-a456-426614174000",
                                "name": "Patrick Mahomes",
                                "team": "KC",
                                "position": "QB",
                                "scenarios": {
                                    "Baseline 2024": {
                                        "half_ppr": 380.5,
                                        "pass_yards": 4500,
                                        "pass_td": 35
                                    },
                                    "High Passing Volume": {
                                        "half_ppr": 420.2,
                                        "pass_yards": 5000,
                                        "pass_td": 40
                                    }
                                }
                            }
                        ]
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
async def compare_scenarios(
    request: ScenarioComparisonRequest,
    db: Session = Depends(get_db)
):
    """
    Compare projections across multiple scenarios.
    
    Parameters:
    - **scenario_ids**: List of scenario IDs to compare
    - **position**: Optional position filter
    
    Returns comparison data for players across the specified scenarios.
    """
    try:
        scenario_service = ScenarioService(db)
        comparison = await scenario_service.compare_scenarios(
            scenario_ids=request.scenario_ids,
            position=request.position
        )
        
        return comparison
        
    except Exception as e:
        logger.error(f"Error comparing scenarios: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error comparing scenarios"
        )