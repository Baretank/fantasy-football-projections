from pydantic import BaseModel, Field, validator, ConfigDict
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, date


class PlayerBase(BaseModel):
    """Base player information model."""

    name: str = Field(..., description="Player's full name")
    team: str = Field(..., description="Current team abbreviation")
    position: str = Field(..., description="Player position (QB, RB, WR, TE)")


class PlayerResponse(PlayerBase):
    """Player response model with additional metadata."""

    player_id: str = Field(..., description="Unique player identifier")

    # Enhanced player details
    date_of_birth: Optional[date] = Field(None, description="Player date of birth (YYYY-MM-DD)")
    height: Optional[int] = Field(None, description="Player height in inches")
    weight: Optional[int] = Field(None, description="Player weight in pounds")
    status: Optional[str] = Field("Active", description="Player status (Active, Injured, Rookie)")
    depth_chart_position: Optional[str] = Field(
        "Backup", description="Depth chart position (Starter, Backup, Reserve)"
    )

    # Draft information
    draft_position: Optional[int] = Field(None, description="Overall draft position")
    draft_team: Optional[str] = Field(None, description="Team that drafted player")
    draft_round: Optional[int] = Field(None, description="Draft round")
    draft_pick: Optional[int] = Field(None, description="Pick within round")

    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class PlayerStatBase(BaseModel):
    """Base statistics model."""

    season: int = Field(..., description="NFL season year")
    week: Optional[int] = Field(None, description="Week number (null for season totals)")
    stat_type: str = Field(
        ..., description="Type of statistic (e.g., passing_yards, rush_attempts)"
    )
    value: float = Field(..., description="Statistical value")


class PlayerStats(BaseModel):
    """Detailed player statistics response."""

    player_id: str
    name: str
    team: str
    position: str
    stats: Dict[int, Dict[str, Dict[int, Dict[str, float]]]] = Field(
        ..., description="Nested statistics by season, week, and stat type"
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
    rush_attempts: Optional[float] = None
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

    model_config = ConfigDict(from_attributes=True)


class AdjustmentRequest(BaseModel):
    """Projection adjustment request."""

    adjustments: Dict[str, float] = Field(
        ...,
        description="Adjustment factors for various metrics",
        json_schema_extra={"example": {"snap_share": 1.1, "target_share": 0.95, "td_rate": 1.05}},
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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


class BatchOverrideRequest(BaseModel):
    """Batch override request for multiple players."""

    player_ids: List[str] = Field(..., description="List of player IDs to override")
    stat_name: str = Field(..., description="Name of the stat to override")
    value: Union[float, Dict[str, Any]] = Field(
        ...,
        description="Value or adjustment method",
        example={"method": "percentage", "amount": 10},
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


class ProjectionCreateRequest(BaseModel):
    """Request to create a new projection."""

    player_id: str = Field(..., description="Player ID")
    season: int = Field(..., description="Season year")
    scenario_id: Optional[str] = Field(None, description="Optional scenario ID")


class ProjectionAdjustRequest(BaseModel):
    """Request to adjust a projection."""

    adjustments: Dict[str, float] = Field(
        ..., description="Adjustment factors for projection metrics"
    )


class ProjectionRangeResponse(BaseModel):
    """Response for projection range endpoints."""

    base: Dict[str, Any] = Field(..., description="Base projection values")
    low: Dict[str, Any] = Field(..., description="Low-end projection values")
    median: Dict[str, Any] = Field(..., description="Median projection values")
    high: Dict[str, Any] = Field(..., description="High-end projection values")
    scenario_ids: Optional[Dict[str, str]] = Field(None, description="IDs of created scenarios")


class RookieProjectionResponse(ProjectionResponse):
    """Response for rookie projection endpoints."""

    comp_level: Optional[str] = Field(None, description="Comparison level used")
    playing_time_pct: Optional[float] = Field(None, description="Playing time percentage")


class TeamStatsResponse(BaseModel):
    """Team statistics response."""

    team_stat_id: str = Field(..., description="Unique identifier")
    team: str = Field(..., description="Team abbreviation")
    season: int = Field(..., description="Season year")

    # Core offensive metrics
    plays: float = Field(..., description="Total offensive plays")
    pass_percentage: float = Field(..., description="Percentage of pass plays")
    pass_attempts: float = Field(..., description="Season pass attempts")
    pass_yards: float = Field(..., description="Season pass yards")
    pass_td: float = Field(..., description="Season pass TDs")
    pass_td_rate: float = Field(..., description="TD rate on pass attempts")
    rush_attempts: float = Field(..., description="Season rush attempts")
    rush_yards: float = Field(..., description="Season rush yards")
    rush_td: float = Field(..., description="Season rush TDs")
    rush_yards_per_carry: float = Field(..., description="Yards per carry")
    targets: float = Field(..., description="Total targets")
    receptions: float = Field(..., description="Total receptions")
    rec_yards: float = Field(..., description="Total receiving yards")
    rec_td: float = Field(..., description="Total receiving TDs")
    rank: int = Field(..., description="Offensive ranking")

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConfidenceIntervalResponse(BaseModel):
    """Response for variance and confidence interval endpoints."""

    mean: float = Field(..., description="Mean projected value")
    std_dev: float = Field(..., description="Standard deviation")
    coef_var: float = Field(..., description="Coefficient of variation")
    intervals: Dict[str, Dict[str, float]] = Field(
        ..., description="Confidence intervals at different levels"
    )


class BatchProjectionCreateRequest(BaseModel):
    """Request to create projections for multiple players."""

    player_ids: List[str] = Field(..., description="List of player IDs")
    season: int = Field(..., description="Season year")
    scenario_id: Optional[str] = Field(None, description="Optional scenario ID")


class BatchProjectionAdjustRequest(BaseModel):
    """Request to adjust multiple projections."""

    adjustments: Dict[str, Dict[str, float]] = Field(
        ...,
        description="Map of projection IDs to adjustment values",
        json_schema_extra={
            "example": {
                "projection_id1": {"target_share": 1.1, "td_rate": 0.9},
                "projection_id2": {"snap_share": 0.8},
            }
        },
    )


class ScenarioTemplate(BaseModel):
    """Template for creating a scenario."""

    name: str = Field(..., description="Scenario name")
    description: Optional[str] = Field(None, description="Scenario description")
    base_scenario_id: Optional[str] = Field(None, description="Base scenario ID to clone from")
    adjustments: Optional[Dict[str, float]] = Field(None, description="Global adjustments")
    player_adjustments: Optional[Dict[str, Dict[str, float]]] = Field(
        None,
        description="Player-specific adjustments",
        json_schema_extra={
            "example": {"player_id1": {"target_share": 1.2}, "player_id2": {"rush_share": 0.9}}
        },
    )


class BatchScenarioCreateRequest(BaseModel):
    """Request to create multiple scenarios."""

    scenarios: List[ScenarioTemplate] = Field(..., description="List of scenario templates")


class ExportFiltersRequest(BaseModel):
    """Filters for exporting projections."""

    filters: Optional[Dict[str, Any]] = Field(
        None,
        description="Export filters",
        json_schema_extra={"example": {"team": "SF", "position": ["QB", "RB"], "season": 2024}},
    )


class BatchResponse(BaseModel):
    """Standard response for batch operations."""

    success: int = Field(..., description="Number of successful operations")
    failure: int = Field(..., description="Number of failed operations")
    failed_players: Optional[List[Dict[str, Any]]] = Field(
        None, description="Details of failed operations"
    )
    failed_projections: Optional[List[Dict[str, Any]]] = Field(
        None, description="Details of failed projection operations"
    )
    failed_scenarios: Optional[List[Dict[str, Any]]] = Field(
        None, description="Details of failed scenario operations"
    )
    projection_ids: Optional[Dict[str, str]] = Field(
        None, description="Map of player IDs to created projection IDs"
    )
    scenario_ids: Optional[Dict[str, str]] = Field(
        None, description="Map of scenario names to created scenario IDs"
    )
    error: Optional[str] = Field(None, description="Error message if all operations failed")


class PaginationInfo(BaseModel):
    """Pagination information."""

    page: int
    page_size: int
    total_count: int
    total_pages: int
    has_next: bool
    has_prev: bool


class OptimizedPlayerResponse(BaseModel):
    """Optimized player response with flexible stats structure."""

    player_id: str
    name: str
    team: str
    position: str
    stats: Optional[Dict[str, Any]] = None
    projection: Optional[Dict[str, Any]] = None


class PlayerListResponse(BaseModel):
    """Response for player listing endpoint."""

    players: List[Dict[str, Any]]
    pagination: PaginationInfo


class PlayerSearchResponse(BaseModel):
    """Response for player search endpoint."""

    query: str
    count: int
    players: List[Dict[str, Any]]


class RookieProjectionTemplateResponse(BaseModel):
    """Rookie projection template model."""

    template_id: str = Field(..., description="Unique template identifier")
    position: str = Field(..., description="Player position (QB, RB, WR, TE)")
    draft_round: int = Field(..., description="Draft round (1-7)")
    draft_pick_min: int = Field(..., description="Minimum draft pick")
    draft_pick_max: int = Field(..., description="Maximum draft pick")
    games: float = Field(..., description="Projected games")
    snap_share: float = Field(..., description="Projected snap share")

    # Position-specific metrics
    pass_attempts: Optional[float] = Field(None, description="Pass attempts")
    comp_pct: Optional[float] = Field(None, description="Completion percentage")
    yards_per_att: Optional[float] = Field(None, description="Yards per attempt")
    pass_td_rate: Optional[float] = Field(None, description="Pass TD rate")
    int_rate: Optional[float] = Field(None, description="Interception rate")
    rush_att_per_game: Optional[float] = Field(None, description="Rush attempts per game")
    rush_yards_per_att: Optional[float] = Field(None, description="Yards per rush attempt")
    rush_td_per_game: Optional[float] = Field(None, description="Rush TDs per game")
    targets_per_game: Optional[float] = Field(None, description="Targets per game")
    catch_rate: Optional[float] = Field(None, description="Catch rate")
    rec_yards_per_catch: Optional[float] = Field(None, description="Receiving yards per catch")
    rec_td_per_catch: Optional[float] = Field(None, description="Receiving TDs per catch")
    rush_td_per_att: Optional[float] = Field(None, description="Rush TDs per attempt")

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RookieProjectionTemplateRequest(BaseModel):
    """Request to create or update a rookie projection template."""

    position: str = Field(..., description="Player position (QB, RB, WR, TE)")
    draft_round: int = Field(..., description="Draft round (1-7)")
    draft_pick_min: int = Field(..., description="Minimum draft pick")
    draft_pick_max: int = Field(..., description="Maximum draft pick")
    games: float = Field(..., description="Projected games")
    snap_share: float = Field(..., description="Projected snap share")

    # Position-specific metrics (only relevant ones are required)
    pass_attempts: Optional[float] = None
    comp_pct: Optional[float] = None
    yards_per_att: Optional[float] = None
    pass_td_rate: Optional[float] = None
    int_rate: Optional[float] = None
    rush_att_per_game: Optional[float] = None
    rush_yards_per_att: Optional[float] = None
    rush_td_per_game: Optional[float] = None
    targets_per_game: Optional[float] = None
    catch_rate: Optional[float] = None
    rec_yards_per_catch: Optional[float] = None
    rec_td_per_catch: Optional[float] = None
    rush_td_per_att: Optional[float] = None
