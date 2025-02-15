from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime

class PlayerBase(BaseModel):
    """Base player information model."""
    name: str = Field(..., description="Player's full name")
    team: str = Field(..., description="Current team abbreviation")
    position: str = Field(..., description="Player position (QB, RB, WR, TE)")

class PlayerResponse(PlayerBase):
    """Player response model with additional metadata."""
    player_id: str = Field(..., description="Unique player identifier")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True

class PlayerStatBase(BaseModel):
    """Base statistics model."""
    season: int = Field(..., description="NFL season year")
    week: Optional[int] = Field(None, description="Week number (null for season totals)")
    stat_type: str = Field(..., description="Type of statistic (e.g., passing_yards, rush_attempts)")
    value: float = Field(..., description="Statistical value")

class PlayerStats(BaseModel):
    """Detailed player statistics response."""
    player_id: str
    name: str
    team: str
    position: str
    stats: Dict[int, Dict[str, Dict[int, Dict[str, float]]]] = Field(
        ..., 
        description="Nested statistics by season, week, and stat type"
    )

class ProjectionBase(BaseModel):
    """Base projection model."""
    season: int = Field(..., description="Season year for projection")
    games: int = Field(..., description="Projected number of games")
    half_ppr: float = Field(..., description="Projected half-PPR fantasy points")

class ProjectionResponse(ProjectionBase):
    """Detailed projection response."""
    projection_id: str = Field(..., description="Unique projection identifier")
    player_id: str = Field(..., description="Associated player ID")
    scenario_id: Optional[str] = Field(None, description="Associated scenario ID")
    
    # Position-specific stats
    pass_attempts: Optional[float] = None
    completions: Optional[float] = None
    pass_yards: Optional[float] = None
    pass_td: Optional[float] = None
    interceptions: Optional[float] = None
    carries: Optional[float] = None
    rush_yards: Optional[float] = None
    rush_td: Optional[float] = None
    targets: Optional[float] = None
    receptions: Optional[float] = None
    rec_yards: Optional[float] = None
    rec_td: Optional[float] = None
    
    # Usage metrics
    snap_share: Optional[float] = None
    target_share: Optional[float] = None
    rush_share: Optional[float] = None
    redzone_share: Optional[float] = None

    class Config:
        from_attributes = True

class AdjustmentRequest(BaseModel):
    """Projection adjustment request."""
    adjustments: Dict[str, float] = Field(
        ..., 
        description="Adjustment factors for various metrics",
        example={
            "snap_share": 1.1,
            "target_share": 0.95,
            "td_rate": 1.05
        }
    )

class ScenarioBase(BaseModel):
    """Base scenario model."""
    name: str = Field(..., description="Scenario name")
    description: Optional[str] = Field(None, description="Scenario description")
    base_scenario_id: Optional[str] = Field(None, description="Parent scenario ID")

class ScenarioResponse(ScenarioBase):
    """Scenario response model."""
    scenario_id: str = Field(..., description="Unique scenario identifier")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str = Field(..., description="Error description")
    code: Optional[str] = Field(None, description="Error code")
    
class SuccessResponse(BaseModel):
    """Standard success response."""
    status: str = Field("success", description="Operation status")
    message: Optional[str] = Field(None, description="Success message")
    data: Optional[Dict] = Field(None, description="Response data")