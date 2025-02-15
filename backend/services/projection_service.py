from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_
from backend.database.models import Player, BaseStat, Projection, TeamStat, Scenario
from .data_service import DataService
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

class ProjectionService:
    """
    Service for managing and calculating player projections.
    Handles projection creation, updates, and scenario management.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.data_service = DataService(db)
        
        # Validation ranges for adjustments
        self.adjustment_ranges = {
            'snap_share': (0.0, 1.0),
            'target_share': (0.0, 0.5),  # Max 50% of team targets
            'rush_share': (0.0, 0.8),    # Max 80% of team rushes
            'td_rate': (0.5, 2.0)        # Can halve or double TD rate
        }

    async def get_projection(self, projection_id: str) -> Optional[Projection]:
        """Retrieve a specific projection."""
        return self.db.query(Projection).filter(
            Projection.projection_id == projection_id
        ).first()

    async def get_player_projections(self, 
                                   player_id: str,
                                   scenario_id: Optional[str] = None) -> List[Projection]:
        """Retrieve projections for a player."""
        query = self.db.query(Projection).filter(Projection.player_id == player_id)
        
        if scenario_id:
            query = query.filter(Projection.scenario_id == scenario_id)
            
        return query.all()

    async def create_base_projection(self, 
                                   player_id: str,
                                   season: int) -> Optional[Projection]:
        """Create baseline projection from historical data."""
        try:
            # Get player and their historical stats
            player = self.db.query(Player).get(player_id)
            if not player:
                logger.error(f"Player {player_id} not found")
                return None
                
            # Get team stats for context
            team_stats = self.db.query(TeamStat).filter(
                and_(TeamStat.team == player.team, 
                     TeamStat.season == season)
            ).first()
            
            if not team_stats:
                logger.error(f"Team stats not found for {player.team} in {season}")
                return None
                
            # Get historical stats from previous season
            base_stats = self.db.query(BaseStat).filter(
                and_(BaseStat.player_id == player_id,
                     BaseStat.season == season - 1)
            ).all()
            
            # Calculate baseline projection
            projection = await self._calculate_base_projection(
                player, team_stats, base_stats, season
            )
            
            if projection:
                self.db.add(projection)
                self.db.commit()
                
            return projection
            
        except Exception as e:
            logger.error(f"Error creating base projection: {str(e)}")
            self.db.rollback()
            return None

    async def update_projection(self, 
                              projection_id: str,
                              adjustments: Dict[str, float]) -> Optional[Projection]:
        """Update an existing projection with adjustments."""
        try:
            projection = await self.get_projection(projection_id)
            if not projection:
                return None
                
            # Validate adjustments
            if not await self.validate_adjustments(projection.player_id, adjustments):
                logger.error("Invalid adjustments provided")
                return None
                
            # Get team context
            team_stats = self.db.query(TeamStat).filter(
                and_(TeamStat.team == projection.player.team,
                     TeamStat.season == projection.season)
            ).first()
            
            # Apply adjustments based on position
            if projection.player.position == 'QB':
                await self._adjust_qb_stats(projection, team_stats, adjustments)
            elif projection.player.position == 'RB':
                await self._adjust_rb_stats(projection, team_stats, adjustments)
            else:  # WR/TE
                await self._adjust_receiver_stats(projection, team_stats, adjustments)
                
            # Recalculate fantasy points
            projection.half_ppr = projection.calculate_fantasy_points()
            projection.updated_at = datetime.utcnow()
            
            self.db.commit()
            return projection
            
        except Exception as e:
            logger.error(f"Error updating projection: {str(e)}")
            self.db.rollback()
            return None

    async def validate_adjustments(self, 
                                 player_id: str,
                                 adjustments: Dict[str, float]) -> bool:
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
            logger.error(f"Error validating adjustments: {str(e)}")
            return False

    async def create_scenario(self, 
                            name: str,
                            description: Optional[str] = None,
                            base_scenario_id: Optional[str] = None) -> Optional[str]:
        """Create a new projection scenario."""
        try:
            scenario = Scenario(
                scenario_id=str(uuid.uuid4()),
                name=name,
                description=description,
                base_scenario_id=base_scenario_id
            )
            
            self.db.add(scenario)
            self.db.commit()
            
            return scenario.scenario_id
            
        except Exception as e:
            logger.error(f"Error creating scenario: {str(e)}")
            self.db.rollback()
            return None

    async def apply_team_adjustments(self, 
                                   team: str,
                                   season: int,
                                   adjustments: Dict[str, float]) -> List[Projection]:
        """Apply adjustments at team level and update affected players."""
        try:
            # Get all players for the team
            players = self.db.query(Player).filter(Player.team == team).all()
            
            # Get team stats
            team_stats = self.db.query(TeamStat).filter(
                and_(TeamStat.team == team,
                     TeamStat.season == season)
            ).first()
            
            if not team_stats:
                logger.error(f"Team stats not found for {team}")
                return []
                
            updated_projections = []
            
            # Update projections for each player
            for player in players:
                projections = await self.get_player_projections(player.player_id)
                
                for proj in projections:
                    # Adjust projection based on team-level changes
                    updated_proj = await self._apply_team_adjustment(
                        proj, team_stats, adjustments
                    )
                    if updated_proj:
                        updated_projections.append(updated_proj)
                        
            self.db.commit()
            return updated_projections
            
        except Exception as e:
            logger.error(f"Error applying team adjustments: {str(e)}")
            self.db.rollback()
            return []

    async def get_projection_trends(self, 
                                  player_id: str,
                                  stat_type: str,
                                  weeks: int = 8) -> List[Dict]:
        """Get historical projection trends for analysis."""
        try:
            # Get base stats for specified period
            base_stats = self.db.query(BaseStat).filter(
                and_(BaseStat.player_id == player_id,
                     BaseStat.stat_type == stat_type)
            ).order_by(
                BaseStat.season.desc(),
                BaseStat.week.desc()
            ).limit(weeks).all()
            
            # Format trend data
            trends = []
            for stat in base_stats:
                trends.append({
                    'season': stat.season,
                    'week': stat.week,
                    'value': stat.value
                })
                
            return trends
            
        except Exception as e:
            logger.error(f"Error getting projection trends: {str(e)}")
            return []

    async def _calculate_base_projection(self,
                                       player: Player,
                                       team_stats: TeamStat,
                                       base_stats: List[BaseStat],
                                       season: int) -> Optional[Projection]:
        """Calculate baseline projection from historical data."""
        try:
            # Convert base stats to dictionary for easier access
            stats_dict = {
                stat.stat_type: stat.value 
                for stat in base_stats
            }
            
            # Create base projection
            projection = Projection(
                projection_id=str(uuid.uuid4()),
                player_id=player.player_id,
                season=season,
                games=17  # Full season
            )
            
            # Set position-specific stats
            if player.position == 'QB':
                self._set_qb_stats(projection, stats_dict, team_stats)
            elif player.position == 'RB':
                self._set_rb_stats(projection, stats_dict, team_stats)
            else:  # WR/TE
                self._set_receiver_stats(projection, stats_dict, team_stats)
                
            # Calculate fantasy points
            projection.half_ppr = projection.calculate_fantasy_points()
            
            return projection
            
        except Exception as e:
            logger.error(f"Error calculating base projection: {str(e)}")
            return None

    # Helper methods for position-specific stat calculations
    async def _adjust_qb_stats(self, 
                              projection: Projection,
                              team_stats: TeamStat,
                              adjustments: Dict[str, float]) -> None:
        """Adjust QB-specific statistics."""
        if 'pass_volume' in adjustments:
            factor = adjustments['pass_volume']
            projection.pass_attempts *= factor
            projection.completions *= factor
            projection.pass_yards *= factor
            
        if 'td_rate' in adjustments:
            projection.pass_td *= adjustments['td_rate']
            
        if 'int_rate' in adjustments:
            projection.interceptions *= adjustments['int_rate']
            
        if 'rush_share' in adjustments:
            factor = adjustments['rush_share']
            projection.carries *= factor
            projection.rush_yards *= factor
            projection.rush_td *= factor

    async def _adjust_rb_stats(self,
                              projection: Projection,
                              team_stats: TeamStat,
                              adjustments: Dict[str, float]) -> None:
        """Adjust RB-specific statistics."""
        if 'rush_share' in adjustments:
            factor = adjustments['rush_share']
            projection.carries *= factor
            projection.rush_yards *= factor
            projection.rush_td *= factor
            
        if 'target_share' in adjustments:
            factor = adjustments['target_share']
            projection.targets *= factor
            projection.receptions *= (factor * 0.95)  # Slight reduction in catch rate
            projection.rec_yards *= factor
            projection.rec_td *= factor

    async def _adjust_receiver_stats(self,
                                   projection: Projection,
                                   team_stats: TeamStat,
                                   adjustments: Dict[str, float]) -> None:
        """Adjust WR/TE-specific statistics."""
        if 'target_share' in adjustments:
            factor = adjustments['target_share']
            projection.targets *= factor
            projection.receptions *= (factor * 0.95)
            projection.rec_yards *= factor
            projection.rec_td *= factor
            
        if 'snap_share' in adjustments:
            factor = adjustments['snap_share']
            projection.snap_share = min(1.0, projection.snap_share * factor)

    async def _apply_team_adjustment(self,
                                   projection: Projection,
                                   team_stats: TeamStat,
                                   adjustments: Dict[str, float]) -> Optional[Projection]:
        """Apply team-level adjustments to individual projection."""
        try:
            # Adjust based on team-level changes
            if 'pass_volume' in adjustments and projection.player.position == 'QB':
                factor = adjustments['pass_volume']
                projection.pass_attempts *= factor
                projection.completions *= factor
                projection.pass_yards *= factor
                
            if 'rush_volume' in adjustments:
                factor = adjustments['rush_volume']
                if projection.carries is not None:
                    projection.carries *= factor
                    projection.rush_yards *= factor
                    
            if 'scoring_rate' in adjustments:
                factor = adjustments['scoring_rate']
                if projection.pass_td is not None:
                    projection.pass_td *= factor
                if projection.rush_td is not None:
                    projection.rush_td *= factor
                if projection.rec_td is not None:
                    projection.rec_td *= factor
                    
            # Recalculate fantasy points
            projection.half_ppr = projection.calculate_fantasy_points()
            projection.updated_at = datetime.utcnow()
            
            return projection
            
        except Exception as e:
            logger.error(f"Error applying team adjustment: {str(e)}")
            return None