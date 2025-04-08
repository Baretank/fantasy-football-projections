from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile, Body, Path
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from datetime import datetime
import os
import logging

from backend.database.database import get_db
from backend.services.query_service import QueryService
from backend.services.cache_service import get_cache
from backend.services.player_import_service import PlayerImportService
from backend.services.rookie_import_service import RookieImportService
from backend.services.rookie_projection_service import RookieProjectionService
from backend.api.schemas import (
    PlayerResponse,
    PlayerStats,
    PlayerSearchResponse,
    OptimizedPlayerResponse,
    PlayerListResponse
)

logger = logging.getLogger(__name__)

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
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
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
    
@router.post("/import", response_model=Dict[str, Any])
async def import_players_from_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Import or update players from a CSV file.
    """
    try:
        # Save uploaded file to temp location
        temp_file = f"temp_{file.filename}"
        with open(temp_file, "wb") as buffer:
            buffer.write(await file.read())
        
        # Process the file
        import_service = PlayerImportService(db)
        success_count, errors = await import_service.import_players_from_csv(temp_file)
        
        # Remove temp file
        os.remove(temp_file)
        
        if success_count == 0 and errors:
            return JSONResponse(
                status_code=400,
                content={"detail": f"Import failed: {errors[0]}" if errors else "Unknown error"}
            )
        
        return {
            "status": "success",
            "imported_count": success_count,
            "errors": errors
        }
        
    except Exception as e:
        logger.error(f"CSV import error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error importing CSV: {str(e)}"
        )

@router.get("/rookies", response_model=List[PlayerResponse])
async def get_rookies(
    position: Optional[str] = Query(None, description="Filter by position"),
    team: Optional[str] = Query(None, description="Filter by team"),
    db: Session = Depends(get_db)
):
    """
    Get all rookies with optional filters.
    """
    from backend.database.models import Player
    query = db.query(Player).filter(Player.status == "Rookie")
    
    if position:
        query = query.filter(Player.position == position)
    if team:
        query = query.filter(Player.team == team)
        
    return query.all()

@router.post("/rookies/import", response_model=Dict[str, Any])
async def import_rookies(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Import rookies from a file (CSV, Excel, or JSON format).
    Automatically detects file format based on extension.
    """
    try:
        # Save uploaded file to temp location
        temp_file = f"temp_{file.filename}"
        with open(temp_file, "wb") as buffer:
            buffer.write(await file.read())
        
        # Process the file
        import_service = RookieImportService(db)
        success_count, errors = await import_service.import_rookies(temp_file)
        
        # Remove temp file
        os.remove(temp_file)
        
        if success_count == 0 and errors:
            return JSONResponse(
                status_code=400,
                content={"detail": f"Import failed: {errors[0]}" if errors else "Unknown error"}
            )
        
        return {
            "status": "success",
            "imported_count": success_count,
            "errors": errors
        }
        
    except Exception as e:
        logger.error(f"Rookie import error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error importing rookie file: {str(e)}"
        )

@router.put("/{player_id}/status", response_model=PlayerResponse)
async def update_player_status(
    player_id: str,
    status: str = Query(..., pattern="^(Active|Injured|Rookie)$"),
    db: Session = Depends(get_db)
):
    """
    Update a player's status (Active/Injured/Rookie).
    """
    from backend.database.models import Player
    player = db.query(Player).filter(Player.player_id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    player.status = status
    player.updated_at = datetime.utcnow()
    db.commit()
    
    return player

@router.put("/{player_id}/depth-chart", response_model=PlayerResponse)
async def update_player_depth_chart(
    player_id: str,
    position: str = Query(..., pattern="^(Starter|Backup|Reserve)$"),
    db: Session = Depends(get_db)
):
    """
    Update a player's depth chart position (Starter/Backup/Reserve).
    """
    from backend.database.models import Player
    player = db.query(Player).filter(Player.player_id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    player.depth_chart_position = position
    player.updated_at = datetime.utcnow()
    db.commit()
    
    return player

@router.post("/batch-update", response_model=Dict[str, Any])
async def batch_update_players(
    updates: List[Dict[str, Any]] = Body(...),
    db: Session = Depends(get_db)
):
    """
    Update multiple players in a single operation.
    
    Each update must include player_id and can optionally include:
    - status
    - depth_chart_position
    - team
    """
    from backend.database.models import Player
    success_count = 0
    errors = []
    
    for update in updates:
        try:
            if 'player_id' not in update:
                errors.append("Missing player_id in update")
                continue
                
            player = db.query(Player).filter(Player.player_id == update['player_id']).first()
            if not player:
                errors.append(f"Player not found: {update['player_id']}")
                continue
                
            if 'status' in update and update['status'] in ['Active', 'Injured', 'Rookie']:
                player.status = update['status']
                
            if 'depth_chart_position' in update and update['depth_chart_position'] in ['Starter', 'Backup', 'Reserve']:
                player.depth_chart_position = update['depth_chart_position']
                
            if 'team' in update:
                player.team = update['team']
                
            player.updated_at = datetime.utcnow()
            success_count += 1
            
        except Exception as e:
            errors.append(f"Error updating player {update.get('player_id')}: {str(e)}")
    
    db.commit()
    
    return {
        "status": "success",
        "updated_count": success_count,
        "errors": errors
    }

@router.put("/rookies/{player_id}/draft", response_model=Dict[str, Any])
async def update_rookie_draft_status(
    player_id: str = Path(..., description="The rookie player ID"),
    team: str = Body(..., description="Team that drafted the player"),
    draft_position: int = Body(..., gt=0, le=262, description="Overall draft position"),
    round: Optional[int] = Body(None, gt=0, le=7, description="Draft round"),
    pick: Optional[int] = Body(None, gt=0, le=32, description="Pick within round"),
    auto_project: bool = Body(True, description="Automatically create projection after draft assignment"),
    db: Session = Depends(get_db)
):
    """
    Update a rookie's draft status and team assignment.
    """
    try:
        from backend.database.models import Player
        player = db.query(Player).filter(Player.player_id == player_id).first()
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")
        
        # Update player info
        player.team = team
        player.draft_position = draft_position
        if round:
            player.draft_round = round
        if pick:
            player.draft_pick = pick
        
        # Set status as Rookie (in case it wasn't already)
        player.status = "Rookie"
        
        # Check if they're active with a team
        if team != "FA":
            # Set depth chart position based on draft position
            if draft_position <= 100:  # High draft picks likely to be starters or key backups
                player.depth_chart_position = "Backup"
            else:
                player.depth_chart_position = "Reserve"
        
        db.commit()
        
        result = {
            "success": True,
            "player": {
                "player_id": player.player_id,
                "name": player.name,
                "team": player.team,
                "position": player.position,
                "draft_position": draft_position,
                "status": player.status,
                "depth_chart_position": player.depth_chart_position
            }
        }
        
        # Create projection if requested
        if auto_project and team != "FA":
            rookie_service = RookieProjectionService(db)
            projection = await rookie_service.create_draft_based_projection(
                player_id=player_id,
                draft_position=draft_position,
                season=2025  # Assuming 2025 season
            )
            
            if projection:
                result["projection_created"] = True
                result["projection_id"] = projection.projection_id
                result["fantasy_points"] = projection.half_ppr
            else:
                result["projection_created"] = False
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating rookie draft status: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error updating rookie: {str(e)}"
        )