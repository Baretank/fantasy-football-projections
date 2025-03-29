from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Union, Any
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
    
    # Basic stats
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
    
    # Enhanced stats
    gross_pass_yards: Optional[float] = None
    sacks: Optional[float] = None
    sack_yards: Optional[float] = None
    net_pass_yards: Optional[float] = None
    fumbles: Optional[float] = None
    net_rush_yards: Optional[float] = None
    
    # Efficiency metrics
    pass_td_rate: Optional[float] = None
    int_rate: Optional[float] = None
    sack_rate: Optional[float] = None
    comp_pct: Optional[float] = None
    yards_per_att: Optional[float] = None
    net_yards_per_att: Optional[float] = None
    fumble_rate: Optional[float] = None
    rush_td_rate: Optional[float] = None
    yards_per_carry: Optional[float] = None
    net_yards_per_carry: Optional[float] = None
    catch_pct: Optional[float] = None
    yards_per_target: Optional[float] = None
    rec_td_rate: Optional[float] = None
    
    # Usage metrics
    snap_share: Optional[float] = None
    target_share: Optional[float] = None
    rush_share: Optional[float] = None
    redzone_share: Optional[float] = None
    pass_att_pct: Optional[float] = None
    car_pct: Optional[float] = None
    tar_pct: Optional[float] = None
    
    # Override info
    has_overrides: bool = False
    is_fill_player: bool = False

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
    is_baseline: Optional[bool] = Field(False, description="Whether this is a baseline scenario")
    base_scenario_id: Optional[str] = Field(None, description="Parent scenario ID")

class ScenarioRequest(ScenarioBase):
    """Scenario creation request."""
    pass

class ScenarioResponse(ScenarioBase):
    """Scenario response model."""
    scenario_id: str = Field(..., description="Unique scenario identifier")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class StatOverrideBase(BaseModel):
    """Base stat override model."""
    stat_name: str = Field(..., description="Name of the stat being overridden")
    manual_value: float = Field(..., description="User-provided value")
    notes: Optional[str] = Field(None, description="Notes about the override")

class StatOverrideRequest(StatOverrideBase):
    """Stat override creation request."""
    player_id: str = Field(..., description="Player ID")
    projection_id: str = Field(..., description="Projection ID")

class StatOverrideResponse(StatOverrideBase):
    """Stat override response model."""
    override_id: str = Field(..., description="Unique override identifier")
    player_id: str = Field(..., description="Player ID")
    projection_id: str = Field(..., description="Projection ID")
    calculated_value: float = Field(..., description="Original calculated value")
    created_at: datetime

    class Config:
        from_attributes = True

class BatchOverrideRequest(BaseModel):
    """Batch override request for multiple players."""
    player_ids: List[str] = Field(..., description="List of player IDs to override")
    stat_name: str = Field(..., description="Name of the stat to override")
    value: Union[float, Dict[str, Any]] = Field(
        ..., 
        description="Value or adjustment method",
        example={"method": "percentage", "amount": 10}
    )
    notes: Optional[str] = Field(None, description="Notes about the overrides")

class BatchOverrideResult(BaseModel):
    """Individual result from a batch override operation."""
    player_id: str
    success: bool
    message: Optional[str] = None
    override_id: Optional[str] = None
    old_value: Optional[float] = None
    new_value: Optional[float] = None

class BatchOverrideResponse(BaseModel):
    """Batch override response."""
    results: Dict[str, BatchOverrideResult]

class ScenarioComparisonRequest(BaseModel):
    """Request to compare multiple scenarios."""
    scenario_ids: List[str] = Field(..., description="List of scenario IDs to compare")
    position: Optional[str] = Field(None, description="Optional position filter")

class ScenarioComparisonPlayer(BaseModel):
    """Player data in a scenario comparison."""
    player_id: str
    name: str
    team: str
    position: str
    scenarios: Dict[str, Dict[str, Any]]

class ScenarioComparisonResponse(BaseModel):
    """Scenario comparison response."""
    scenarios: List[Dict[str, str]]
    players: List[ScenarioComparisonPlayer]

class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str = Field(..., description="Error description")
    code: Optional[str] = Field(None, description="Error code")
    
class SuccessResponse(BaseModel):
    """Standard success response."""
    status: str = Field("success", description="Operation status")
    message: Optional[str] = Field(None, description="Success message")
    data: Optional[Dict] = Field(None, description="Response data")