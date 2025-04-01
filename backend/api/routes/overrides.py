from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from ..schemas import (
    StatOverrideRequest,
    StatOverrideResponse,
    BatchOverrideRequest,
    BatchOverrideResponse,
    ErrorResponse,
    SuccessResponse
)
from backend.database.database import get_db
from backend.services.override_service import OverrideService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post(
    "/",
    response_model=StatOverrideResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Override created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "override_id": "123e4567-e89b-12d3-a456-426614174000",
                        "player_id": "789e0123-e89b-12d3-a456-426614174000",
                        "projection_id": "abc4567-e89b-12d3-a456-426614174000",
                        "stat_name": "pass_attempts",
                        "calculated_value": 550.0,
                        "manual_value": 600.0,
                        "notes": "Increased volume expected due to new OC",
                        "created_at": "2024-03-15T12:00:00Z"
                    }
                }
            }
        },
        400: {
            "model": ErrorResponse,
            "description": "Invalid request or unable to create override"
        },
        404: {
            "model": ErrorResponse,
            "description": "Projection not found"
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error"
        }
    }
)
async def create_override(
    request: StatOverrideRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new stat override for a projection.
    
    Parameters:
    - **player_id**: Player ID
    - **projection_id**: Projection ID to override
    - **stat_name**: Name of the stat to override
    - **manual_value**: User-specified value
    - **notes**: Optional notes explaining the override
    
    Creates a manual override for a specific stat in a projection.
    Overrides track both the original calculated value and the manual value.
    Dependent stats are recalculated automatically to maintain consistency.
    """
    try:
        override_service = OverrideService(db)
        override = await override_service.create_override(
            player_id=request.player_id,
            projection_id=request.projection_id,
            stat_name=request.stat_name,
            manual_value=request.manual_value,
            notes=request.notes
        )
        
        if not override:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not create override"
            )
            
        return override
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating override: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating override"
        )

@router.get(
    "/player/{player_id}",
    response_model=List[StatOverrideResponse],
    responses={
        200: {
            "description": "List of overrides for the player",
            "content": {
                "application/json": {
                    "example": [{
                        "override_id": "123e4567-e89b-12d3-a456-426614174000",
                        "player_id": "789e0123-e89b-12d3-a456-426614174000",
                        "projection_id": "abc4567-e89b-12d3-a456-426614174000",
                        "stat_name": "pass_attempts",
                        "calculated_value": 550.0,
                        "manual_value": 600.0,
                        "notes": "Increased volume expected due to new OC",
                        "created_at": "2024-03-15T12:00:00Z"
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
async def get_player_overrides(
    player_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieve all overrides for a player.
    
    Parameters:
    - **player_id**: Player ID
    
    Returns a list of all manual overrides created for the player across all projections.
    """
    try:
        override_service = OverrideService(db)
        overrides = await override_service.get_player_overrides(player_id)
        return overrides
        
    except Exception as e:
        logger.error(f"Error retrieving player overrides: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving overrides"
        )

@router.get(
    "/projection/{projection_id}",
    response_model=List[StatOverrideResponse],
    responses={
        200: {
            "description": "List of overrides for the projection",
            "content": {
                "application/json": {
                    "example": [{
                        "override_id": "123e4567-e89b-12d3-a456-426614174000",
                        "player_id": "789e0123-e89b-12d3-a456-426614174000",
                        "projection_id": "abc4567-e89b-12d3-a456-426614174000",
                        "stat_name": "pass_attempts",
                        "calculated_value": 550.0,
                        "manual_value": 600.0,
                        "notes": "Increased volume expected due to new OC",
                        "created_at": "2024-03-15T12:00:00Z"
                    }]
                }
            }
        },
        404: {
            "model": ErrorResponse,
            "description": "Projection not found"
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error"
        }
    }
)
async def get_projection_overrides(
    projection_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieve all overrides for a projection.
    
    Parameters:
    - **projection_id**: Projection ID
    
    Returns a list of all manual overrides created for the specified projection.
    """
    try:
        override_service = OverrideService(db)
        overrides = await override_service.get_projection_overrides(projection_id)
        return overrides
        
    except Exception as e:
        logger.error(f"Error retrieving projection overrides: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving overrides"
        )

@router.delete(
    "/{override_id}",
    response_model=SuccessResponse,
    responses={
        200: {
            "description": "Override deleted successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Override deleted successfully"
                    }
                }
            }
        },
        404: {
            "model": ErrorResponse,
            "description": "Override not found"
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error"
        }
    }
)
async def delete_override(
    override_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete an override and restore the calculated value.
    
    Parameters:
    - **override_id**: Override ID to delete
    
    Deletes the specified override and restores the original calculated value
    in the projection. Dependent stats are recalculated automatically.
    """
    try:
        override_service = OverrideService(db)
        success = await override_service.delete_override(override_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Override not found or could not be deleted"
            )
            
        return SuccessResponse(
            status="success",
            message="Override deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting override: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting override"
        )

@router.post(
    "/batch",
    response_model=BatchOverrideResponse,
    responses={
        200: {
            "description": "Batch override applied successfully",
            "content": {
                "application/json": {
                    "example": {
                        "results": {
                            "player1": {
                                "success": True,
                                "override_id": "123e4567-e89b-12d3-a456-426614174000",
                                "old_value": 550.0,
                                "new_value": 605.0
                            },
                            "player2": {
                                "success": True,
                                "override_id": "456e7890-e89b-12d3-a456-426614174000",
                                "old_value": 520.0,
                                "new_value": 572.0
                            }
                        }
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
async def batch_override(
    request: BatchOverrideRequest,
    db: Session = Depends(get_db)
):
    """
    Apply the same override to multiple players.
    
    Parameters:
    - **player_ids**: List of player IDs to apply the override to
    - **stat_name**: Name of the stat to override
    - **value**: Either a fixed value or an adjustment method (percentage, increment)
    - **notes**: Optional notes explaining the overrides
    
    Applies the same override to multiple players at once.
    For percentage changes, specify a dictionary with method: "percentage" and amount as percentage points.
    For incremental changes, specify a dictionary with method: "increment" and amount to add/subtract.
    For absolute values, simply provide the numeric value.
    """
    try:
        override_service = OverrideService(db)
        results = await override_service.batch_override(
            player_ids=request.player_ids,
            stat_name=request.stat_name,
            value=request.value,
            notes=request.notes
        )
        
        return results
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error applying batch override: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error applying batch override"
        )