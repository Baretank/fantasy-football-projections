from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Dict, List, Optional, Any
import logging
import uuid

logger = logging.getLogger(__name__)

from backend.database.database import get_db
from backend.database.models import Projection
from backend.services.projection_service import ProjectionService
from backend.services.rookie_projection_service import RookieProjectionService
from backend.services.projection_variance_service import ProjectionVarianceService
from backend.services.team_stat_service import TeamStatService
from backend.services.scenario_service import ScenarioService
from backend.api.schemas import (
    ProjectionResponse, 
    ProjectionCreateRequest,
    ProjectionAdjustRequest,
    ProjectionRangeResponse,
    RookieProjectionResponse,
    TeamStatsResponse
)

router = APIRouter(
    tags=["projections"]
)

@router.get("/{projection_id}", response_model=ProjectionResponse)
async def get_projection(
    projection_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific projection by ID."""
    service = ProjectionService(db)
    projection = await service.get_projection(projection_id)
    
    if not projection:
        raise HTTPException(status_code=404, detail="Projection not found")
        
    return projection

@router.get("/", response_model=List[ProjectionResponse])
async def get_projections(
    player_id: Optional[str] = None,
    team: Optional[str] = None,
    season: Optional[int] = None,
    scenario_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get projections with optional filters."""
    service = ProjectionService(db)
    projections = await service.get_player_projections(
        player_id=player_id,
        team=team,
        season=season,
        scenario_id=scenario_id
    )
    
    return projections

@router.post("/create", response_model=ProjectionResponse)
async def create_projection(
    request: ProjectionCreateRequest,
    db: Session = Depends(get_db)
):
    """Create a new baseline projection."""
    service = ProjectionService(db)
    projection = await service.create_base_projection(
        player_id=request.player_id,
        season=request.season,
        scenario_id=request.scenario_id
    )
    
    if not projection:
        raise HTTPException(
            status_code=400,
            detail="Failed to create projection"
        )
        
    return projection

@router.post("/{projection_id}/adjust", response_model=ProjectionResponse)  # Changed to POST for test compatibility
async def adjust_projection(
    projection_id: str,
    adjustments: ProjectionAdjustRequest,
    db: Session = Depends(get_db)
):
    """Update a projection with adjustments."""
    service = ProjectionService(db)
    projection = await service.update_projection(
        projection_id=projection_id,
        adjustments=adjustments.adjustments
    )
    
    if not projection:
        raise HTTPException(
            status_code=400,
            detail="Failed to adjust projection"
        )
        
    return projection

@router.get("/{projection_id}/range", response_model=ProjectionRangeResponse)
async def get_projection_range(
    projection_id: str,
    confidence: float = Query(0.80, ge=0.5, le=0.99),
    create_scenarios: bool = False,
    db: Session = Depends(get_db)
):
    """
    Generate projection ranges (low/median/high) with confidence intervals.
    
    - confidence: Confidence level (0.5-0.99)
    - create_scenarios: If true, create scenario projections for each range
    """
    service = ProjectionVarianceService(db)
    proj_range = await service.generate_projection_range(
        projection_id=projection_id,
        confidence=confidence,
        scenarios=create_scenarios
    )
    
    if not proj_range:
        raise HTTPException(
            status_code=400,
            detail="Failed to generate projection range"
        )
        
    return proj_range

@router.get("/{projection_id}/variance", response_model=Dict)
async def get_projection_variance(
    projection_id: str,
    use_historical: bool = True,
    db: Session = Depends(get_db)
):
    """
    Get variance statistics and confidence intervals for a projection.
    
    - use_historical: If true, use historical game-to-game variance
    """
    service = ProjectionVarianceService(db)
    variance_data = await service.calculate_variance(
        projection_id=projection_id,
        use_historical=use_historical
    )
    
    if not variance_data:
        raise HTTPException(
            status_code=400,
            detail="Failed to calculate variance"
        )
        
    return variance_data

@router.post("/rookies/create", response_model=Dict)
async def create_rookie_projections(
    season: int = Query(..., ge=2023),
    scenario_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Create projections for all rookies in the rookies.json file.
    
    - season: The season year to project
    - scenario_id: Optional scenario ID to associate with the projections
    """
    service = RookieProjectionService(db)
    success_count, errors = await service.create_rookie_projections(
        season=season,
        scenario_id=scenario_id
    )
    
    if success_count == 0:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to create rookie projections: {errors[0] if errors else 'Unknown error'}"
        )
        
    return {
        "success": True,
        "count": success_count,
        "errors": errors
    }

@router.put("/rookies/{player_id}/enhance", response_model=RookieProjectionResponse)
async def enhance_rookie_projection(
    player_id: str,
    comp_level: str = Query("medium", pattern="^(high|medium|low)$"),
    playing_time_pct: float = Query(0.5, ge=0.0, le=1.0),
    season: int = Query(..., ge=2023),
    db: Session = Depends(get_db)
):
    """
    Enhance a rookie projection with more sophisticated modeling.
    
    - player_id: The rookie player ID
    - comp_level: Comparison level (high, medium, low)
    - playing_time_pct: Expected playing time percentage (0.0-1.0)
    - season: The season year
    """
    service = RookieProjectionService(db)
    projection = await service.enhance_rookie_projection(
        player_id=player_id,
        comp_level=comp_level,
        playing_time_pct=playing_time_pct,
        season=season
    )
    
    if not projection:
        raise HTTPException(
            status_code=400,
            detail="Failed to enhance rookie projection"
        )
        
    return projection

@router.put("/team/{team}/adjust", response_model=List[ProjectionResponse])
async def adjust_team_projections(
    team: str,
    season: int = Query(..., ge=2023),
    scenario_id: Optional[str] = None,
    adjustments: Dict[str, float] = None,
    player_shares: Optional[Dict[str, Dict[str, float]]] = None,
    db: Session = Depends(get_db)
):
    """
    Apply team-level adjustments to all affected player projections.
    
    - team: The team code (e.g., 'LAR')
    - season: The season year
    - scenario_id: Optional scenario ID
    - adjustments: Adjustment factors for team-level metrics
      (e.g., {"pass_volume": 1.1, "rush_volume": 0.9})
    - player_shares: Optional player-specific distribution changes
      (e.g., {"player_id": {"targets": 0.25}})
    """
    try:
        service = TeamStatService(db)
        
        if not adjustments and not player_shares:
            raise HTTPException(
                status_code=400,
                detail="Must provide either adjustments or player_shares"
            )
            
        logger.info(f"Adjusting team projections for {team}, season {season}, scenario_id {scenario_id}")
        logger.info(f"Adjustments: {adjustments}")
        logger.info(f"Player shares: {player_shares}")
        
        # Clone projections from base scenario to new scenario if needed
        if scenario_id:
            # Check if we have projections for this scenario_id
            projections_exist = db.query(Projection).filter(
                and_(
                    Projection.scenario_id == scenario_id,
                    Projection.season == season
                )
            ).count() > 0
            
            if not projections_exist:
                # We need to clone some projections from the base scenario
                scenario_service = ScenarioService(db)
                base_scenario = await scenario_service.get_scenario(scenario_id)
                
                if base_scenario and base_scenario.base_scenario_id:
                    # Clone projections from base scenario
                    source_projections = db.query(Projection).filter(
                        and_(
                            Projection.scenario_id == base_scenario.base_scenario_id,
                            Projection.season == season
                        )
                    ).all()
                    
                    # Clone each projection
                    for source_proj in source_projections:
                        if not db.query(Projection).filter(
                            and_(
                                Projection.player_id == source_proj.player_id,
                                Projection.scenario_id == scenario_id,
                                Projection.season == season
                            )
                        ).first():
                            # Create a new projection based on the source
                            new_proj = Projection(
                                projection_id=str(uuid.uuid4()),
                                player_id=source_proj.player_id,
                                scenario_id=scenario_id,
                                season=season,
                                games=source_proj.games,
                                half_ppr=source_proj.half_ppr,
                                
                                # Copy all stats
                                pass_attempts=source_proj.pass_attempts,
                                completions=source_proj.completions,
                                pass_yards=source_proj.pass_yards,
                                pass_td=source_proj.pass_td,
                                interceptions=source_proj.interceptions,
                                rush_attempts=source_proj.rush_attempts,
                                rush_yards=source_proj.rush_yards,
                                rush_td=source_proj.rush_td,
                                targets=source_proj.targets,
                                receptions=source_proj.receptions,
                                rec_yards=source_proj.rec_yards,
                                rec_td=source_proj.rec_td,
                                
                                # Usage metrics
                                snap_share=source_proj.snap_share,
                                target_share=source_proj.target_share,
                                rush_share=source_proj.rush_share
                            )
                            db.add(new_proj)
                            
                    db.commit()
        
        updated_projections = await service.apply_team_adjustments(
            team=team,
            season=season,
            adjustments=adjustments or {},
            player_shares=player_shares,
            scenario_id=scenario_id
        )
        
        if not updated_projections:
            raise HTTPException(
                status_code=400,
                detail="Failed to apply team adjustments"
            )
            
        return updated_projections
    except Exception as e:
        logger.error(f"Error in adjust_team_projections: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error applying team adjustments: {str(e)}"
        )

@router.get("/team/{team}/usage", response_model=Dict)
async def get_team_usage_breakdown(
    team: str,
    season: int = Query(..., ge=2023),
    db: Session = Depends(get_db)
):
    """
    Get a breakdown of team usage by position group and player.
    
    - team: The team code (e.g., 'LAR')
    - season: The season year
    """
    service = TeamStatService(db)
    usage_data = await service.get_team_usage_breakdown(
        team=team,
        season=season
    )
    
    if not usage_data:
        raise HTTPException(
            status_code=400,
            detail="Failed to retrieve team usage breakdown"
        )
        
    return usage_data

@router.get("/team/{team}/stats", response_model=TeamStatsResponse)
async def get_team_stats(
    team: str,
    season: int = Query(..., ge=2023),
    db: Session = Depends(get_db)
):
    """
    Get team-level offensive statistics.
    
    - team: The team code (e.g., 'LAR')
    - season: The season year
    """
    service = TeamStatService(db)
    stats = await service.get_team_stats(
        team=team,
        season=season
    )
    
    if not stats or len(stats) == 0:
        raise HTTPException(
            status_code=404,
            detail="Team stats not found"
        )
        
    return stats[0]
    
@router.post("/rookies/draft-based", response_model=ProjectionResponse)
async def create_draft_based_rookie_projection(
    player_id: str = Query(..., description="Rookie player ID"),
    draft_position: int = Query(..., gt=0, le=262, description="Overall draft position"),
    season: int = Query(..., ge=2025, description="Projection season"),
    scenario_id: Optional[str] = Query(None, description="Optional scenario ID"),
    db: Session = Depends(get_db)
):
    """
    Create a rookie projection based on draft position.
    """
    service = RookieProjectionService(db)
    projection = await service.create_draft_based_projection(
        player_id=player_id,
        draft_position=draft_position,
        season=season,
        scenario_id=scenario_id
    )
    
    if not projection:
        raise HTTPException(
            status_code=400,
            detail="Failed to create rookie projection"
        )
        
    return projection