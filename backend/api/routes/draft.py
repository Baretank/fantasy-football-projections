from fastapi import APIRouter, Depends, HTTPException, Query, Body, Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.database.models import DraftStatus
from backend.services.draft_service import DraftService
from backend.services.rookie_projection_service import RookieProjectionService

router = APIRouter()

class DraftStatusUpdate(BaseModel):
    """Schema for updating a player's draft status"""
    player_id: str
    draft_status: str = Field(..., pattern="^(available|drafted|watched)$") 
    fantasy_team: Optional[str] = None
    draft_order: Optional[int] = None
    create_projection: bool = False
    
    def dict_with_status(self):
        """Convert model to dict with draft_status renamed to status"""
        # Use model_dump which is the recommended replacement for dict() in Pydantic v2
        data = self.model_dump()
        data["status"] = data.pop("draft_status")
        return data

class BatchDraftStatusUpdate(BaseModel):
    """Schema for batch updating player draft statuses"""
    updates: List[DraftStatusUpdate]

class DraftBoardCreate(BaseModel):
    """Schema for creating a new draft board"""
    name: str
    description: Optional[str] = None
    season: Optional[int] = None
    settings: Optional[Dict[str, Any]] = None
    number_of_teams: int = 12
    roster_spots: int = 15

@router.get("/draft-board")
async def get_draft_board(
    status: Optional[str] = Query(None, pattern="^(available|drafted|watched)$"),
    position: Optional[str] = Query(None, pattern="^(QB|RB|WR|TE)$"),
    team: Optional[str] = None,
    order_by: str = Query("ranking", pattern="^(ranking|name|position|team|points)$"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Get the draft board with players and their statuses.
    
    Parameters:
    - status: Filter by draft status (available, drafted, watched)
    - position: Filter by player position
    - team: Filter by NFL team
    - order_by: Field to order results by
    - limit: Maximum number of results to return
    - offset: Number of results to skip
    
    Returns:
    - List of players with their draft status and related data
    """
    draft_service = DraftService(db)
    result = await draft_service.get_draft_board(
        status=status,
        position=position,
        team=team,
        order_by=order_by,
        limit=limit,
        offset=offset
    )
    return result

@router.post("/draft-status")
async def update_draft_status(
    update: DraftStatusUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a player's draft status.
    
    Parameters:
    - player_id: Player's unique identifier
    - draft_status: New status (available, drafted, watched)
    - fantasy_team: Fantasy team that drafted the player (for 'drafted' status)
    - draft_order: Order in which player was drafted (for 'drafted' status)
    - create_projection: Whether to create a projection for rookie players
    
    Returns:
    - Updated player information
    """
    draft_service = DraftService(db)
    update_dict = update.dict_with_status()
    result = await draft_service.update_draft_status(
        player_id=update_dict["player_id"],
        status=update_dict["status"],
        fantasy_team=update_dict["fantasy_team"],
        draft_order=update_dict["draft_order"],
        create_projection=update_dict["create_projection"]
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Player not found or update failed")
    
    return {
        "success": True,
        "player": {
            "player_id": result.player_id,
            "name": result.name,
            "position": result.position,
            "team": result.team,
            "draft_status": result.draft_status.value,
            "fantasy_team": result.fantasy_team,
            "draft_order": result.draft_order
        }
    }

@router.post("/batch-draft-status")
async def batch_update_draft_status(
    updates: BatchDraftStatusUpdate,
    db: Session = Depends(get_db)
):
    """
    Update draft status for multiple players in one operation.
    
    Parameters:
    - updates: List of player updates with player_id, status, and optional fields
    
    Returns:
    - Success status and count information
    """
    draft_service = DraftService(db)
    result = await draft_service.batch_update_draft_status(
        updates=[update.dict_with_status() for update in updates.updates]
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error_messages"])
    
    return result

@router.post("/reset-draft")
async def reset_draft(
    db: Session = Depends(get_db)
):
    """
    Reset all players to 'available' status.
    
    Returns:
    - Count of players reset
    """
    draft_service = DraftService(db)
    result = await draft_service.reset_draft()
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
    
    return result

@router.post("/undo-draft")
async def undo_last_draft_pick(
    db: Session = Depends(get_db)
):
    """
    Undo the last draft pick by setting the player with the highest draft order back to 'available'.
    
    Returns:
    - Information about the player whose draft status was reset
    """
    draft_service = DraftService(db)
    result = await draft_service.undo_last_draft_pick()
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "No drafted players found"))
    
    return result

@router.get("/draft-progress")
async def get_draft_progress(
    db: Session = Depends(get_db)
):
    """
    Get overall draft progress statistics.
    
    Returns:
    - Dict with draft progress metrics
    """
    draft_service = DraftService(db)
    result = await draft_service.get_draft_progress()
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result

@router.post("/draft-boards")
async def create_draft_board(
    board: DraftBoardCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new draft board.
    
    Parameters:
    - name: The name of the draft board
    - description: Optional description
    - season: The season for the draft (defaults to current year)
    - settings: Optional configuration settings
    - number_of_teams: Number of teams in the draft
    - roster_spots: Number of roster spots per team
    
    Returns:
    - Created draft board information
    """
    draft_service = DraftService(db)
    result = await draft_service.create_draft_board(
        name=board.name,
        description=board.description,
        season=board.season,
        settings=board.settings
    )
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create draft board")
    
    return {
        "draft_board_id": result.draft_board_id,
        "name": result.name,
        "description": result.description,
        "season": result.season,
        "created_at": result.created_at.isoformat()
    }

@router.get("/draft-boards")
async def get_draft_boards(
    active_only: bool = Query(True),
    db: Session = Depends(get_db)
):
    """
    Get all draft boards with optional filtering.
    
    Parameters:
    - active_only: If True, only return active draft boards
    
    Returns:
    - List of draft boards
    """
    draft_service = DraftService(db)
    result = await draft_service.get_draft_boards(active_only=active_only)
    
    return {
        "draft_boards": result
    }

@router.get("/rookie-projection-template/{position}")
async def get_rookie_projection_template(
    position: str = Path(..., pattern="^(QB|RB|WR|TE)$"),
    draft_round: Optional[int] = Query(None, ge=1, le=7),
    db: Session = Depends(get_db)
):
    """
    Get rookie projection templates for a specific position.
    
    Parameters:
    - position: Player position (QB, RB, WR, TE)
    - draft_round: Optional filter by draft round
    
    Returns:
    - List of rookie projection templates
    """
    rookie_service = RookieProjectionService(db)
    templates = await rookie_service.get_projection_templates(position, draft_round)
    
    return {
        "templates": templates
    }