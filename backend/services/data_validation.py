import logging
import pandas as pd
from typing import Dict, List, Optional, Set, Tuple, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError

from backend.database.models import Player, BaseStat, GameStats, TeamStat

logger = logging.getLogger(__name__)

class DataValidationService:
    """Service for validating and fixing inconsistencies in imported data."""
    
    def __init__(self, db: Session):
        self.db = db
        # Define the minimum stats that should exist for each position
        self.required_stats = {
            'QB': {'games', 'completions', 'pass_attempts', 'pass_yards', 'pass_td', 'interceptions', 'rush_attempts', 'rush_yards', 'rush_td'},
            'RB': {'games', 'rush_attempts', 'rush_yards', 'rush_td', 'targets', 'receptions', 'rec_yards', 'rec_td'},
            'WR': {'games', 'targets', 'receptions', 'rec_yards', 'rec_td', 'rush_attempts', 'rush_yards', 'rush_td'},
            'TE': {'games', 'targets', 'receptions', 'rec_yards', 'rec_td'}
        }
        
    def validate_player_data(
        self, 
        player: Player, 
        season: int
    ) -> List[str]:
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
        game_stats = self.db.query(GameStats).filter(
            and_(
                GameStats.player_id == player.player_id,
                GameStats.season == season
            )
        ).all()
        
        # Get games count stat
        games_stat = self.db.query(BaseStat).filter(
            and_(
                BaseStat.player_id == player.player_id,
                BaseStat.season == season,
                BaseStat.stat_type == "games"
            )
        ).first()
        
        if not game_stats and not games_stat:
            # No data for this season
            return []
            
        game_count = len(game_stats)
        
        if not games_stat:
            issues.append(f"Player {player.name} has {game_count} game logs but no games count stat")
            self._fix_games_count(player, season, game_count)
        elif game_count != int(games_stat.value):
            issues.append(f"Player {player.name} has {game_count} game logs but games stat is {int(games_stat.value)}")
            self._fix_games_count(player, season, game_count)
            
        return issues
    
    def _verify_season_totals(self, player: Player, season: int) -> List[str]:
        """Verify that season totals match the sum of game logs."""
        issues = []
        
        # Get game logs
        game_stats = self.db.query(GameStats).filter(
            and_(
                GameStats.player_id == player.player_id,
                GameStats.season == season
            )
        ).all()
        
        if not game_stats:
            return []
            
        # Get base stats
        base_stats = self.db.query(BaseStat).filter(
            and_(
                BaseStat.player_id == player.player_id,
                BaseStat.season == season,
                BaseStat.stat_type != "games"  # Exclude games count
            )
        ).all()
        
        # Convert to dictionary
        base_stat_dict = {stat.stat_type: stat.value for stat in base_stats}
        
        # Define stat mapping (similar to the mappings in NFLDataImportService)
        stat_mappings = {
            'QB': {
                'completions': 'cmp',
                'pass_attempts': 'att',
                'pass_yards': 'pass_yds',
                'pass_td': 'pass_td',
                'interceptions': 'int',
                'rush_attempts': 'rush_att',
                'rush_yards': 'rush_yds',
                'rush_td': 'rush_td',
                'sacks': 'sacked'
            },
            'RB': {
                'rush_attempts': 'rush_att',
                'rush_yards': 'rush_yds',
                'rush_td': 'rush_td',
                'targets': 'tgt',
                'receptions': 'rec',
                'rec_yards': 'rec_yds',
                'rec_td': 'rec_td'
            },
            'WR': {
                'targets': 'tgt',
                'receptions': 'rec',
                'rec_yards': 'rec_yds',
                'rec_td': 'rec_td',
                'rush_attempts': 'rush_att',
                'rush_yards': 'rush_yds',
                'rush_td': 'rush_td'
            },
            'TE': {
                'targets': 'tgt',
                'receptions': 'rec',
                'rec_yards': 'rec_yds',
                'rec_td': 'rec_td'
            }
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
                        issues.append(f"Player {player.name} has invalid value for {nfl_data_name} in game {game.week}")
                        continue
            
            calculated_totals[stat_name] = total
            
            # Compare with stored values
            if stat_name in base_stat_dict:
                stored_value = base_stat_dict[stat_name]
                # Allow small rounding differences (0.1%)
                if total > 0 and abs(stored_value - total) / total > 0.001:
                    issues.append(f"Player {player.name} has inconsistent {stat_name}: stored={stored_value}, calculated={total}")
                    # Fix the inconsistency
                    self._fix_stat_value(player, season, stat_name, total)
            else:
                # Missing stat that should exist
                issues.append(f"Player {player.name} is missing {stat_name} stat")
                self._add_missing_stat(player, season, stat_name, total)
                
        return issues
    
    def _check_missing_stats(self, player: Player, season: int) -> List[str]:
        """Check if any required stats are missing."""
        issues = []
        
        # Get all base stats for this player and season
        base_stats = self.db.query(BaseStat).filter(
            and_(
                BaseStat.player_id == player.player_id,
                BaseStat.season == season
            )
        ).all()
        
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
            games_stat = self.db.query(BaseStat).filter(
                and_(
                    BaseStat.player_id == player.player_id,
                    BaseStat.season == season,
                    BaseStat.stat_type == "games"
                )
            ).first()
            
            if games_stat:
                games_stat.value = float(game_count)
            else:
                games_stat = BaseStat(
                    player_id=player.player_id,
                    season=season,
                    stat_type="games",
                    value=float(game_count)
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
            stat = self.db.query(BaseStat).filter(
                and_(
                    BaseStat.player_id == player.player_id,
                    BaseStat.season == season,
                    BaseStat.stat_type == stat_type
                )
            ).first()
            
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
                player_id=player.player_id,
                season=season,
                stat_type=stat_type,
                value=value
            )
            self.db.add(new_stat)
            self.db.flush()
            logger.info(f"Added missing {stat_type} for {player.name}: {value}")
        except SQLAlchemyError as e:
            logger.error(f"Error adding {stat_type} for {player.name}: {str(e)}")
            self.db.rollback()
            
    def validate_team_consistency(self, season: int) -> List[str]:
        """Validate that team-level stats are consistent with player stats."""
        # This would aggregate player stats by team and compare with team stats
        # Implementation depends on how team stats are stored and calculated
        # Reserved for future enhancement
        return []
        
    async def validate_team_stats(self, team: str, season: Optional[int] = None) -> Dict[str, Any]:
        """
        Validate team statistics for consistency.
        
        Args:
            team: The team abbreviation to validate
            season: Optional season to filter by, if not provided uses the latest season
            
        Returns:
            Dict with validation results
        """
        try:
            # Build query for team stats
            query = self.db.query(TeamStat).filter(TeamStat.team == team)
            
            if season:
                query = query.filter(TeamStat.season == season)
            else:
                # Use the latest season if not specified
                latest_season = self.db.query(TeamStat.season).order_by(TeamStat.season.desc()).first()
                if latest_season:
                    season = latest_season[0]
                    query = query.filter(TeamStat.season == season)
            
            # Get team stats
            team_stats = query.first()
            
            if not team_stats:
                return {
                    "valid": False,
                    "message": f"No team stats found for {team}" + (f" in season {season}" if season else ""),
                    "issues": []
                }
            
            # Run validations
            issues = []
            
            # Check if plays matches the sum of pass and rush attempts
            total_plays = team_stats.pass_attempts + team_stats.rush_attempts
            if abs(total_plays - team_stats.plays) > 1:  # Allow 1 play difference for rounding
                issues.append(f"Plays mismatch: Total {team_stats.plays} != Pass {team_stats.pass_attempts} + Rush {team_stats.rush_attempts}")
                
            # Check if pass percentage matches actual ratio
            if team_stats.plays > 0:
                expected_pass_pct = team_stats.pass_attempts / team_stats.plays
                if abs(expected_pass_pct - team_stats.pass_percentage) > 0.01:  # Allow 1% difference
                    issues.append(f"Pass percentage mismatch: Stored {team_stats.pass_percentage:.3f} != Calculated {expected_pass_pct:.3f}")
                    
            # Check if yards per carry matches
            if team_stats.rush_attempts > 0:
                expected_ypc = team_stats.rush_yards / team_stats.rush_attempts
                if abs(expected_ypc - team_stats.rush_yards_per_carry) > 0.01:  # Allow 0.01 ypc difference
                    issues.append(f"Rush YPC mismatch: Stored {team_stats.rush_yards_per_carry:.2f} != Calculated {expected_ypc:.2f}")
                    
            # Check if passing stats match receiving stats
            if team_stats.pass_yards != team_stats.rec_yards:
                issues.append(f"Pass/Rec yards mismatch: Pass {team_stats.pass_yards} != Rec {team_stats.rec_yards}")
                
            if team_stats.pass_td != team_stats.rec_td:
                issues.append(f"Pass/Rec TD mismatch: Pass {team_stats.pass_td} != Rec {team_stats.rec_td}")
                
            # Check if targets match pass attempts
            if team_stats.targets != team_stats.pass_attempts:
                issues.append(f"Targets/Pass attempts mismatch: Targets {team_stats.targets} != Pass Attempts {team_stats.pass_attempts}")
            
            # Check if passing TDs make sense
            pass_td_rate = team_stats.pass_td / team_stats.pass_attempts if team_stats.pass_attempts > 0 else 0
            if abs(pass_td_rate - team_stats.pass_td_rate) > 0.01:
                issues.append(f"Pass TD rate mismatch: Stored {team_stats.pass_td_rate:.3f} != Calculated {pass_td_rate:.3f}")
            
            return {
                "valid": len(issues) == 0,
                "message": "Team stats validation " + ("successful" if len(issues) == 0 else "failed"),
                "issues": issues,
                "team_stats": {
                    "team": team_stats.team,
                    "season": team_stats.season,
                    "plays": team_stats.plays,
                    "pass_attempts": team_stats.pass_attempts,
                    "rush_attempts": team_stats.rush_attempts,
                    "pass_yards": team_stats.pass_yards,
                    "rush_yards": team_stats.rush_yards
                }
            }
            
        except Exception as e:
            return {
                "valid": False,
                "message": f"Error validating team stats: {str(e)}",
                "issues": [str(e)]
            }