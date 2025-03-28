from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.api.schemas import (
    PlayerResponse, 
    PlayerStats, 
    ErrorResponse,
    SuccessResponse
)
from backend.database.database import get_db
from backend.services.data_service import DataService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get(
    "",
    response_model=List[PlayerResponse],
    responses={
        200: {
            "description": "List of players matching the criteria",
            "content": {
                "application/json": {
                    "example": [{
                        "player_id": "123e4567-e89b-12d3-a456-426614174000",
                        "name": "Patrick Mahomes",
                        "team": "KC",
                        "position": "QB"
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
async def get_players(
    position: Optional[str] = Query(
        None, 
        description="Filter by position (QB, RB, WR, TE)",
        example="QB"
    ),
    team: Optional[str] = Query(
        None, 
        description="Filter by team abbreviation",
        example="KC"
    ),
    db: Session = Depends(get_db)
):
    """
    Retrieve a list of players with optional position and team filters.
    
    - **position**: Optional filter for player position
    - **team**: Optional filter for team abbreviation
    """
    try:
        data_service = DataService(db)
        players = await data_service.get_players(position=position, team=team)
        return players
    except Exception as e:
        logger.error(f"Error retrieving players: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving players"
        )

@router.get(
    "/{player_id}",
    response_model=PlayerResponse,
    responses={
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
async def get_player(
    player_id: str = Query(
        ..., 
        description="Unique player identifier",
        example="123e4567-e89b-12d3-a456-426614174000"
    ),
    db: Session = Depends(get_db)
):
    """
    Retrieve detailed information for a specific player.
    
    - **player_id**: Unique identifier for the player
    """
    try:
        data_service = DataService(db)
        player = await data_service.get_player(player_id)
        if not player:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Player not found"
            )
        return player
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving player {player_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving player"
        )

@router.get(
    "/{player_id}/stats",
    response_model=PlayerStats,
    responses={
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
async def get_player_stats(
    player_id: str = Query(
        ..., 
        description="Unique player identifier",
        example="123e4567-e89b-12d3-a456-426614174000"
    ),
    season: Optional[int] = Query(
        None, 
        description="Filter by season year",
        example=2023
    ),
    db: Session = Depends(get_db)
):
    """
    Retrieve historical statistics for a player.
    
    - **player_id**: Unique identifier for the player
    - **season**: Optional filter for specific season
    """
    try:
        data_service = DataService(db)
        
        # Get player info
        player = await data_service.get_player(player_id)
        if not player:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Player not found"
            )
            
        # Get stats
        stats = await data_service.get_player_stats(player_id, season)
        
        # Transform stats into structured dictionary
        stats_dict = {}
        for stat in stats:
            if stat.season not in stats_dict:
                stats_dict[stat.season] = {}
            if stat.week:
                if 'weeks' not in stats_dict[stat.season]:
                    stats_dict[stat.season]['weeks'] = {}
                if stat.week not in stats_dict[stat.season]['weeks']:
                    stats_dict[stat.season]['weeks'][stat.week] = {}
                stats_dict[stat.season]['weeks'][stat.week][stat.stat_type] = stat.value
            else:
                stats_dict[stat.season][stat.stat_type] = stat.value
                
        return PlayerStats(
            player_id=player.player_id,
            name=player.name,
            team=player.team,
            position=player.position,
            stats=stats_dict
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving stats for player {player_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving player statistics"
        )