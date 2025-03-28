from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_
from backend.database.models import TeamStat
import logging

logger = logging.getLogger(__name__)

class TeamStatsService:
    """
    Service for managing and validating team-level statistics.
    Handles team stat retrieval, validation, and consistency checks.
    """
    def __init__(self, db: Session):
        self.db = db
        
        # Mapping from PFR column names to our database columns
        self.pfr_mapping = {
            'Tm': 'team',
            'PaATT': 'pass_attempts',
            'PaYD': 'pass_yards',
            'PaTD': 'pass_td',
            'RuATT': 'rush_attempts',
            'RuYD': 'rush_yards',
            'RuTD': 'rush_td',
            'Car': 'carries',
            'YPC': 'rush_yards_per_carry',
            'Tar': 'targets',
            'Rec': 'receptions',
            'ReYD': 'rec_yards',
            'ReTD': 'rec_td',
            'Pass %': 'pass_percentage',
            'TD%': 'pass_td_rate'
        }
    
    async def get_team_stats(self, team: str, season: int) -> Optional[TeamStat]:
        """Get team stats for a specific team and season."""
        return self.db.query(TeamStat).filter(
            and_(TeamStat.team == team, TeamStat.season == season)
        ).first()

    async def get_all_team_stats(self, season: int) -> List[TeamStat]:
        """Get stats for all teams in a season."""
        return self.db.query(TeamStat).filter(TeamStat.season == season).all()

    async def validate_team_stats(self, team_stat: TeamStat) -> Tuple[bool, List[str]]:
        """
        Validate team stats for mathematical consistency.
        Returns (is_valid, list of validation messages)
        """
        validation_messages = []
        
        try:
            # Validate play totals
            total_plays = team_stat.pass_attempts + team_stat.rush_attempts
            if abs(total_plays - team_stat.plays) > 0.01:
                msg = (f"Play count mismatch: {total_plays} total vs {team_stat.plays} recorded "
                      f"(Pass: {team_stat.pass_attempts}, Rush: {team_stat.rush_attempts})")
                validation_messages.append(msg)
                
            # Validate pass percentage matches PFR calculation
            expected_pass_pct = team_stat.pass_attempts / team_stat.plays
            if abs(team_stat.pass_percentage - expected_pass_pct) > 0.001:
                msg = (f"Pass percentage mismatch: {expected_pass_pct:.3f} calculated vs "
                      f"{team_stat.pass_percentage:.3f} recorded")
                validation_messages.append(msg)
                
            # Validate yards per carry matches PFR calculation
            if team_stat.carries > 0:
                expected_ypc = team_stat.rush_yards / team_stat.carries
                if abs(team_stat.rush_yards_per_carry - expected_ypc) > 0.001:
                    msg = (f"YPC mismatch: {expected_ypc:.2f} calculated vs "
                          f"{team_stat.rush_yards_per_carry:.2f} recorded")
                    validation_messages.append(msg)
                    
            # Validate pass/receive yards match (PFR requirement)
            if abs(team_stat.pass_yards - team_stat.rec_yards) > 0.01:
                msg = (f"Pass/receive yards mismatch: {team_stat.pass_yards} pass vs "
                      f"{team_stat.rec_yards} receive")
                validation_messages.append(msg)
                
            # Validate pass/receive TDs match (PFR requirement)
            if team_stat.pass_td != team_stat.rec_td:
                msg = (f"Pass/receive TD mismatch: {team_stat.pass_td} pass vs "
                      f"{team_stat.rec_td} receive")
                validation_messages.append(msg)
                
            # Validate targets match attempts (PFR standard)
            if team_stat.targets != team_stat.pass_attempts:
                msg = (f"Targets/attempts mismatch: {team_stat.targets} targets vs "
                      f"{team_stat.pass_attempts} attempts")
                validation_messages.append(msg)
            
            return len(validation_messages) == 0, validation_messages
            
        except Exception as e:
            logger.error(f"Error validating team stats: {str(e)}")
            return False, [f"Validation error: {str(e)}"]

    def convert_pfr_stats(self, pfr_data: Dict) -> Dict:
        """Convert PFR column names to our database column names."""
        converted = {}
        for pfr_name, value in pfr_data.items():
            if pfr_name in self.pfr_mapping:
                db_name = self.pfr_mapping[pfr_name]
                converted[db_name] = value
        return converted

    async def update_team_stats(self, 
                              team: str, 
                              season: int, 
                              stats: Dict[str, float],
                              is_pfr_format: bool = False) -> Optional[TeamStat]:
        """
        Update team statistics while maintaining consistency.
        
        Args:
            team: Team abbreviation
            season: Season year
            stats: Dictionary of stats to update
            is_pfr_format: Whether the stats are in PFR column format
        """
        try:
            # Convert PFR column names if necessary
            stats_to_update = self.convert_pfr_stats(stats) if is_pfr_format else stats
            
            team_stat = await self.get_team_stats(team, season)
            if not team_stat:
                return None
                
            # Update stats
            for key, value in stats_to_update.items():
                if hasattr(team_stat, key):
                    setattr(team_stat, key, value)
                    
            # Validate after updates
            is_valid, messages = await self.validate_team_stats(team_stat)
            if not is_valid:
                logger.error(f"Invalid team stat update: {messages}")
                self.db.rollback()
                return None
                
            self.db.commit()
            return team_stat
            
        except Exception as e:
            logger.error(f"Error updating team stats: {str(e)}")
            self.db.rollback()
            return None

    async def calculate_derived_stats(self, team_stat: TeamStat) -> Dict[str, float]:
        """Calculate additional statistical metrics from base team stats."""
        try:
            derived_stats = {}
            
            # Passing efficiency metrics (using PFR calculation methods)
            if team_stat.pass_attempts > 0:
                derived_stats['completion_rate'] = team_stat.receptions / team_stat.pass_attempts
                derived_stats['yards_per_attempt'] = team_stat.pass_yards / team_stat.pass_attempts
                derived_stats['yards_per_completion'] = (
                    team_stat.pass_yards / team_stat.receptions if team_stat.receptions > 0 else 0
                )
                
            # Rushing efficiency metrics (using PFR calculation methods)
            if team_stat.rush_attempts > 0:
                derived_stats['yards_per_rush'] = team_stat.rush_yards / team_stat.rush_attempts
                
            # Scoring efficiency
            if team_stat.plays > 0:
                derived_stats['points_per_play'] = (
                    (team_stat.pass_td * 6 + team_stat.rush_td * 6) / team_stat.plays
                )
                
            return derived_stats
            
        except Exception as e:
            logger.error(f"Error calculating derived stats: {str(e)}")
            return {}