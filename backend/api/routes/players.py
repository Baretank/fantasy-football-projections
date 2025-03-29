from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any

from backend.database.database import get_db
from backend.services.query_service import QueryService
from backend.services.cache_service import get_cache
from backend.api.schemas import (
    PlayerResponse,
    PlayerStats,
    PlayerSearchResponse,
    OptimizedPlayerResponse,
    PlayerListResponse
)

router = APIRouter(
    prefix="/players",
    tags=["players"]
)

@router.get("/", response_model=PlayerListResponse)
async def get_players(
    name: Optional[str] = None,
    team: Optional[str] = None,
    position: Optional[str] = None,
    include_projections: bool = False,
    include_stats: bool = False,
    min_fantasy_points: Optional[float] = None,
    page: int = Query(1, gt=0),
    page_size: int = Query(20, gt=0, le=100),
    sort_by: str = "name",
    sort_dir: str = Query("asc", regex="^(asc|desc)$"),
    db: Session = Depends(get_db)
):
    """
    Get a paginated list of players with optional filters.
    
    Optimized endpoint with pagination, sorting, and filtering options.
    Can include projection and statistical data for each player.
    """
    service = QueryService(db)
    
    # Build filters
    filters = {}
    if name:
        filters["name"] = name
    if team:
        filters["team"] = team
    if position:
        filters["position"] = position
    if min_fantasy_points:
        filters["min_fantasy_points"] = min_fantasy_points
    
    # Get players with pagination
    players, total_count = await service.get_players_optimized(
        filters=filters,
        include_projections=include_projections,
        include_stats=include_stats,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_dir=sort_dir
    )
    
    # Calculate pagination info
    total_pages = (total_count + page_size - 1) // page_size
    has_next = page < total_pages
    has_prev = page > 1
    
    return {
        "players": players,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_prev": has_prev
        }
    }

@router.get("/search", response_model=PlayerSearchResponse)
async def search_players(
    query: str = Query(..., min_length=2),
    position: Optional[str] = None,
    limit: int = Query(20, gt=0, le=100),
    db: Session = Depends(get_db)
):
    """
    Search for players by name with autocomplete functionality.
    
    Fast endpoint for player search with optional position filtering.
    """
    service = QueryService(db)
    
    players = await service.search_players(
        search_term=query,
        position=position,
        limit=limit
    )
    
    return {
        "query": query,
        "count": len(players),
        "players": players
    }

@router.get("/{player_id}", response_model=OptimizedPlayerResponse)
async def get_player(
    player_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific player.
    
    Returns comprehensive player information with optimized query.
    """
    service = QueryService(db)
    
    # Get player with projected stats
    result = await service.get_player_stats_optimized(
        player_id=player_id
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Player not found")
        
    return result

@router.get("/{player_id}/stats", response_model=Dict[str, Any])
async def get_player_stats(
    player_id: str,
    seasons: Optional[List[int]] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get detailed statistics for a specific player.
    
    Returns comprehensive statistical data for a player,
    optionally filtered by seasons.
    """
    service = QueryService(db)
    
    # Get player with stats for specified seasons
    result = await service.get_player_stats_optimized(
        player_id=player_id,
        seasons=seasons
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Player not found")
        
    return result

@router.get("/seasons", response_model=List[int])
async def get_available_seasons(
    db: Session = Depends(get_db)
):
    """
    Get list of seasons with available data.
    
    Returns a list of all seasons that have player data available.
    """
    service = QueryService(db)
    
    seasons = await service.get_available_seasons()
    return seasons