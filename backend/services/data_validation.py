import logging
from typing import Dict, List, Optional, Any, Tuple, Set
from typing_extensions import TypedDict
from sqlalchemy.orm import Session
from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError

from backend.database.models import Player, BaseStat, GameStats, TeamStat, Projection
from backend.services.typing import safe_float, safe_dict_get, safe_calculate

logger = logging.getLogger(__name__)


class ValidationResultDict(TypedDict):
    """Results of a validation operation."""
    valid: bool
    message: str
    issues: List[str]
    team_stats: Optional[Dict[str, Any]]


class DataValidationService:
    """Service for validating and fixing inconsistencies in imported data."""

    def __init__(self, db: Session):
        self.db = db
        # Define the minimum stats that should exist for each position
        self.required_stats = {
            "QB": {
                "games",
                "completions",
                "pass_attempts",
                "pass_yards",
                "pass_td",
                "interceptions",
                "rush_attempts",
                "rush_yards",
                "rush_td",
            },
            "RB": {
                "games",
                "rush_attempts",
                "rush_yards",
                "rush_td",
                "targets",
                "receptions",
                "rec_yards",
                "rec_td",
            },
            "WR": {
                "games",
                "targets",
                "receptions",
                "rec_yards",
                "rec_td",
                "rush_attempts",
                "rush_yards",
                "rush_td",
            },
            "TE": {"games", "targets", "receptions", "rec_yards", "rec_td"},
        }

    def validate_player_data(self, player: Player, season: int) -> List[str]:
        """
        Validate a player's data for a specific season.

        Returns:
            List of validation issues found.
        """
        issues = []

        # Skip if player's position is not defined
        if player.position not in self.required_stats:
            return [f"Player {player.name} has invalid position: {player.position}"]

        # Check game counts
        issues.extend(self._check_game_counts(player, season))

        # Verify season totals against game logs
        issues.extend(self._verify_season_totals(player, season))

        # Check for missing required stats
        issues.extend(self._check_missing_stats(player, season))

        return issues

    def _check_game_counts(self, player: Player, season: int) -> List[str]:
        """Verify that the games count stat matches the number of game logs."""
        issues = []

        # Get game logs
        game_stats = (
            self.db.query(GameStats)
            .filter(and_(GameStats.player_id == player.player_id, GameStats.season == season))
            .all()
        )

        # Get games count stat
        games_stat = (
            self.db.query(BaseStat)
            .filter(
                and_(
                    BaseStat.player_id == player.player_id,
                    BaseStat.season == season,
                    BaseStat.stat_type == "games",
                )
            )
            .first()
        )

        if not game_stats and not games_stat:
            # No data for this season
            return []

        game_count = len(game_stats)

        if not games_stat:
            issues.append(
                f"Player {player.name} has {game_count} game logs but no games count stat"
            )
            self._fix_games_count(player, season, game_count)
        elif game_count != int(games_stat.value):
            issues.append(
                f"Player {player.name} has {game_count} game logs but games stat is {int(games_stat.value)}"
            )
            self._fix_games_count(player, season, game_count)

        return issues

    def _verify_season_totals(self, player: Player, season: int) -> List[str]:
        """Verify that season totals match the sum of game logs."""
        issues = []

        # Get game logs
        game_stats = (
            self.db.query(GameStats)
            .filter(and_(GameStats.player_id == player.player_id, GameStats.season == season))
            .all()
        )

        if not game_stats:
            return []

        # Get base stats
        base_stats = (
            self.db.query(BaseStat)
            .filter(
                and_(
                    BaseStat.player_id == player.player_id,
                    BaseStat.season == season,
                    BaseStat.stat_type != "games",  # Exclude games count
                )
            )
            .all()
        )

        # Convert to dictionary
        base_stat_dict = {stat.stat_type: stat.value for stat in base_stats}

        # Define stat mapping (similar to the mappings in NFLDataImportService)
        stat_mappings = {
            "QB": {
                "completions": "cmp",
                "pass_attempts": "att",
                "pass_yards": "pass_yds",
                "pass_td": "pass_td",
                "interceptions": "int",
                "rush_attempts": "rush_att",
                "rush_yards": "rush_yds",
                "rush_td": "rush_td",
                "sacks": "sacked",
            },
            "RB": {
                "rush_attempts": "rush_att",
                "rush_yards": "rush_yds",
                "rush_td": "rush_td",
                "targets": "tgt",
                "receptions": "rec",
                "rec_yards": "rec_yds",
                "rec_td": "rec_td",
            },
            "WR": {
                "targets": "tgt",
                "receptions": "rec",
                "rec_yards": "rec_yds",
                "rec_td": "rec_td",
                "rush_attempts": "rush_att",
                "rush_yards": "rush_yds",
                "rush_td": "rush_td",
            },
            "TE": {
                "targets": "tgt",
                "receptions": "rec",
                "rec_yards": "rec_yds",
                "rec_td": "rec_td",
            },
        }

        # Calculate totals from game logs
        calculated_totals = {}

        for stat_name, nfl_data_name in stat_mappings[player.position].items():
            total = 0
            for game in game_stats:
                if nfl_data_name in game.stats:
                    try:
                        total += float(game.stats[nfl_data_name])
                    except (ValueError, TypeError):
                        issues.append(
                            f"Player {player.name} has invalid value for {nfl_data_name} in game {game.week}"
                        )
                        continue

            calculated_totals[stat_name] = total

            # Compare with stored values using safe_float for type safety
            if stat_name in base_stat_dict:
                stored_value = safe_float(base_stat_dict[stat_name], 0)
                calculated_value = safe_float(total, 0)

                # Allow small rounding differences (0.1%)
                if calculated_value > 0 and abs(stored_value - calculated_value) / calculated_value > 0.001:
                    issues.append(
                        f"Player {player.name} has inconsistent {stat_name}: stored={stored_value}, calculated={calculated_value}"
                    )
                    # Fix the inconsistency
                    self._fix_stat_value(player, season, stat_name, calculated_value)
            else:
                # Missing stat that should exist
                issues.append(f"Player {player.name} is missing {stat_name} stat")
                self._add_missing_stat(player, season, stat_name, total)

        return issues

    def _check_missing_stats(self, player: Player, season: int) -> List[str]:
        """Check if any required stats are missing."""
        issues = []

        # Get all base stats for this player and season
        base_stats = (
            self.db.query(BaseStat)
            .filter(and_(BaseStat.player_id == player.player_id, BaseStat.season == season))
            .all()
        )

        if not base_stats:
            return []

        # Get set of stat types that exist
        existing_stats = {stat.stat_type for stat in base_stats}

        # Check for missing required stats
        required = self.required_stats[player.position]
        missing = required - existing_stats

        if missing:
            for stat_type in missing:
                issues.append(f"Player {player.name} is missing required stat: {stat_type}")

                # We don't have enough information to fix this here
                # The _verify_season_totals method will fix it if game logs exist

        return issues

    def _fix_games_count(self, player: Player, season: int, game_count: int) -> None:
        """Fix the games count stat."""
        try:
            games_stat = (
                self.db.query(BaseStat)
                .filter(
                    and_(
                        BaseStat.player_id == player.player_id,
                        BaseStat.season == season,
                        BaseStat.stat_type == "games",
                    )
                )
                .first()
            )

            if games_stat:
                games_stat.value = float(game_count)
            else:
                games_stat = BaseStat(
                    player_id=player.player_id,
                    season=season,
                    stat_type="games",
                    value=float(game_count),
                )
                self.db.add(games_stat)

            self.db.flush()
            logger.info(f"Fixed games count for {player.name}: now {game_count}")
        except SQLAlchemyError as e:
            logger.error(f"Error fixing games count for {player.name}: {str(e)}")
            self.db.rollback()

    def _fix_stat_value(self, player: Player, season: int, stat_type: str, value: float) -> None:
        """Fix an incorrect stat value."""
        try:
            stat = (
                self.db.query(BaseStat)
                .filter(
                    and_(
                        BaseStat.player_id == player.player_id,
                        BaseStat.season == season,
                        BaseStat.stat_type == stat_type,
                    )
                )
                .first()
            )

            if stat:
                stat.value = value
                self.db.flush()
                logger.info(f"Fixed {stat_type} for {player.name}: now {value}")
        except SQLAlchemyError as e:
            logger.error(f"Error fixing {stat_type} for {player.name}: {str(e)}")
            self.db.rollback()

    def _add_missing_stat(self, player: Player, season: int, stat_type: str, value: float) -> None:
        """Add a missing stat."""
        try:
            new_stat = BaseStat(
                player_id=player.player_id, season=season, stat_type=stat_type, value=value
            )
            self.db.add(new_stat)
            self.db.flush()
            logger.info(f"Added missing {stat_type} for {player.name}: {value}")
        except SQLAlchemyError as e:
            logger.error(f"Error adding {stat_type} for {player.name}: {str(e)}")
            self.db.rollback()

    def validate_team_consistency(self, team: str, season: int) -> List[str]:
        """
        Validate that team-level stats are consistent with the sum of player stats.
        
        Args:
            team: The team abbreviation
            season: The season to validate
            
        Returns:
            List of validation issues found
        """
        issues = []
        
        try:
            # Get team stats
            team_stats = (
                self.db.query(TeamStat)
                .filter(and_(TeamStat.team == team, TeamStat.season == season))
                .first()
            )
            
            if not team_stats:
                return [f"No team stats found for {team} in season {season}"]
                
            # Get all players for the team in this season
            players = (
                self.db.query(Player)
                .filter(Player.team == team)
                .all()
            )
            
            if not players:
                return [f"No players found for team {team}"]
                
            # Retrieve base stats for all players
            player_ids = [player.player_id for player in players]
            
            # Get all base stats for these players in this season
            all_player_stats = (
                self.db.query(BaseStat)
                .filter(
                    and_(
                        BaseStat.player_id.in_(player_ids),
                        BaseStat.season == season,
                    )
                )
                .all()
            )
            
            # Group stats by player_id and stat_type
            player_stats_by_id = {}
            for stat in all_player_stats:
                if stat.player_id not in player_stats_by_id:
                    player_stats_by_id[stat.player_id] = {}
                player_stats_by_id[stat.player_id][stat.stat_type] = safe_float(stat.value, 0)
            
            # Initialize aggregated stats
            aggregated_stats = {
                "pass_attempts": 0,
                "completions": 0,
                "pass_yards": 0,
                "pass_td": 0,
                "interceptions": 0,
                "rush_attempts": 0,
                "rush_yards": 0,
                "rush_td": 0,
                "targets": 0,
                "receptions": 0,
                "rec_yards": 0,
                "rec_td": 0,
            }
            
            # Aggregate player stats
            for player_id, stats in player_stats_by_id.items():
                for stat_type, value in stats.items():
                    if stat_type in aggregated_stats:
                        aggregated_stats[stat_type] += value
            
            # Compare with team stats
            stat_comparisons = [
                ("pass_attempts", "pass_attempts", 0.02),  # 2% tolerance
                ("completions", "completions", 0.02),
                ("pass_yards", "pass_yards", 0.02),
                ("pass_td", "pass_td", 0.05),  # Higher tolerance for TDs
                ("interceptions", "interceptions", 0.05),
                ("rush_attempts", "rush_attempts", 0.02),
                ("rush_yards", "rush_yards", 0.02),
                ("rush_td", "rush_td", 0.05),
                ("targets", "targets", 0.02),
                ("receptions", "receptions", 0.02),
                ("rec_yards", "rec_yards", 0.02),
                ("rec_td", "rec_td", 0.05),
            ]
            
            # Check each stat
            for player_stat, team_stat_attr, tolerance in stat_comparisons:
                if not hasattr(team_stats, team_stat_attr):
                    issues.append(f"Team stats missing {team_stat_attr}")
                    continue
                    
                team_value = safe_float(getattr(team_stats, team_stat_attr), 0)
                player_sum = aggregated_stats[player_stat]
                
                # Skip check if both values are 0 or very small
                if team_value < 0.1 and player_sum < 0.1:
                    continue
                
                # Calculate difference percentage (avoid division by zero)
                denominator = max(team_value, 1.0)  # Avoid division by zero
                diff_pct = abs(team_value - player_sum) / denominator
                
                if diff_pct > tolerance:
                    issues.append(
                        f"{team_stat_attr} mismatch: Team value {team_value} != Player sum {player_sum}, diff: {diff_pct:.1%}"
                    )
            
            # Verify that passing stats match receiving stats within the team
            if abs(aggregated_stats["pass_yards"] - aggregated_stats["rec_yards"]) > 10:
                issues.append(
                    f"Team internal consistency issue: Pass yards {aggregated_stats['pass_yards']} != Rec yards {aggregated_stats['rec_yards']}"
                )
                
            if abs(aggregated_stats["pass_td"] - aggregated_stats["rec_td"]) > 0.5:
                issues.append(
                    f"Team internal consistency issue: Pass TDs {aggregated_stats['pass_td']} != Rec TDs {aggregated_stats['rec_td']}"
                )
                
            return issues
            
        except Exception as e:
            logger.error(f"Error validating team consistency for {team} in season {season}: {str(e)}")
            return [f"Error validating team consistency: {str(e)}"]

    async def validate_team_stats(self, team: str, season: Optional[int] = None) -> ValidationResultDict:
        """
        Validate team statistics for consistency.

        Args:
            team: The team abbreviation to validate
            season: Optional season to filter by, if not provided uses the latest season

        Returns:
            ValidationResultDict with validation results
        """
        try:
            # Build query for team stats
            query = self.db.query(TeamStat).filter(TeamStat.team == team)

            if season:
                query = query.filter(TeamStat.season == season)
            else:
                # Use the latest season if not specified
                latest_season = (
                    self.db.query(TeamStat.season).order_by(TeamStat.season.desc()).first()
                )
                if latest_season:
                    season = latest_season[0]
                    query = query.filter(TeamStat.season == season)

            # Get team stats
            team_stats = query.first()

            if not team_stats:
                return {
                    "valid": False,
                    "message": f"No team stats found for {team}"
                    + (f" in season {season}" if season else ""),
                    "issues": [],
                }

            # Run validations
            issues = []

            # Check if plays matches the sum of pass and rush attempts using safe_float
            pass_attempts = safe_float(team_stats.pass_attempts, 0)
            rush_attempts = safe_float(team_stats.rush_attempts, 0)
            total_plays = pass_attempts + rush_attempts

            if abs(total_plays - safe_float(team_stats.plays, 0)) > 1:  # Allow 1 play difference for rounding
                issues.append(
                    f"Plays mismatch: Total {team_stats.plays} != Pass {team_stats.pass_attempts} + Rush {team_stats.rush_attempts}"
                )

            # Check if pass percentage matches actual ratio with safe_float
            plays = safe_float(team_stats.plays, 1)  # Use 1 as default to avoid division by zero
            if plays > 0:
                expected_pass_pct = pass_attempts / plays
                stored_pct = safe_float(team_stats.pass_percentage, 0)

                if abs(expected_pass_pct - stored_pct) > 0.01:  # Allow 1% difference
                    issues.append(
                        f"Pass percentage mismatch: Stored {stored_pct:.3f} != Calculated {expected_pass_pct:.3f}"
                    )

            # Check if yards per carry matches with safe_float
            if rush_attempts > 0:
                rush_yards = safe_float(team_stats.rush_yards, 0)
                expected_ypc = rush_yards / rush_attempts
                stored_ypc = safe_float(team_stats.rush_yards_per_carry, 0)

                if abs(expected_ypc - stored_ypc) > 0.01:  # Allow 0.01 ypc difference
                    issues.append(
                        f"Rush YPC mismatch: Stored {stored_ypc:.2f} != Calculated {expected_ypc:.2f}"
                    )

            # Check if passing stats match receiving stats using safe_float
            pass_yards = safe_float(team_stats.pass_yards, 0)
            rec_yards = safe_float(team_stats.rec_yards, 0)
            if pass_yards != rec_yards:
                issues.append(
                    f"Pass/Rec yards mismatch: Pass {pass_yards} != Rec {rec_yards}"
                )

            pass_td = safe_float(team_stats.pass_td, 0)
            rec_td = safe_float(team_stats.rec_td, 0)
            if pass_td != rec_td:
                issues.append(
                    f"Pass/Rec TD mismatch: Pass {pass_td} != Rec {rec_td}"
                )

            # Check if targets match pass attempts using safe_float
            targets = safe_float(team_stats.targets, 0)
            if targets != pass_attempts:
                issues.append(
                    f"Targets/Pass attempts mismatch: Targets {targets} != Pass Attempts {pass_attempts}"
                )

            # Check if passing TDs make sense using safe_float
            stored_pass_td_rate = safe_float(team_stats.pass_td_rate, 0)
            calculated_pass_td_rate = pass_td / pass_attempts if pass_attempts > 0 else 0

            if abs(calculated_pass_td_rate - stored_pass_td_rate) > 0.01:
                issues.append(
                    f"Pass TD rate mismatch: Stored {stored_pass_td_rate:.3f} != Calculated {calculated_pass_td_rate:.3f}"
                )

            # Create result using ValidationResultDict TypedDict
            result: ValidationResultDict = {
                "valid": len(issues) == 0,
                "message": "Team stats validation "
                + ("successful" if len(issues) == 0 else "failed"),
                "issues": issues,
                "team_stats": {
                    "team": team_stats.team,
                    "season": team_stats.season,
                    "plays": safe_float(team_stats.plays, 0),
                    "pass_attempts": safe_float(team_stats.pass_attempts, 0),
                    "rush_attempts": safe_float(team_stats.rush_attempts, 0),
                    "pass_yards": safe_float(team_stats.pass_yards, 0),
                    "rush_yards": safe_float(team_stats.rush_yards, 0),
                },
            }
            return result

        except Exception as e:
            # Create error result using ValidationResultDict TypedDict
            error_result: ValidationResultDict = {
                "valid": False,
                "message": f"Error validating team stats: {str(e)}",
                "issues": [str(e)],
                "team_stats": None
            }
            return error_result
            
    async def validate_all_teams(self, season: int) -> Dict[str, ValidationResultDict]:
        """
        Run validation on all teams for a specific season.
        
        Args:
            season: The season to validate
            
        Returns:
            Dict mapping team abbreviations to their validation results
        """
        try:
            # Get all distinct teams in the database
            teams = [
                team[0] 
                for team in self.db.query(Player.team).distinct().all()
                if team[0]  # Filter out None values
            ]
            
            results = {}
            for team in teams:
                # Validate team statistics
                team_stat_result = await self.validate_team_stats(team, season)
                
                # Validate team consistency
                consistency_issues = self.validate_team_consistency(team, season)
                
                # If we have consistency issues, add them to the result
                if consistency_issues:
                    if team_stat_result["valid"]:
                        team_stat_result["valid"] = False
                    
                    team_stat_result["message"] += "; Team consistency validation failed"
                    team_stat_result["issues"].extend(consistency_issues)
                
                results[team] = team_stat_result
                
            return results
        except Exception as e:
            logger.error(f"Error validating all teams for season {season}: {str(e)}")
            return {"ERROR": {
                "valid": False,
                "message": f"Error validating all teams: {str(e)}",
                "issues": [str(e)],
                "team_stats": None
            }}
            
    async def validate_mathematical_consistency(
        self, player_id: str, season: int, scenario_id: Optional[str] = None
    ) -> List[str]:
        """
        Validate mathematical consistency within a player's projection.
        
        Args:
            player_id: The player ID to validate
            season: The season to validate
            scenario_id: Optional scenario ID to filter projections
            
        Returns:
            List of validation issues found
        """
        issues = []
        
        try:
            # Build projection query
            query = (
                self.db.query(Projection)
                .filter(
                    and_(
                        Projection.player_id == player_id,
                        Projection.season == season
                    )
                )
            )
            
            # Add scenario filter if provided
            if scenario_id:
                query = query.filter(Projection.scenario_id == scenario_id)
                
            projection = query.first()
            
            if not projection:
                return [f"No projection found for player {player_id} in season {season}"]
                
            # Get player for position info
            player = self.db.query(Player).filter(Player.player_id == player_id).first()
            
            if not player:
                return [f"Player not found with ID {player_id}"]
                
            # Validate based on position
            if player.position == "QB":
                issues.extend(self._validate_qb_math(projection))
            elif player.position == "RB":
                issues.extend(self._validate_rb_math(projection))
            elif player.position in ["WR", "TE"]:
                issues.extend(self._validate_receiver_math(projection))
                
            # Validate fantasy point calculations
            issues.extend(self._validate_fantasy_points(projection))
            
            return issues
            
        except Exception as e:
            logger.error(f"Error validating mathematical consistency for player {player_id}: {str(e)}")
            return [f"Error validating mathematical consistency: {str(e)}"]
            
    def _validate_qb_math(self, projection: Projection) -> List[str]:
        """Validate mathematical consistency for QB projections."""
        issues = []
        
        # Dictionary to store calculation checks
        checks = []
        
        # Check completion percentage
        if safe_float(projection.pass_attempts, 0) > 0:
            expected_comp_pct = safe_float(projection.completions, 0) / safe_float(projection.pass_attempts, 1) * 100
            actual_comp_pct = safe_float(projection.comp_pct, 0)
            
            checks.append(
                (
                    "Completion percentage", 
                    expected_comp_pct, 
                    actual_comp_pct, 
                    0.1  # Allow 0.1% difference due to rounding
                )
            )
        
        # Check yards per attempt
        if safe_float(projection.pass_attempts, 0) > 0:
            expected_ypa = safe_float(projection.pass_yards, 0) / safe_float(projection.pass_attempts, 1)
            actual_ypa = safe_float(projection.yards_per_att, 0)
            
            checks.append(
                (
                    "Yards per attempt", 
                    expected_ypa, 
                    actual_ypa, 
                    0.01  # Allow 0.01 difference due to rounding
                )
            )
        
        # Check TD rate
        if safe_float(projection.pass_attempts, 0) > 0:
            expected_td_rate = safe_float(projection.pass_td, 0) / safe_float(projection.pass_attempts, 1) * 100
            actual_td_rate = safe_float(projection.pass_td_rate, 0)
            
            checks.append(
                (
                    "Pass TD rate", 
                    expected_td_rate, 
                    actual_td_rate, 
                    0.1  # Allow 0.1% difference due to rounding
                )
            )
        
        # Check INT rate
        if safe_float(projection.pass_attempts, 0) > 0:
            expected_int_rate = safe_float(projection.interceptions, 0) / safe_float(projection.pass_attempts, 1) * 100
            actual_int_rate = safe_float(projection.int_rate, 0)
            
            checks.append(
                (
                    "Interception rate", 
                    expected_int_rate, 
                    actual_int_rate, 
                    0.1  # Allow 0.1% difference due to rounding
                )
            )
        
        # Check yards per completion
        if safe_float(projection.completions, 0) > 0:
            expected_ypc = safe_float(projection.pass_yards, 0) / safe_float(projection.completions, 1)
            actual_ypc = safe_float(projection.yards_per_completion, 0)
            
            checks.append(
                (
                    "Yards per completion", 
                    expected_ypc, 
                    actual_ypc, 
                    0.01  # Allow 0.01 difference due to rounding
                )
            )
            
        # Check rush yards per attempt
        if safe_float(projection.rush_attempts, 0) > 0:
            expected_ypc = safe_float(projection.rush_yards, 0) / safe_float(projection.rush_attempts, 1)
            actual_ypc = safe_float(projection.rush_yards_per_att, 0)
            
            checks.append(
                (
                    "Rush yards per carry", 
                    expected_ypc, 
                    actual_ypc, 
                    0.01  # Allow 0.01 difference due to rounding
                )
            )
        
        # Validate all checks
        for name, expected, actual, tolerance in checks:
            if abs(expected - actual) > tolerance:
                issues.append(
                    f"{name} mismatch: Expected {expected:.2f} but found {actual:.2f}"
                )
                
        return issues
        
    def _validate_rb_math(self, projection: Projection) -> List[str]:
        """Validate mathematical consistency for RB projections."""
        issues = []
        
        # Dictionary to store calculation checks
        checks = []
        
        # Check rush yards per attempt
        if safe_float(projection.rush_attempts, 0) > 0:
            expected_ypc = safe_float(projection.rush_yards, 0) / safe_float(projection.rush_attempts, 1)
            actual_ypc = safe_float(projection.rush_yards_per_att, 0)
            
            checks.append(
                (
                    "Rush yards per carry", 
                    expected_ypc, 
                    actual_ypc, 
                    0.01  # Allow 0.01 difference due to rounding
                )
            )
        
        # Check receiving yards per reception
        if safe_float(projection.receptions, 0) > 0:
            expected_ypr = safe_float(projection.rec_yards, 0) / safe_float(projection.receptions, 1)
            actual_ypr = safe_float(projection.yards_per_reception, 0)
            
            checks.append(
                (
                    "Yards per reception", 
                    expected_ypr, 
                    actual_ypr, 
                    0.01  # Allow 0.01 difference due to rounding
                )
            )
        
        # Check catch rate
        if safe_float(projection.targets, 0) > 0:
            expected_catch_rate = safe_float(projection.receptions, 0) / safe_float(projection.targets, 1) * 100
            actual_catch_rate = safe_float(projection.catch_rate, 0)
            
            checks.append(
                (
                    "Catch rate", 
                    expected_catch_rate, 
                    actual_catch_rate, 
                    0.1  # Allow 0.1% difference due to rounding
                )
            )
        
        # Check rush TD rate
        if safe_float(projection.rush_attempts, 0) > 0:
            expected_td_rate = safe_float(projection.rush_td, 0) / safe_float(projection.rush_attempts, 1) * 100
            actual_td_rate = safe_float(projection.rush_td_rate, 0)
            
            checks.append(
                (
                    "Rush TD rate", 
                    expected_td_rate, 
                    actual_td_rate, 
                    0.1  # Allow 0.1% difference due to rounding
                )
            )
        
        # Validate all checks
        for name, expected, actual, tolerance in checks:
            if abs(expected - actual) > tolerance:
                issues.append(
                    f"{name} mismatch: Expected {expected:.2f} but found {actual:.2f}"
                )
                
        return issues
        
    def _validate_receiver_math(self, projection: Projection) -> List[str]:
        """Validate mathematical consistency for WR/TE projections."""
        issues = []
        
        # Dictionary to store calculation checks
        checks = []
        
        # Check receiving yards per reception
        if safe_float(projection.receptions, 0) > 0:
            expected_ypr = safe_float(projection.rec_yards, 0) / safe_float(projection.receptions, 1)
            actual_ypr = safe_float(projection.yards_per_reception, 0)
            
            checks.append(
                (
                    "Yards per reception", 
                    expected_ypr, 
                    actual_ypr, 
                    0.01  # Allow 0.01 difference due to rounding
                )
            )
        
        # Check catch rate
        if safe_float(projection.targets, 0) > 0:
            expected_catch_rate = safe_float(projection.receptions, 0) / safe_float(projection.targets, 1) * 100
            actual_catch_rate = safe_float(projection.catch_rate, 0)
            
            checks.append(
                (
                    "Catch rate", 
                    expected_catch_rate, 
                    actual_catch_rate, 
                    0.1  # Allow 0.1% difference due to rounding
                )
            )
        
        # Check TD rate (per reception)
        if safe_float(projection.receptions, 0) > 0:
            expected_td_rate = safe_float(projection.rec_td, 0) / safe_float(projection.receptions, 1) * 100
            actual_td_rate = safe_float(projection.rec_td_rate, 0)
            
            checks.append(
                (
                    "Receiving TD rate", 
                    expected_td_rate, 
                    actual_td_rate, 
                    0.1  # Allow 0.1% difference due to rounding
                )
            )
        
        # Check yards per target
        if safe_float(projection.targets, 0) > 0:
            expected_ypt = safe_float(projection.rec_yards, 0) / safe_float(projection.targets, 1)
            actual_ypt = safe_float(projection.yards_per_target, 0)
            
            checks.append(
                (
                    "Yards per target", 
                    expected_ypt, 
                    actual_ypt, 
                    0.01  # Allow 0.01 difference due to rounding
                )
            )
        
        # Validate all checks
        for name, expected, actual, tolerance in checks:
            if abs(expected - actual) > tolerance:
                issues.append(
                    f"{name} mismatch: Expected {expected:.2f} but found {actual:.2f}"
                )
                
        return issues
        
    def _validate_fantasy_points(self, projection: Projection) -> List[str]:
        """Validate fantasy point calculations."""
        issues = []
        
        # Calculate expected PPR fantasy points
        expected_ppr = 0
        expected_ppr += safe_float(projection.pass_yards, 0) * 0.04  # 0.04 points per passing yard
        expected_ppr += safe_float(projection.pass_td, 0) * 4  # 4 points per passing TD
        expected_ppr -= safe_float(projection.interceptions, 0) * 2  # -2 points per INT
        expected_ppr += safe_float(projection.rush_yards, 0) * 0.1  # 0.1 points per rushing yard
        expected_ppr += safe_float(projection.rush_td, 0) * 6  # 6 points per rushing TD
        expected_ppr += safe_float(projection.receptions, 0) * 1  # 1 point per reception (PPR)
        expected_ppr += safe_float(projection.rec_yards, 0) * 0.1  # 0.1 points per receiving yard
        expected_ppr += safe_float(projection.rec_td, 0) * 6  # 6 points per receiving TD
        expected_ppr -= safe_float(projection.fumbles_lost, 0) * 2  # -2 points per fumble lost
        
        # Check PPR points
        actual_ppr = safe_float(projection.ppr, 0)
        if abs(expected_ppr - actual_ppr) > 0.1:  # Allow 0.1 point difference due to rounding
            issues.append(
                f"PPR points mismatch: Expected {expected_ppr:.1f} but found {actual_ppr:.1f}"
            )
        
        # Calculate expected half PPR points
        expected_half_ppr = expected_ppr - (safe_float(projection.receptions, 0) * 0.5)  # Remove 0.5 points per reception
        
        # Check half PPR points
        actual_half_ppr = safe_float(projection.half_ppr, 0)
        if abs(expected_half_ppr - actual_half_ppr) > 0.1:  # Allow 0.1 point difference due to rounding
            issues.append(
                f"Half PPR points mismatch: Expected {expected_half_ppr:.1f} but found {actual_half_ppr:.1f}"
            )
        
        # Calculate expected standard points
        expected_standard = expected_ppr - safe_float(projection.receptions, 0)  # Remove all reception points
        
        # Check standard points
        actual_standard = safe_float(projection.standard, 0)
        if abs(expected_standard - actual_standard) > 0.1:  # Allow 0.1 point difference due to rounding
            issues.append(
                f"Standard points mismatch: Expected {expected_standard:.1f} but found {actual_standard:.1f}"
            )
            
        return issues
        
    async def batch_validate_projections(
        self, season: int, scenario_id: Optional[str] = None, position: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Validate mathematical consistency for a batch of projections.
        
        Args:
            season: The season to validate
            scenario_id: Optional scenario ID to filter projections
            position: Optional position to filter (QB, RB, WR, TE)
            
        Returns:
            Dictionary mapping player IDs to validation results
        """
        results = {}
        
        try:
            # Build the query to get all players with projections
            query = (
                self.db.query(Player)
                .join(
                    Projection,
                    and_(
                        Player.player_id == Projection.player_id,
                        Projection.season == season
                    )
                )
            )
            
            # Add filters if provided
            if scenario_id:
                query = query.filter(Projection.scenario_id == scenario_id)
                
            if position:
                query = query.filter(Player.position == position)
                
            players = query.all()
            
            # Validate each player's projections
            for player in players:
                issues = await self.validate_mathematical_consistency(
                    player.player_id, season, scenario_id
                )
                
                # Store the result
                results[player.player_id] = {
                    "name": player.name,
                    "position": player.position,
                    "team": player.team,
                    "valid": len(issues) == 0,
                    "issues": issues
                }
                
            return results
            
        except Exception as e:
            logger.error(f"Error batch validating projections for season {season}: {str(e)}")
            return {"ERROR": {
                "name": "Error",
                "position": None,
                "team": None,
                "valid": False,
                "issues": [f"Error batch validating projections: {str(e)}"]
            }}
