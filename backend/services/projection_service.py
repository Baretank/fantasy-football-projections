from typing import Dict, List, Optional, Any, Union, TypedDict, cast
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
import uuid
import logging
import pandas as pd

from backend.database.models import Player, BaseStat, Projection, TeamStat, Scenario
from backend.services.active_player_service import ActivePlayerService
from backend.services.typing import safe_float

logger = logging.getLogger(__name__)

# Type definitions for complex structures
class StatsDict(TypedDict, total=False):
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

class AdjustmentDict(TypedDict, total=False):
    pass_volume: float
    rush_volume: float
    td_rate: float
    int_rate: float
    target_share: float
    rush_share: float
    snap_share: float
    scoring_rate: float


class ProjectionError(Exception):
    """Base exception for projection-related errors."""

    pass


class ProjectionService:
    def __init__(self, db: Session, active_player_service=None):
        self.db = db
        self.active_player_service = active_player_service or ActivePlayerService()
        self.adjustment_ranges = {
            "snap_share": (0.1, 1.0),
            "target_share": (0.0, 0.5),
            "rush_share": (0.0, 0.5),
            "td_rate": (0.5, 2.0),
            "pass_volume": (0.7, 1.3),
            "rush_volume": (0.7, 1.3),
            "scoring_rate": (0.5, 1.5),
            "int_rate": (0.5, 1.5),
        }
        
    def filter_active_players(self, players: List[Player], season: Optional[int] = None) -> List[Player]:
        """
        Filter a list of Player objects to include only active players.
        
        Args:
            players: List of Player objects
            season: Optional season year for season-specific filtering
                   (2025 = current season, stricter filtering)
                   (2024 and earlier = historical seasons, more lenient filtering)
            
        Returns:
            List of active Player objects
        """
        if not players:
            return players
            
        try:
            # Convert players to DataFrame for filtering
            player_df = pd.DataFrame([
                {
                    "display_name": p.name,
                    "team_abbr": p.team,
                    "position": p.position,
                    "player_id": p.player_id,
                    "status": p.status,
                    "fantasy_points": getattr(p, "fantasy_points", 0)  # For historical filtering
                } 
                for p in players
            ])
            
            # Filter active players with season awareness
            if not player_df.empty:
                filtered_df = self.active_player_service.filter_active(
                    player_df, 
                    season=season
                )
                
                # Log filtering results
                filtered_count = len(filtered_df) if not filtered_df.empty else 0
                original_count = len(player_df)
                logger.info(
                    f"Active player filtering (season: {season}): {filtered_count}/{original_count} "
                    f"players retained ({original_count - filtered_count} filtered out)"
                )
                
                # Return only active players
                if not filtered_df.empty:
                    active_ids = set(filtered_df["player_id"].tolist())
                    return [p for p in players if p.player_id in active_ids]
                else:
                    return []
        except Exception as e:
            # Log error but continue with unfiltered players
            logger.error(f"Error filtering active players: {str(e)}")
            
        return players
        
        # Regression weights for different metrics
        # These determine how much we weight historical vs current season data
        self.regression_weights = {
            # QB metrics
            "pass_attempts": 0.65,  # 65% current, 35% historical
            "completions": 0.65,
            "pass_yards": 0.65,
            "pass_td": 0.6,  # TDs have higher variance, so more regression
            "interceptions": 0.5,  # INTs have high variance, so 50/50 split
            "comp_pct": 0.7,  # Completion % is fairly stable
            "yards_per_att": 0.65,
            
            # RB metrics
            "rush_attempts": 0.7,
            "rush_yards": 0.65,
            "rush_td": 0.6,
            "yards_per_carry": 0.6,  # YPC has variance year to year
            
            # Receiving metrics (RB/WR/TE)
            "targets": 0.7,
            "receptions": 0.7,
            "rec_yards": 0.65,
            "rec_td": 0.55,  # Receiving TDs have high variance
            "catch_pct": 0.7,
            "yards_per_target": 0.65,
            
            # Usage metrics (defaults)
            "snap_share": 0.75,
            "target_share": 0.7,
            "rush_share": 0.7,
        }
        
    def _safe_calculate_share_factor(self, new_share: float, current_share: Any) -> float:
        """Safely calculate a relative share factor between new and current share values.
        
        Args:
            new_share: The new share value to set
            current_share: The current share value (may be None or non-numeric)
            
        Returns:
            float: The multiplication factor to apply to stats
        """
        try:
            # Convert current_share to float, defaulting to 0.0 if None or invalid
            current_float = 0.0
            if current_share is not None:
                try:
                    current_float = float(current_share)
                except (ValueError, TypeError):
                    current_float = 0.0
            
            # Calculate relative factor (safely handle division by zero)
            if current_float > 0.0:
                return new_share / current_float
            else:
                return new_share
        except Exception as e:
            logger.error(f"Error calculating share factor: {str(e)}")
            # Return a safe default if anything goes wrong
            return new_share
            
    async def apply_statistical_regression(
        self, player_id: str, season: int, scenario_id: Optional[str] = None
    ) -> Optional[Projection]:
        """
        Apply statistical regression to smooth projections using historical data.
        
        This method implements a weighted average between a player's current projection
        and their historical averages, creating more stable and reliable projections.
        
        Args:
            player_id: The player ID to apply regression to
            season: Current season
            scenario_id: Optional scenario ID to filter projections
            
        Returns:
            Updated projection with regression applied, or None if failed
        """
        try:
            # Get the player
            player = self.db.get(Player, player_id)
            if not player:
                logger.error(f"Player {player_id} not found")
                return None
                
            # Get the player's current projection
            query = self.db.query(Projection).filter(
                and_(
                    Projection.player_id == player_id,
                    Projection.season == season
                )
            )
            
            if scenario_id:
                query = query.filter(Projection.scenario_id == scenario_id)
            else:
                # If no scenario, get the base projection
                query = query.filter(Projection.scenario_id.is_(None))
                
            current_projection = query.first()
            if not current_projection:
                logger.error(f"No projection found for player {player_id} in season {season}")
                return None
                
            # Get historical stats (from previous season)
            previous_season = season - 1
            historical_stats = (
                self.db.query(BaseStat)
                .filter(
                    and_(
                        BaseStat.player_id == player_id,
                        BaseStat.season == previous_season,
                        BaseStat.week.is_(None)  # Season totals
                    )
                )
                .all()
            )
            
            # If no historical stats, no regression can be applied
            if not historical_stats:
                logger.info(f"No historical stats found for player {player_id}, skipping regression")
                return current_projection
                
            # Convert historical stats to a more usable format
            hist_stats_dict = {}
            for stat in historical_stats:
                if stat.stat_type and stat.value is not None:
                    hist_stats_dict[stat.stat_type] = float(stat.value)
            
            # Create a map from BaseStat stat_type to Projection field names
            # This is needed because the field names might not match exactly
            stat_mapping = {
                "pass_attempts": "pass_attempts",
                "completions": "completions",
                "pass_yards": "pass_yards",
                "pass_td": "pass_td",
                "interceptions": "interceptions",
                "rush_attempts": "rush_attempts",
                "rush_yards": "rush_yards", 
                "rush_td": "rush_td",
                "targets": "targets",
                "receptions": "receptions",
                "rec_yards": "rec_yards",
                "rec_td": "rec_td",
                # Efficiency metrics can be recalculated later
            }
            
            # Apply regression to each stat
            for hist_stat, proj_field in stat_mapping.items():
                # Only process if we have historical data for this stat
                if hist_stat in hist_stats_dict:
                    hist_value = hist_stats_dict[hist_stat]
                    curr_value = getattr(current_projection, proj_field)
                    
                    # Skip if current value is None
                    if curr_value is None:
                        continue
                        
                    # Get the regression weight for this stat
                    weight = self.regression_weights.get(proj_field, 0.65)  # Default to 0.65 if not specified
                    
                    # Apply weighted average: weight * current + (1 - weight) * historical
                    regressed_value = (weight * float(curr_value)) + ((1 - weight) * hist_value)
                    
                    # Update the projection with the regressed value
                    setattr(current_projection, proj_field, regressed_value)
            
            # Recalculate efficiency metrics based on the regressed stats
            # For QB
            if player.position == "QB" and current_projection.pass_attempts > 0:
                if current_projection.completions is not None:
                    current_projection.comp_pct = (
                        current_projection.completions / current_projection.pass_attempts * 100
                    )
                    
                if current_projection.pass_yards is not None:
                    current_projection.yards_per_att = (
                        current_projection.pass_yards / current_projection.pass_attempts
                    )
                    
                if current_projection.pass_td is not None:
                    current_projection.pass_td_rate = (
                        current_projection.pass_td / current_projection.pass_attempts
                    )
            
            # For rushing stats (QB/RB)
            if current_projection.rush_attempts is not None and current_projection.rush_attempts > 0:
                if current_projection.rush_yards is not None:
                    current_projection.yards_per_carry = (
                        current_projection.rush_yards / current_projection.rush_attempts
                    )
            
            # For receiving stats (RB/WR/TE)
            if current_projection.targets is not None and current_projection.targets > 0:
                if current_projection.receptions is not None:
                    current_projection.catch_pct = (
                        current_projection.receptions / current_projection.targets * 100
                    )
                    
                if current_projection.rec_yards is not None:
                    current_projection.yards_per_target = (
                        current_projection.rec_yards / current_projection.targets
                    )
            
            # Recalculate fantasy points
            current_projection.half_ppr = current_projection.calculate_fantasy_points()
            
            # Set updated timestamp
            current_projection.updated_at = datetime.utcnow()
            
            # Save changes
            self.db.commit()
            return current_projection
            
        except Exception as e:
            logger.error(f"Error applying statistical regression: {str(e)}")
            self.db.rollback()
            return None

    async def get_projection(self, projection_id: str) -> Optional[Projection]:
        """Retrieve a specific projection."""
        return self.db.query(Projection).filter(Projection.projection_id == projection_id).first()

    async def get_player_projections(
        self,
        player_id: Optional[str] = None,
        team: Optional[str] = None,
        season: Optional[int] = None,
        scenario_id: Optional[str] = None,
    ) -> List[Projection]:
        """Retrieve projections with optional filters."""
        query = self.db.query(Projection)

        if player_id:
            query = query.filter(Projection.player_id == player_id)

        if team:
            query = query.join(Player).filter(Player.team == team)

        if season:
            query = query.filter(Projection.season == season)

        if scenario_id:
            query = query.filter(Projection.scenario_id == scenario_id)

        return query.all()

    async def get_projection_by_player(self, player_id: str, season: int) -> Optional[Projection]:
        """Get a projection for a specific player and season."""
        projections = await self.get_player_projections(player_id=player_id, season=season)
        return projections[0] if projections else None

    async def create_base_projection(
        self, player_id: str, season: int, scenario_id: Optional[str] = None
    ) -> Optional[Projection]:
        """Create baseline projection from historical data."""
        try:
            # Get player and their historical stats
            player = self.db.get(Player, player_id)
            if not player:
                logger.error(f"Player {player_id} not found")
                return None

            # Get team stats for context
            team_stats = (
                self.db.query(TeamStat)
                .filter(and_(TeamStat.team == player.team, TeamStat.season == season))
                .first()
            )

            if not team_stats:
                logger.error(f"Team stats not found for {player.team} in {season}")
                return None

            # Get historical stats from previous season
            base_stats = (
                self.db.query(BaseStat)
                .filter(and_(BaseStat.player_id == player_id, BaseStat.season == season - 1))
                .all()
            )

            # Calculate baseline projection
            projection = await self._calculate_base_projection(
                player, team_stats, base_stats, season
            )

            if projection:
                # Set scenario_id if provided
                if scenario_id:
                    projection.scenario_id = scenario_id

                self.db.add(projection)
                self.db.commit()

            return projection

        except Exception as e:
            logger.error(f"Error creating base projection: {str(e)}")
            self.db.rollback()
            return None

    async def update_projection(
        self, projection_id: str, adjustments: AdjustmentDict
    ) -> Optional[Projection]:
        """Update an existing projection with adjustments."""
        try:
            # Use a join to get both the projection and the player in one query
            projection = (
                self.db.query(Projection)
                .join(Player)
                .filter(Projection.projection_id == projection_id)
                .first()
            )

            if not projection:
                return None

            # Get the player object
            player = projection.player

            # Validate adjustments
            if not await self.validate_adjustments(projection.player_id, adjustments):
                logger.error("Invalid adjustments provided")
                return None

            # Get team context
            team_stats = (
                self.db.query(TeamStat)
                .filter(and_(TeamStat.team == player.team, TeamStat.season == projection.season))
                .first()
            )

            # Make a deep copy of the projection for modification
            # We'll modify this copy and then persist it
            projection_values = {
                "projection_id": projection_id,
                "player_id": projection.player_id,
                "scenario_id": projection.scenario_id,
                "season": projection.season,
                "games": projection.games,
                "half_ppr": projection.half_ppr,
                # Copy all the fields that might be adjusted
                "pass_attempts": projection.pass_attempts,
                "completions": projection.completions,
                "pass_yards": projection.pass_yards,
                "pass_td": projection.pass_td,
                "interceptions": projection.interceptions,
                "rush_attempts": projection.rush_attempts,
                "rush_yards": projection.rush_yards,
                "rush_td": projection.rush_td,
                "targets": projection.targets,
                "receptions": projection.receptions,
                "rec_yards": projection.rec_yards,
                "rec_td": projection.rec_td,
                # Efficiency metrics
                "yards_per_att": projection.yards_per_att,
                "comp_pct": projection.comp_pct,
                "pass_td_rate": projection.pass_td_rate,
                "yards_per_carry": projection.yards_per_carry,
                "catch_pct": projection.catch_pct,
                "yards_per_target": projection.yards_per_target,
                "rec_td_rate": projection.rec_td_rate,
                # Other fields
                "snap_share": projection.snap_share,
                "target_share": projection.target_share,
                "rush_share": projection.rush_share,
                # Mark as updated
                "updated_at": datetime.utcnow(),
            }

            logger.debug(f"Adjusting {player.name} ({player.position}) with: {adjustments}")
            logger.debug(
                f"Before adjustments: pass_td={projection_values.get('pass_td', 'N/A')}, rush_td={projection_values.get('rush_td', 'N/A')}, rec_td={projection_values.get('rec_td', 'N/A')}"
            )

            # Apply adjustments based on player position
            if player.position == "QB":
                # QB adjustments
                if "pass_volume" in adjustments:
                    factor = adjustments["pass_volume"]
                    if projection_values.get("pass_attempts") is not None:
                        projection_values["pass_attempts"] = float(projection_values["pass_attempts"]) * factor
                    if projection_values.get("completions") is not None:
                        projection_values["completions"] = float(projection_values["completions"]) * factor
                    if projection_values.get("pass_yards") is not None:
                        projection_values["pass_yards"] = float(projection_values["pass_yards"]) * factor
                    
                    pass_attempts = projection_values.get("pass_attempts")
                    if pass_attempts is not None and float(pass_attempts) > 0:
                        pass_yards = projection_values.get("pass_yards")
                        completions = projection_values.get("completions")
                        
                        if pass_yards is not None:
                            projection_values["yards_per_att"] = float(pass_yards) / float(pass_attempts)
                        
                        if completions is not None:
                            projection_values["comp_pct"] = (
                                float(completions) / float(pass_attempts) * 100
                            )

                if "td_rate" in adjustments:
                    factor = adjustments["td_rate"]
                    pass_td = projection_values.get("pass_td")
                    if pass_td is not None:
                        old_pass_td = float(pass_td)
                        projection_values["pass_td"] = old_pass_td * factor
                        logger.debug(
                            f"QB td_rate adjustment: {old_pass_td} -> {projection_values['pass_td']} (factor: {factor})"
                        )
                        
                        pass_attempts = projection_values.get("pass_attempts")
                        if pass_attempts is not None and float(pass_attempts) > 0:
                            projection_values["pass_td_rate"] = (
                                float(projection_values["pass_td"]) / float(pass_attempts)
                            )

                if "int_rate" in adjustments:
                    int_rate = adjustments["int_rate"]
                    interceptions = projection_values.get("interceptions")
                    if interceptions is not None:
                        projection_values["interceptions"] = float(interceptions) * int_rate

                if "rush_volume" in adjustments:
                    factor = adjustments["rush_volume"]
                    
                    rush_attempts = projection_values.get("rush_attempts")
                    if rush_attempts is not None:
                        projection_values["rush_attempts"] = float(rush_attempts) * factor
                    
                    rush_yards = projection_values.get("rush_yards")
                    if rush_yards is not None:
                        projection_values["rush_yards"] = float(rush_yards) * factor
                    
                    rush_td = projection_values.get("rush_td")
                    if rush_td is not None:
                        projection_values["rush_td"] = float(rush_td) * factor
                    
                    updated_rush_attempts = projection_values.get("rush_attempts")
                    updated_rush_yards = projection_values.get("rush_yards")
                    
                    if (updated_rush_attempts is not None and 
                        updated_rush_yards is not None and 
                        float(updated_rush_attempts) > 0):
                        projection_values["yards_per_carry"] = (
                            float(updated_rush_yards) / float(updated_rush_attempts)
                        )

            elif player.position == "RB":
                # RB adjustments
                if "rush_volume" in adjustments:
                    factor = adjustments["rush_volume"]
                    
                    rush_attempts = projection_values.get("rush_attempts")
                    if rush_attempts is not None:
                        projection_values["rush_attempts"] = float(rush_attempts) * factor
                    
                    rush_yards = projection_values.get("rush_yards")
                    if rush_yards is not None:
                        projection_values["rush_yards"] = float(rush_yards) * factor
                    
                    rush_td = projection_values.get("rush_td")
                    if rush_td is not None:
                        projection_values["rush_td"] = float(rush_td) * factor
                    
                    updated_rush_attempts = projection_values.get("rush_attempts")
                    updated_rush_yards = projection_values.get("rush_yards")
                    
                    if (updated_rush_attempts is not None and 
                        updated_rush_yards is not None and 
                        float(updated_rush_attempts) > 0):
                        projection_values["yards_per_carry"] = (
                            float(updated_rush_yards) / float(updated_rush_attempts)
                        )

                if "target_share" in adjustments:
                    factor = adjustments["target_share"]
                    # Get the current target_share
                    current_target_share = projection_values.get("target_share", 0.0)
                    
                    # Use our safe helper function to calculate the relative multiplier
                    relative_factor = self._safe_calculate_share_factor(factor, current_target_share)
                    
                    # Store the target_share value (as a percentage between 0-0.5)
                    projection_values["target_share"] = min(0.5, max(0.0, factor))
                    
                    # Apply the relative factor to all receiving stats
                    targets = projection_values.get("targets")
                    if targets is not None:
                        projection_values["targets"] = float(targets) * relative_factor
                    
                    receptions = projection_values.get("receptions")
                    if receptions is not None:
                        projection_values["receptions"] = float(receptions) * relative_factor * 0.95
                    
                    rec_yards = projection_values.get("rec_yards")
                    if rec_yards is not None:
                        projection_values["rec_yards"] = float(rec_yards) * relative_factor
                    
                    rec_td = projection_values.get("rec_td")
                    if rec_td is not None:
                        projection_values["rec_td"] = float(rec_td) * relative_factor
                    
                    updated_targets = projection_values.get("targets")
                    updated_receptions = projection_values.get("receptions")
                    updated_rec_yards = projection_values.get("rec_yards")
                    updated_rec_td = projection_values.get("rec_td")
                    
                    # Safely handle target-based calculations
                    if updated_targets is not None:
                        try:
                            targets_float = float(updated_targets)
                            if targets_float > 0:
                                # Calculate catch_pct if receptions are available
                                if updated_receptions is not None:
                                    try:
                                        receptions_float = float(updated_receptions)
                                        projection_values["catch_pct"] = (receptions_float / targets_float) * 100
                                    except (ValueError, TypeError):
                                        pass
                                
                                # Calculate yards_per_target if rec_yards are available
                                if updated_rec_yards is not None:
                                    try:
                                        rec_yards_float = float(updated_rec_yards)
                                        projection_values["yards_per_target"] = rec_yards_float / targets_float
                                    except (ValueError, TypeError):
                                        pass
                                
                                # Calculate rec_td_rate if rec_td are available
                                if updated_rec_td is not None:
                                    try:
                                        rec_td_float = float(updated_rec_td)
                                        projection_values["rec_td_rate"] = rec_td_float / targets_float
                                    except (ValueError, TypeError):
                                        pass
                        except (ValueError, TypeError):
                            # Skip calculations if targets can't be converted to float
                            pass

                # Apply td_rate adjustment for RBs
                if "td_rate" in adjustments:
                    factor = adjustments["td_rate"]
                    
                    rush_td = projection_values.get("rush_td")
                    rec_td = projection_values.get("rec_td")
                    
                    old_rush_td = float(rush_td) if rush_td is not None else 0.0
                    old_rec_td = float(rec_td) if rec_td is not None else 0.0
                    
                    if rush_td is not None:
                        projection_values["rush_td"] = old_rush_td * factor
                    
                    if rec_td is not None:
                        projection_values["rec_td"] = old_rec_td * factor
                    
                    logger.debug(
                        f"RB td_rate adjustment: rush_td {old_rush_td} -> {projection_values.get('rush_td', 'N/A')}, rec_td {old_rec_td} -> {projection_values.get('rec_td', 'N/A')} (factor: {factor})"
                    )

            elif player.position in ["WR", "TE"]:
                # WR/TE adjustments
                if "target_share" in adjustments:
                    factor = adjustments["target_share"]
                    # Get the current target_share
                    current_target_share = projection_values.get("target_share", 0.0)
                    
                    # Use our safe helper function to calculate the relative multiplier
                    relative_factor = self._safe_calculate_share_factor(factor, current_target_share)
                    
                    # Store the target_share value (as a percentage between 0-0.5)
                    projection_values["target_share"] = min(0.5, max(0.0, factor))
                    
                    # Apply the relative factor to all receiving stats
                    targets = projection_values.get("targets")
                    if targets is not None:
                        projection_values["targets"] = float(targets) * relative_factor
                    
                    receptions = projection_values.get("receptions")
                    if receptions is not None:
                        projection_values["receptions"] = float(receptions) * relative_factor * 0.95
                    
                    rec_yards = projection_values.get("rec_yards")
                    if rec_yards is not None:
                        projection_values["rec_yards"] = float(rec_yards) * relative_factor
                    
                    rec_td = projection_values.get("rec_td")
                    if rec_td is not None:
                        projection_values["rec_td"] = float(rec_td) * relative_factor
                    
                    updated_targets = projection_values.get("targets")
                    updated_receptions = projection_values.get("receptions")
                    updated_rec_yards = projection_values.get("rec_yards")
                    updated_rec_td = projection_values.get("rec_td")
                    
                    # Safely handle target-based calculations
                    if updated_targets is not None:
                        try:
                            targets_float = float(updated_targets)
                            if targets_float > 0:
                                # Calculate catch_pct if receptions are available
                                if updated_receptions is not None:
                                    try:
                                        receptions_float = float(updated_receptions)
                                        projection_values["catch_pct"] = (receptions_float / targets_float) * 100
                                    except (ValueError, TypeError):
                                        pass
                                
                                # Calculate yards_per_target if rec_yards are available
                                if updated_rec_yards is not None:
                                    try:
                                        rec_yards_float = float(updated_rec_yards)
                                        projection_values["yards_per_target"] = rec_yards_float / targets_float
                                    except (ValueError, TypeError):
                                        pass
                                
                                # Calculate rec_td_rate if rec_td are available
                                if updated_rec_td is not None:
                                    try:
                                        rec_td_float = float(updated_rec_td)
                                        projection_values["rec_td_rate"] = rec_td_float / targets_float
                                    except (ValueError, TypeError):
                                        pass
                        except (ValueError, TypeError):
                            # Skip calculations if targets can't be converted to float
                            pass

                if "td_rate" in adjustments:
                    factor = adjustments["td_rate"]
                    rec_td = projection_values.get("rec_td")
                    old_rec_td = float(rec_td) if rec_td is not None else 0.0
                    
                    if rec_td is not None:
                        projection_values["rec_td"] = old_rec_td * factor
                    
                    logger.debug(
                        f"WR/TE td_rate adjustment: rec_td {old_rec_td} -> {projection_values.get('rec_td', 'N/A')} (factor: {factor})"
                    )

                if "snap_share" in adjustments:
                    snap_share = projection_values.get("snap_share")
                    current_snap_share = float(snap_share) if snap_share is not None else 0.0
                    adjusted_snap_share = current_snap_share * adjustments["snap_share"]
                    projection_values["snap_share"] = min(1.0, adjusted_snap_share)

            # Calculate fantasy points
            # First, update the projection with our adjusted values
            for key, value in projection_values.items():
                setattr(projection, key, value)

            # Calculate fantasy points
            original_half_ppr = projection.half_ppr if projection.half_ppr else 0.0
            calculated_half_ppr = projection.calculate_fantasy_points()
            projection_values["half_ppr"] = calculated_half_ppr

            logger.info(f"Fantasy points: original={original_half_ppr}, new={calculated_half_ppr}")
            logger.info(f"TD values: rush_td={projection.rush_td}, rec_td={projection.rec_td}")

            # Persist the changes - update the existing record with our values
            update_stmt = {
                key: value for key, value in projection_values.items() if key != "projection_id"
            }  # exclude primary key

            logger.debug(f"Updating with statement: {update_stmt}")

            self.db.query(Projection).filter(Projection.projection_id == projection_id).update(
                update_stmt
            )

            self.db.commit()

            # Get a completely fresh version of the projection from the database
            # This ensures we don't run into stale/cached data issues from SQLAlchemy
            self.db.expire_all()  # Clear any cached state on the session
            # Force a new query to get the latest data from database
            updated = (
                self.db.query(Projection).filter(Projection.projection_id == projection_id).first()
            )
            logger.info(f"Updated projection half_ppr: {updated.half_ppr}")
            logger.debug(
                f"Final values: pass_td={getattr(updated, 'pass_td', 'N/A')}, rush_td={getattr(updated, 'rush_td', 'N/A')}, rec_td={getattr(updated, 'rec_td', 'N/A')}"
            )
            return updated

        except Exception as e:
            logger.error(f"Error updating projection: {str(e)}")
            self.db.rollback()
            return None

    async def validate_adjustments(self, player_id: str, adjustments: AdjustmentDict) -> bool:
        """Validate adjustment factors for reasonableness."""
        try:
            for metric, value in adjustments.items():
                if metric not in self.adjustment_ranges:
                    logger.warning(f"Unknown adjustment metric: {metric}")
                    return False

                min_val, max_val = self.adjustment_ranges[metric]
                if not min_val <= value <= max_val:
                    logger.warning(
                        f"Adjustment {metric}={value} outside valid range "
                        f"({min_val}, {max_val})"
                    )
                    return False

            return True

        except Exception as e:
            logger.error(f"Error validating adjustments for player {player_id}: {str(e)}")
            return False

    async def create_scenario(
        self, name: str, description: Optional[str] = None, base_scenario_id: Optional[str] = None
    ) -> Optional[str]:
        """Create a new projection scenario."""
        try:
            scenario = Scenario(
                scenario_id=str(uuid.uuid4()),
                name=name,
                description=description,
                base_scenario_id=base_scenario_id,
            )

            self.db.add(scenario)
            self.db.commit()

            return scenario.scenario_id

        except Exception as e:
            logger.error(f"Error creating scenario: {str(e)}")
            self.db.rollback()
            return None

    async def apply_team_adjustments(
        self, team: str, season: int, adjustments: AdjustmentDict
    ) -> List[Projection]:
        """Apply adjustments at team level and update affected players."""
        try:
            # Get all players for the team
            players = self.db.query(Player).filter(Player.team == team).all()

            # Get team stats
            team_stats = (
                self.db.query(TeamStat)
                .filter(and_(TeamStat.team == team, TeamStat.season == season))
                .first()
            )

            if not team_stats:
                logger.error(f"Team stats not found for {team}")
                return []

            updated_projections = []

            # Update projections for each player
            for player in players:
                projections = await self.get_player_projections(player.player_id)

                for proj in projections:
                    # Adjust projection based on team-level changes
                    updated_proj = await self._apply_team_adjustment(proj, team_stats, adjustments)
                    if updated_proj:
                        updated_projections.append(updated_proj)

            self.db.commit()
            return updated_projections

        except Exception as e:
            logger.error(f"Error applying team adjustments: {str(e)}")
            self.db.rollback()
            return []

    class TrendItem(TypedDict):
        season: int
        week: int
        value: float
        
    async def get_projection_trends(
        self, player_id: str, stat_type: str, weeks: int = 8
    ) -> List[TrendItem]:
        """Get historical projection trends for analysis."""
        try:
            # Get base stats for specified period
            base_stats = (
                self.db.query(BaseStat)
                .filter(and_(BaseStat.player_id == player_id, BaseStat.stat_type == stat_type))
                .order_by(BaseStat.season.desc(), BaseStat.week.desc())
                .limit(weeks)
                .all()
            )

            # Format trend data
            return [
                {"season": stat.season or 0, 
                 "week": stat.week or 0, 
                 "value": float(stat.value) if stat.value is not None else 0.0}
                for stat in base_stats
            ]

        except Exception as e:
            logger.error(f"Error getting projection trends: {str(e)}")
            return []
            
    async def fix_efficiency_metrics(
        self, player_id: Optional[str] = None, team: Optional[str] = None, 
        position: Optional[str] = None, season: Optional[int] = None, 
        scenario_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Recalculate and fix efficiency metrics for projections.
        
        This method ensures that derived metrics like yards_per_att, comp_pct, etc.
        are consistent with the base statistics in the projections.
        
        Args:
            player_id: Optional specific player ID
            team: Optional team filter
            position: Optional position filter
            season: Optional season filter
            scenario_id: Optional scenario ID filter
            
        Returns:
            Dictionary with results summary
        """
        try:
            # Build query for projections
            query = self.db.query(Projection)
            
            if player_id:
                query = query.filter(Projection.player_id == player_id)
            elif team or position:
                # Join with Player table for team/position filtering
                query = query.join(Player)
                
                if team:
                    query = query.filter(Player.team == team)
                    
                if position:
                    query = query.filter(Player.position == position)
            
            if season:
                query = query.filter(Projection.season == season)
                
            if scenario_id:
                query = query.filter(Projection.scenario_id == scenario_id)
                
            projections = query.all()
            
            if not projections:
                return {"success": False, "message": "No projections found matching criteria", "count": 0}
            
            # Track results
            updated_count = 0
            error_messages = []
            
            # Process each projection
            for projection in projections:
                try:
                    # Get the player position to know which metrics to calculate
                    player = self.db.get(Player, projection.player_id)
                    if not player:
                        error_messages.append(f"Player not found for projection {projection.projection_id}")
                        continue
                    
                    # Calculate QB metrics
                    if player.position == "QB":
                        # Calculate completion percentage
                        if (projection.pass_attempts is not None and 
                            projection.pass_attempts > 0 and 
                            projection.completions is not None):
                            projection.comp_pct = (projection.completions / projection.pass_attempts) * 100
                            
                        # Calculate yards per attempt
                        if (projection.pass_attempts is not None and 
                            projection.pass_attempts > 0 and 
                            projection.pass_yards is not None):
                            projection.yards_per_att = projection.pass_yards / projection.pass_attempts
                            
                        # Calculate TD rate
                        if (projection.pass_attempts is not None and 
                            projection.pass_attempts > 0 and 
                            projection.pass_td is not None):
                            projection.pass_td_rate = projection.pass_td / projection.pass_attempts
                            
                        # Calculate INT rate
                        if (projection.pass_attempts is not None and 
                            projection.pass_attempts > 0 and 
                            projection.interceptions is not None):
                            projection.int_rate = projection.interceptions / projection.pass_attempts
                    
                    # Calculate rushing metrics for all positions
                    if (projection.rush_attempts is not None and 
                        projection.rush_attempts > 0 and 
                        projection.rush_yards is not None):
                        projection.yards_per_carry = projection.rush_yards / projection.rush_attempts
                        
                        if projection.rush_td is not None:
                            projection.rush_td_rate = projection.rush_td / projection.rush_attempts
                    
                    # Calculate receiving metrics for relevant positions
                    if player.position in ["RB", "WR", "TE"]:
                        if (projection.targets is not None and 
                            projection.targets > 0):
                            
                            # Calculate catch percentage
                            if projection.receptions is not None:
                                projection.catch_pct = (projection.receptions / projection.targets) * 100
                                
                            # Calculate yards per target
                            if projection.rec_yards is not None:
                                projection.yards_per_target = projection.rec_yards / projection.targets
                                
                            # Calculate receiving TD rate
                            if projection.rec_td is not None:
                                projection.rec_td_rate = projection.rec_td / projection.targets
                    
                    # Set usage metrics if they are not set
                    # These are specifically for team context and require team stats
                    # We'll just set reasonable defaults here based on position if they're None
                    if projection.snap_share is None:
                        if player.position == "QB":
                            projection.snap_share = 1.0  # Starting QBs typically play all snaps
                        elif player.position == "RB":
                            projection.snap_share = 0.5  # RBs often rotate
                        elif player.position == "WR" or player.position == "TE":
                            projection.snap_share = 0.7  # Typical for starting receivers
                    
                    # Recalculate fantasy points
                    projection.half_ppr = projection.calculate_fantasy_points()
                    
                    # Set updated timestamp
                    projection.updated_at = datetime.utcnow()
                    
                    updated_count += 1
                    
                except Exception as e:
                    error_messages.append(f"Error updating metrics for projection {projection.projection_id}: {str(e)}")
            
            # Commit all changes
            self.db.commit()
            
            return {
                "success": True,
                "message": f"Updated efficiency metrics for {updated_count} of {len(projections)} projections",
                "count": updated_count,
                "errors": error_messages if error_messages else None
            }
            
        except Exception as e:
            logger.error(f"Error fixing efficiency metrics: {str(e)}")
            self.db.rollback()
            return {"success": False, "message": f"Error fixing efficiency metrics: {str(e)}", "count": 0}
    
    async def batch_apply_regression(
        self, team: Optional[str] = None, position: Optional[str] = None, 
        season: int = 2024, scenario_id: Optional[str] = None,
        active_only: bool = True
    ) -> Dict[str, Any]:
        """
        Apply statistical regression to a batch of players, filtered by team and/or position.
        
        Args:
            team: Optional team filter
            position: Optional position filter
            season: Season to apply regression to
            scenario_id: Optional scenario ID
            
        Returns:
            Dictionary with results summary
        """
        try:
            # Build query for players
            query = self.db.query(Player)
            
            if team:
                query = query.filter(Player.team == team)
                
            if position:
                query = query.filter(Player.position == position)
                
            players = query.all()
            
            # Filter for active players if requested
            if active_only:
                # Track original count for logging
                original_count = len(players)
                players = self.filter_active_players(players, season=season)
                logger.info(f"Active player filtering: {len(players)}/{original_count} players retained")
            
            if not players:
                return {"success": False, "message": "No players found matching criteria", "count": 0}
                
            # Track results
            success_count = 0
            error_messages = []
            
            # Process each player
            for player in players:
                try:
                    # Apply regression
                    result = await self.apply_statistical_regression(
                        player_id=player.player_id,
                        season=season,
                        scenario_id=scenario_id
                    )
                    
                    if result:
                        success_count += 1
                    else:
                        error_messages.append(f"Failed to apply regression for {player.name}")
                        
                except Exception as e:
                    error_messages.append(f"Error applying regression for {player.name}: {str(e)}")
            
            return {
                "success": True,
                "message": f"Applied regression to {success_count} of {len(players)} players",
                "count": success_count,
                "errors": error_messages if error_messages else None
            }
            
        except Exception as e:
            logger.error(f"Error in batch regression: {str(e)}")
            return {"success": False, "message": f"Error in batch regression: {str(e)}", "count": 0}

    async def _calculate_base_projection(
        self, player: Player, team_stats: TeamStat, base_stats: List[BaseStat], season: int
    ) -> Optional[Projection]:
        """Calculate baseline projection from historical data."""
        try:
            # Convert base stats to dictionary for easier access
            stats_dict: StatsDict = {
                cast(str, stat.stat_type): float(stat.value) 
                for stat in base_stats 
                if stat.stat_type and stat.value is not None
            }

            # If no historical stats, estimate from team context
            if not stats_dict:
                stats_dict = self._estimate_stats_from_team_context(player, team_stats)

            # Create base projection
            projection = Projection(
                projection_id=str(uuid.uuid4()),
                player_id=player.player_id,
                season=season,
                games=17,  # Full season
            )

            # Set position-specific stats using a polymorphic approach
            position_setters = {
                "QB": self._set_qb_stats,
                "RB": self._set_rb_stats,
                "WR": self._set_receiver_stats,
                "TE": self._set_receiver_stats,
            }

            setter = position_setters.get(player.position)
            if setter:
                setter(projection, stats_dict, team_stats)

            # Calculate fantasy points
            projection.half_ppr = projection.calculate_fantasy_points()

            return projection

        except Exception as e:
            logger.error(f"Error calculating base projection: {str(e)}")
            return None

    def _estimate_stats_from_team_context(self, player: Player, team_stats: TeamStat) -> StatsDict:
        """Estimate baseline stats from team context when no historical data available."""
        position_estimators = {
            "QB": self._estimate_qb_stats,
            "RB": self._estimate_rb_stats,
            "WR": self._estimate_receiver_stats,
            "TE": self._estimate_receiver_stats,
        }

        estimator = position_estimators.get(player.position)
        return estimator(team_stats) if estimator else {}

    def _estimate_qb_stats(self, team_stats: TeamStat) -> StatsDict:
        """Estimate QB stats based on team context."""
        return {
            "pass_attempts": team_stats.pass_attempts * 0.95,
            "completions": team_stats.receptions * 0.95,
            "pass_yards": team_stats.pass_yards * 0.95,
            "pass_td": team_stats.pass_td * 0.95,
            "interceptions": team_stats.pass_attempts * 0.02,
            "rush_attempts": 40,
            "rush_yards": 200,
            "rush_td": 2,
        }

    def _estimate_rb_stats(self, team_stats: TeamStat) -> StatsDict:
        """Estimate RB stats based on team context."""
        return {
            "rush_attempts": team_stats.rush_attempts * 0.4,
            "rush_yards": team_stats.rush_yards * 0.4,
            "rush_td": team_stats.rush_td * 0.4,
            "targets": team_stats.targets * 0.1,
            "receptions": team_stats.receptions * 0.1,
            "rec_yards": team_stats.rec_yards * 0.08,
            "rec_td": team_stats.rec_td * 0.08,
        }

    def _estimate_receiver_stats(self, team_stats: TeamStat) -> StatsDict:
        """Estimate WR/TE stats based on team context."""
        return {
            "targets": team_stats.targets * 0.15,
            "receptions": team_stats.receptions * 0.15,
            "rec_yards": team_stats.rec_yards * 0.15,
            "rec_td": team_stats.rec_td * 0.15,
            "rush_attempts": 0,
            "rush_yards": 0,
            "rush_td": 0,
        }

    async def _adjust_stats(
        self, projection: Projection, team_stats: TeamStat, adjustments: AdjustmentDict
    ) -> None:
        """Generic stat adjustment method based on player position."""
        position_adjusters = {
            "QB": self._adjust_qb_stats,
            "RB": self._adjust_rb_stats,
            "WR": self._adjust_receiver_stats,
            "TE": self._adjust_receiver_stats,
        }

        adjuster = position_adjusters.get(projection.player.position)
        if adjuster:
            await adjuster(projection, team_stats, adjustments)

        # Create a new instance with the same ID to ensure updates are tracked by SQLAlchemy
        # The adjustment changes weren't being persisted because we're modifying the same object
        projection.updated_at = datetime.utcnow()
        self.db.flush()

    async def _adjust_qb_stats(
        self, projection: Projection, team_stats: TeamStat, adjustments: AdjustmentDict
    ) -> None:
        """Adjust QB-specific statistics."""
        if "pass_volume" in adjustments:
            factor = adjustments["pass_volume"]
            projection.pass_attempts = projection.pass_attempts * factor
            projection.completions = projection.completions * factor
            projection.pass_yards = projection.pass_yards * factor

        if "td_rate" in adjustments:
            projection.pass_td = projection.pass_td * adjustments["td_rate"]
            if projection.pass_attempts > 0:
                projection.pass_td_rate = projection.pass_td / projection.pass_attempts

        if "int_rate" in adjustments:
            projection.interceptions = projection.interceptions * adjustments["int_rate"]

        if "rush_share" in adjustments:
            factor = adjustments["rush_share"]
            projection.rush_attempts = projection.rush_attempts * factor
            projection.rush_yards = projection.rush_yards * factor
            projection.rush_td = projection.rush_td * factor

    async def _adjust_rb_stats(
        self, projection: Projection, team_stats: TeamStat, adjustments: AdjustmentDict
    ) -> None:
        """Adjust RB-specific statistics."""
        if "rush_share" in adjustments:
            factor = adjustments["rush_share"]
            current_rush_share = getattr(projection, "rush_share", 0.0) or 0.0
            
            # Calculate the relative multiplier based on the current and new rush share
            relative_factor = factor / current_rush_share if current_rush_share > 0 else factor
            
            # Store the rush_share value (as a percentage between 0-0.5)
            projection.rush_share = min(0.5, max(0.0, factor))
            
            # Apply adjustments based on the relative factor
            if projection.rush_attempts is not None:
                projection.rush_attempts = projection.rush_attempts * relative_factor
                
            if projection.rush_yards is not None:
                projection.rush_yards = projection.rush_yards * relative_factor
                
            if projection.rush_td is not None:
                projection.rush_td = projection.rush_td * relative_factor
                
            if projection.rush_attempts is not None and projection.rush_attempts > 0:
                if projection.rush_yards is not None:
                    projection.yards_per_carry = projection.rush_yards / projection.rush_attempts
                    
                if projection.rush_td is not None:
                    projection.rush_td_rate = projection.rush_td / projection.rush_attempts

        if "target_share" in adjustments:
            factor = adjustments["target_share"]
            current_target_share = getattr(projection, "target_share", 0.0)
            
            # Use our safe helper function to calculate the relative multiplier
            relative_factor = self._safe_calculate_share_factor(factor, current_target_share)
            
            # Store the target_share value (as a percentage between 0-0.5)
            projection.target_share = min(0.5, max(0.0, factor))
            
            # Apply adjustments based on the relative factor
            if projection.targets is not None:
                projection.targets = projection.targets * relative_factor
                
            if projection.receptions is not None:
                # Slight reduction in catch rate
                projection.receptions = projection.receptions * (relative_factor * 0.95)
                
            if projection.rec_yards is not None:
                projection.rec_yards = projection.rec_yards * relative_factor
                
            if projection.rec_td is not None:
                projection.rec_td = projection.rec_td * relative_factor
                
            if projection.targets is not None and projection.targets > 0:
                if projection.receptions is not None:
                    projection.catch_pct = projection.receptions / projection.targets * 100
                    
                if projection.rec_yards is not None:
                    projection.yards_per_target = projection.rec_yards / projection.targets
                    
                if projection.rec_td is not None:
                    projection.rec_td_rate = projection.rec_td / projection.targets

    async def _adjust_receiver_stats(
        self, projection: Projection, team_stats: TeamStat, adjustments: AdjustmentDict
    ) -> None:
        """Adjust WR/TE-specific statistics."""
        if "target_share" in adjustments:
            factor = adjustments["target_share"]
            current_target_share = getattr(projection, "target_share", 0.0)
            
            # Use our safe helper function to calculate the relative multiplier
            relative_factor = self._safe_calculate_share_factor(factor, current_target_share)
            
            # Store the target_share value (as a percentage between 0-0.5)
            projection.target_share = min(0.5, max(0.0, factor))
            
            # Apply adjustments based on the relative factor
            if projection.targets is not None:
                projection.targets = projection.targets * relative_factor
                
            if projection.receptions is not None:
                projection.receptions = projection.receptions * (relative_factor * 0.95)
                
            if projection.rec_yards is not None:    
                projection.rec_yards = projection.rec_yards * relative_factor
                
            if projection.rec_td is not None:
                projection.rec_td = projection.rec_td * relative_factor
                
            if projection.targets is not None and projection.targets > 0:
                if projection.receptions is not None:
                    projection.catch_pct = projection.receptions / projection.targets * 100
                    
                if projection.rec_yards is not None:
                    projection.yards_per_target = projection.rec_yards / projection.targets
                    
                if projection.rec_td is not None:
                    projection.rec_td_rate = projection.rec_td / projection.targets

        if "snap_share" in adjustments:
            factor = adjustments["snap_share"]
            current_snap_share = getattr(projection, "snap_share", 0.0) or 0.0
            projection.snap_share = min(1.0, current_snap_share * factor)

    async def _apply_team_adjustment(
        self, projection: Projection, team_stats: TeamStat, adjustments: AdjustmentDict
    ) -> Optional[Projection]:
        """Apply team-level adjustments to individual projection."""
        try:
            # Adjust based on team-level changes
            if "pass_volume" in adjustments and projection.player.position == "QB":
                factor = adjustments["pass_volume"]
                
                if projection.pass_attempts is not None:
                    projection.pass_attempts = projection.pass_attempts * factor
                
                if projection.completions is not None:
                    projection.completions = projection.completions * factor
                
                if projection.pass_yards is not None:
                    projection.pass_yards = projection.pass_yards * factor
                
                if projection.pass_attempts is not None and projection.pass_attempts > 0:
                    if projection.pass_yards is not None:
                        projection.yards_per_att = projection.pass_yards / projection.pass_attempts

            # Adjust receiver targets based on pass volume
            if "pass_volume" in adjustments and projection.player.position in ["WR", "TE", "RB"]:
                factor = adjustments["pass_volume"]
                
                if projection.targets is not None:
                    projection.targets = projection.targets * factor
                    
                    if projection.receptions is not None:
                        projection.receptions = projection.receptions * factor
                    
                    if projection.rec_yards is not None:
                        projection.rec_yards = projection.rec_yards * factor
                    
                    if projection.targets > 0 and projection.rec_yards is not None:
                        projection.yards_per_target = projection.rec_yards / projection.targets

            if "rush_volume" in adjustments:
                factor = adjustments["rush_volume"]
                
                if projection.rush_attempts is not None:
                    projection.rush_attempts = projection.rush_attempts * factor
                    
                    if projection.rush_yards is not None:
                        projection.rush_yards = projection.rush_yards * factor
                        
                        if projection.rush_attempts > 0:
                            projection.yards_per_carry = (
                                projection.rush_yards / projection.rush_attempts
                            )

            if "scoring_rate" in adjustments:
                factor = adjustments["scoring_rate"]
                
                if projection.pass_td is not None:
                    projection.pass_td = projection.pass_td * factor
                    if projection.pass_attempts is not None and projection.pass_attempts > 0:
                        projection.pass_td_rate = projection.pass_td / projection.pass_attempts
                
                if projection.rush_td is not None:
                    projection.rush_td = projection.rush_td * factor
                    if projection.rush_attempts is not None and projection.rush_attempts > 0:
                        projection.rush_td_rate = projection.rush_td / projection.rush_attempts
                
                if projection.rec_td is not None:
                    projection.rec_td = projection.rec_td * factor
                    if projection.targets is not None and projection.targets > 0:
                        projection.rec_td_rate = projection.rec_td / projection.targets

            # Recalculate fantasy points
            projection.half_ppr = projection.calculate_fantasy_points()
            projection.updated_at = datetime.utcnow()

            # Make sure changes are persisted
            self.db.flush()

            return projection

        except Exception as e:
            logger.error(f"Error applying team adjustment: {str(e)}")
            return None

    def _set_qb_stats(self, projection: Projection, stats_dict: StatsDict, team_stats: TeamStat) -> None:
        """Set QB-specific projection stats."""
        projection.pass_attempts = stats_dict.get("pass_attempts", team_stats.pass_attempts)
        projection.completions = stats_dict.get("completions", team_stats.receptions)
        projection.pass_yards = stats_dict.get("pass_yards", team_stats.pass_yards)
        projection.pass_td = stats_dict.get("pass_td", team_stats.pass_td)
        projection.interceptions = stats_dict.get("interceptions", 0)
        projection.rush_attempts = stats_dict.get("rush_attempts", 0)
        projection.rush_yards = stats_dict.get("rush_yards", 0)
        projection.rush_td = stats_dict.get("rush_td", 0)

        # Calculate efficiency metrics
        if (projection.pass_attempts is not None and 
            projection.pass_attempts > 0):
            
            if projection.pass_yards is not None:
                projection.yards_per_att = projection.pass_yards / projection.pass_attempts
            
            if projection.completions is not None:
                projection.comp_pct = projection.completions / projection.pass_attempts * 100
            
            if projection.pass_td is not None:
                projection.pass_td_rate = projection.pass_td / projection.pass_attempts

        if (projection.rush_attempts is not None and 
            projection.rush_attempts > 0 and 
            projection.rush_yards is not None):
            
            projection.yards_per_carry = projection.rush_yards / projection.rush_attempts

    def _set_rb_stats(self, projection: Projection, stats_dict: StatsDict, team_stats: TeamStat) -> None:
        """Set RB-specific projection stats."""
        projection.rush_attempts = stats_dict.get("rush_attempts", 0)
        projection.rush_yards = stats_dict.get("rush_yards", 0)
        projection.rush_td = stats_dict.get("rush_td", 0)
        projection.targets = stats_dict.get("targets", 0)
        projection.receptions = stats_dict.get("receptions", 0)
        projection.rec_yards = stats_dict.get("rec_yards", 0)
        projection.rec_td = stats_dict.get("rec_td", 0)

        # Calculate efficiency metrics
        if (projection.rush_attempts is not None and 
            projection.rush_attempts > 0):
            
            if projection.rush_yards is not None:
                projection.yards_per_carry = projection.rush_yards / projection.rush_attempts
            
            if projection.rush_td is not None:
                projection.rush_td_rate = projection.rush_td / projection.rush_attempts

        if (projection.targets is not None and 
            projection.targets > 0):
            
            if projection.receptions is not None:
                projection.catch_pct = projection.receptions / projection.targets * 100
            
            if projection.rec_yards is not None:
                projection.yards_per_target = projection.rec_yards / projection.targets
            
            if projection.rec_td is not None:
                projection.rec_td_rate = projection.rec_td / projection.targets

    def _set_receiver_stats(
        self, projection: Projection, stats_dict: StatsDict, team_stats: TeamStat
    ) -> None:
        """Set WR/TE-specific projection stats."""
        projection.targets = stats_dict.get("targets", 0)
        projection.receptions = stats_dict.get("receptions", 0)
        projection.rec_yards = stats_dict.get("rec_yards", 0)
        projection.rec_td = stats_dict.get("rec_td", 0)
        projection.rush_attempts = stats_dict.get("rush_attempts", 0)
        projection.rush_yards = stats_dict.get("rush_yards", 0)
        projection.rush_td = stats_dict.get("rush_td", 0)

        # Calculate efficiency metrics
        if (projection.targets is not None and 
            projection.targets > 0):
            
            if projection.receptions is not None:
                projection.catch_pct = projection.receptions / projection.targets * 100
            
            if projection.rec_yards is not None:
                projection.yards_per_target = projection.rec_yards / projection.targets
            
            if projection.rec_td is not None:
                projection.rec_td_rate = projection.rec_td / projection.targets

        if (projection.rush_attempts is not None and 
            projection.rush_attempts > 0 and 
            projection.rush_yards is not None):
            
            projection.yards_per_carry = projection.rush_yards / projection.rush_attempts
