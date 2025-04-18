"""
Centralized type definitions for the fantasy football projections backend.
This module defines common types used across multiple services to ensure consistency
and improve type safety.
"""

from typing import Dict, List, Union, TypedDict, Optional, Any
from datetime import datetime


# Player-related types
class PlayerDict(TypedDict, total=False):
    player_id: str
    name: str
    team: str
    position: str
    status: Optional[str]
    draft_position: Optional[int]
    height: Optional[int]
    weight: Optional[float]


# Statistics types
class StatsDict(TypedDict, total=False):
    """Common statistics dictionary used in projection calculations"""

    pass_attempts: float
    completions: float
    pass_yards: float
    pass_td: float
    interceptions: float
    rush_attempts: float
    rush_yards: float
    rush_td: float
    targets: float
    receptions: float
    rec_yards: float
    rec_td: float
    half_ppr: float
    games: float
    snap_share: float
    target_share: float
    rush_share: float


# Adjustment types
class AdjustmentDict(TypedDict, total=False):
    """Dictionary of adjustment factors for projections"""

    pass_volume: float
    rush_volume: float
    td_rate: float
    int_rate: float
    target_share: float
    rush_share: float
    snap_share: float
    scoring_rate: float
    pass_efficiency: float
    rush_efficiency: float


# Team statistics types
class TeamStatsDict(TypedDict, total=False):
    """Dictionary of team-level statistics"""

    team: str
    season: int
    pass_attempts: float
    pass_yards: float
    pass_td: float
    rush_attempts: float
    rush_yards: float
    rush_td: float
    targets: float
    receptions: float
    rec_yards: float
    rec_td: float
    plays: float
    pass_percentage: float
    pass_td_rate: float
    rush_yards_per_carry: float
    rank: float


# Usage breakdown types
class PlayerUsageDict(TypedDict, total=False):
    """Dictionary for individual player usage data"""

    name: str
    value: float
    share: float


class UsageMetricDict(TypedDict, total=False):
    """Dictionary for usage metrics by position group"""

    team_total: float
    players: Dict[str, PlayerUsageDict]


class UsageDict(TypedDict, total=False):
    """Dictionary for team usage breakdown"""

    passing: UsageMetricDict
    rushing: UsageMetricDict
    targets: UsageMetricDict


# Position-specific usage types
class MetricDataDict(TypedDict, total=False):
    """Dictionary for position-specific usage metrics"""

    pass_attempts: Dict[str, PlayerUsageDict]
    rush_attempts: Dict[str, PlayerUsageDict]
    targets: Dict[str, PlayerUsageDict]


class PositionUsageDict(TypedDict, total=False):
    """Dictionary for usage data by position"""

    QB: MetricDataDict
    RB: MetricDataDict
    WR: MetricDataDict
    TE: MetricDataDict


# Trend analysis types
class TrendItem(TypedDict):
    """Dictionary for historical trend data points"""

    season: int
    week: int
    value: float


# Variance-specific type definitions
class VarianceCoefficientDict(TypedDict, total=False):
    """Dictionary of variance coefficients by stat"""

    pass_attempts: float
    completions: float
    pass_yards: float
    pass_td: float
    interceptions: float
    rush_attempts: float
    rush_yards: float
    rush_td: float
    targets: float
    receptions: float
    rec_yards: float
    rec_td: float


class ConfidenceIntervalDict(TypedDict):
    """Dictionary for confidence interval bounds"""

    lower: float
    upper: float


class IntervalsByConfidenceDict(TypedDict, total=False):
    """Dictionary of confidence intervals by confidence level"""

    # Keys are confidence levels as strings (e.g., "0.50", "0.80", "0.95")
    # Values are ConfidenceIntervalDict objects
    pass


class StatVarianceDict(TypedDict):
    """Dictionary for variance metrics of a single stat"""

    mean: float
    std_dev: float
    coef_var: float
    intervals: IntervalsByConfidenceDict


class ProjectionRangeDict(TypedDict, total=False):
    """Dictionary for projection range results"""

    base: Dict[str, Any]
    low: Dict[str, float]
    median: Dict[str, float]
    high: Dict[str, float]
    scenario_ids: Dict[str, str]


# Override-specific type definitions
class OverrideMethodDict(TypedDict):
    """Dictionary for batch override method"""

    method: str  # 'percentage' or 'increment'
    amount: float


class OverrideResultDict(TypedDict):
    """Dictionary for override operation result"""

    success: bool
    message: Optional[str]
    override_id: Optional[str]
    old_value: Optional[float]
    new_value: Optional[float]


class BatchOverrideResultDict(TypedDict):
    """Dictionary for batch override results"""

    results: Dict[str, OverrideResultDict]


# Draft-specific type definitions
class PlayerDraftDataDict(TypedDict, total=False):
    """Dictionary for player draft data"""

    player_id: str
    name: str
    team: str
    position: str
    draft_status: str
    fantasy_team: Optional[str]
    draft_order: Optional[int]
    is_rookie: bool
    points: Optional[float]
    games: Optional[int]


# Player data types
class PlayerDataDict(TypedDict, total=False):
    """Dictionary for player data updates"""

    name: Optional[str]
    team: Optional[str]
    position: Optional[str]
    status: Optional[str]
    height: Optional[int]
    weight: Optional[float]
    draft_pick: Optional[int]
    is_rookie: Optional[bool]


# Game statistics types
class GameStatsDict(TypedDict, total=False):
    """Dictionary for aggregated game statistics"""

    games: int
    total_points: float
    points_allowed: float


class PlayerSplitsDict(TypedDict, total=False):
    """Dictionary for player statistical splits"""

    home: GameStatsDict
    away: GameStatsDict
    wins: GameStatsDict
    losses: GameStatsDict


# Query service types
class PlayerProjectionDataDict(TypedDict, total=False):
    """Dictionary for player projection data in query results"""

    projection_id: str
    half_ppr: float
    season: int
    pass_yards: Optional[float]
    pass_td: Optional[float]
    interceptions: Optional[float]
    rush_yards: Optional[float]
    rush_td: Optional[float]
    rec_yards: Optional[float]
    rec_td: Optional[float]


class PlayerQueryResultDict(TypedDict, total=False):
    """Dictionary for player query results"""

    player_id: str
    name: str
    team: str
    position: str
    status: Optional[str]
    depth_chart_position: Optional[str]
    date_of_birth: Optional[str]
    height: Optional[int]
    weight: Optional[float]
    draft_position: Optional[int]
    draft_team: Optional[str]
    draft_round: Optional[int]
    draft_pick: Optional[int]
    created_at: Optional[str]
    updated_at: Optional[str]
    projection: Optional[PlayerProjectionDataDict]
    stats: Optional[Dict[str, Dict[str, float]]]


class QueryResultDict(TypedDict):
    """Dictionary for query results with pagination"""

    players: List[PlayerQueryResultDict]
    total: int
    counts: Optional[Dict[str, int]]


# Scenario service types
class ScenarioInfoDict(TypedDict):
    """Dictionary for scenario information"""

    id: str
    name: str


# Pandas DataFrame related types
class PandasRowDict(TypedDict, total=False):
    """Base dictionary type for pandas DataFrame rows"""

    pass


class PlayerScenarioDataDict(TypedDict, total=False):
    """Dictionary for player data in scenario comparison"""

    player_id: str
    name: str
    team: str
    position: str
    scenarios: Dict[str, Dict[str, Any]]


class ScenarioComparisonResultDict(TypedDict):
    """Dictionary for scenario comparison results"""

    scenarios: List[ScenarioInfoDict]
    players: List[PlayerScenarioDataDict]


class FillStatsDict(TypedDict, total=False):
    """Dictionary for fill player statistics"""

    pass_attempts: float
    pass_yards: float
    pass_td: float
    rush_attempts: float
    rush_yards: float
    rush_td: float
    targets: float
    receptions: float
    rec_yards: float
    rec_td: float


class DraftBoardDict(TypedDict):
    """Dictionary for draft board data"""

    players: List[PlayerDraftDataDict]
    total: int
    counts: Dict[str, int]


class DraftStatusUpdateDict(TypedDict, total=False):
    """Dictionary for draft status update request"""

    player_id: str
    status: str
    fantasy_team: Optional[str]
    draft_order: Optional[int]
    create_projection: bool


class DraftResultDict(TypedDict, total=False):
    """Dictionary for draft operation result"""

    success: bool
    success_count: Optional[int]
    error_count: Optional[int]
    error_messages: Optional[List[str]]
    error: Optional[str]
    reset_count: Optional[int]
    player: Optional[Dict[str, Any]]


# Import types
class PlayerImportResultDict(TypedDict):
    """Dictionary for player import results"""

    success_count: int
    error_messages: List[str]


class RookieImportResultDict(TypedDict):
    """Dictionary for rookie import results"""

    success_count: int
    error_messages: List[str]


class ImportMetricsDict(TypedDict):
    """Dictionary for import operation metrics"""

    requests_made: int
    errors: int
    players_processed: int
    game_stats_processed: int
    start_time: Optional[datetime]
    end_time: Optional[datetime]


class DataImportResultDict(TypedDict):
    """Dictionary for data import results"""

    duration_seconds: float
    metrics: ImportMetricsDict


# Type aliases for common complex types
PlayerDict_T = Dict[str, Union[str, int, float, None]]
StatsDict_T = Dict[str, float]
AdjustmentDict_T = Dict[str, float]
PlayerShare_T = Dict[str, Dict[str, float]]
ScenarioDict_T = Dict[str, Union[str, Dict[str, Any]]]
VarianceResultDict = Dict[str, StatVarianceDict]


# Safe type casting helpers
def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert a value to float, with a default if conversion fails"""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_dict_get(d: Union[Dict[str, Any], dict, None], key: str, default: Any = None) -> Any:
    """
    Safely get a value from a dictionary with a default.

    Works with both regular Dict and TypedDict objects.
    """
    if d is None:
        return default
    # TypedDict doesn't have .get() method, but can be accessed via subscript
    try:
        return d.get(key, default)  # For regular Dict
    except AttributeError:
        # For TypedDict objects
        try:
            value = d[key]  # type: ignore
            return value if value is not None else default
        except KeyError:
            return default


def safe_calculate(numerator: Any, denominator: Any, default: float = 0.0) -> float:
    """Safely perform division, handling None values and zero denominators"""
    try:
        num = safe_float(numerator)
        den = safe_float(denominator)
        if den == 0.0:
            return default
        return num / den
    except (ValueError, TypeError):
        return default
