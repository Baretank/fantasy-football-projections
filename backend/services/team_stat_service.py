from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from backend.database.models import TeamStat, Player, BaseStat
import logging

logger = logging.getLogger(__name__)

class TeamStatsService:
    def __init__(self, db: Session):
        self.db = db

    async def calculate_team_stats(self, team: str, season: int) -> Optional[TeamStat]:
        """Calculate team stats from player data."""
        try:
            # Get all players for team
            players = self.db.query(Player).filter(Player.team == team).all()
            
            # Initialize counters
            stats = {
                'plays': 0,
                'pass_attempts': 0,
                'pass_yards': 0,
                'pass_td': 0,
                'rush_attempts': 0,
                'rush_yards': 0,
                'rush_td': 0,
                'targets': 0,
                'receptions': 0,
                'rec_yards': 0,
                'rec_td': 0
            }

            # Aggregate player stats
            for player in players:
                player_stats = self.db.query(BaseStat).filter(
                    BaseStat.player_id == player.player_id,
                    BaseStat.season == season
                ).all()
                
                for stat in player_stats:
                    if stat.stat_type in stats:
                        stats[stat.stat_type] += stat.value

            # Calculate derived stats
            if stats['pass_attempts'] + stats['rush_attempts'] > 0:
                stats['pass_percentage'] = (
                    stats['pass_attempts'] / 
                    (stats['pass_attempts'] + stats['rush_attempts'])
                )
            
            # Create team stat record
            team_stat = TeamStat(
                team=team,
                season=season,
                **stats
            )
            
            self.db.add(team_stat)
            self.db.commit()
            
            return team_stat

        except Exception as e:
            logger.error(f"Error calculating team stats for {team}: {str(e)}")
            self.db.rollback()
            return None

    async def get_team_stats(self, team: str, season: int) -> Optional[Dict]:
        """Get team stats with additional derived metrics."""
        try:
            team_stat = self.db.query(TeamStat).filter(
                TeamStat.team == team,
                TeamStat.season == season
            ).first()
            
            if not team_stat:
                return None

            # Calculate additional metrics
            metrics = {
                'team': team_stat.team,
                'season': team_stat.season,
                'plays_per_game': team_stat.plays / 17,
                'pass_plays_per_game': team_stat.pass_attempts / 17,
                'rush_plays_per_game': team_stat.rush_attempts / 17,
                'points_per_game': (team_stat.pass_td * 6 + team_stat.rush_td * 6) / 17,
                'yards_per_game': (team_stat.pass_yards + team_stat.rush_yards) / 17
            }

            return metrics

        except Exception as e:
            logger.error(f"Error getting team stats for {team}: {str(e)}")
            return None