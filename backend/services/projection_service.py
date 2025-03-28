from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
import uuid
import logging

from backend.database.models import Player, BaseStat, Projection, TeamStat, Scenario

logger = logging.getLogger(__name__)

class ProjectionError(Exception):
    """Base exception for projection-related errors."""
    pass

class ProjectionService:
    def __init__(self, db: Session):
        self.db = db
        self.adjustment_ranges = {
            'snap_share': (0.1, 1.0),
            'target_share': (0.0, 0.5),
            'rush_share': (0.0, 0.5),
            'td_rate': (0.5, 2.0),
            'pass_volume': (0.7, 1.3),
            'rush_volume': (0.7, 1.3),
            'scoring_rate': (0.5, 1.5),
            'int_rate': (0.5, 1.5)
        }

    async def get_projection(self, projection_id: str) -> Optional[Projection]:
        """Retrieve a specific projection."""
        return self.db.query(Projection).filter(Projection.projection_id == projection_id).first()

    async def get_player_projections(
        self,
        player_id: Optional[str] = None,
        team: Optional[str] = None,
        season: Optional[int] = None,
        scenario_id: Optional[str] = None
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

    async def create_base_projection(self, player_id: str, season: int) -> Optional[Projection]:
        """Create baseline projection from historical data."""
        try:
            # Get player and their historical stats
            player = self.db.query(Player).get(player_id)
            if not player:
                logger.error(f"Player {player_id} not found")
                return None
                
            # Get team stats for context
            team_stats = self.db.query(TeamStat).filter(
                and_(TeamStat.team == player.team, TeamStat.season == season)
            ).first()
            
            if not team_stats:
                logger.error(f"Team stats not found for {player.team} in {season}")
                return None
                
            # Get historical stats from previous season
            base_stats = self.db.query(BaseStat).filter(
                and_(BaseStat.player_id == player_id, BaseStat.season == season - 1)
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

    async def update_projection(
        self, 
        projection_id: str,
        adjustments: Dict[str, float]
    ) -> Optional[Projection]:
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
            
            # Apply adjustments
            await self._adjust_stats(projection, team_stats, adjustments)
                
            # Recalculate fantasy points
            projection.half_ppr = projection.calculate_fantasy_points()
            projection.updated_at = datetime.utcnow()
            
            self.db.commit()
            return projection
            
        except Exception as e:
            logger.error(f"Error updating projection: {str(e)}")
            self.db.rollback()
            return None

    async def validate_adjustments(
        self, 
        player_id: str,
        adjustments: Dict[str, float]
    ) -> bool:
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
        self, 
        name: str,
        description: Optional[str] = None,
        base_scenario_id: Optional[str] = None
    ) -> Optional[str]:
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

    async def apply_team_adjustments(
        self, 
        team: str,
        season: int,
        adjustments: Dict[str, float]
    ) -> List[Projection]:
        """Apply adjustments at team level and update affected players."""
        try:
            # Get all players for the team
            players = self.db.query(Player).filter(Player.team == team).all()
            
            # Get team stats
            team_stats = self.db.query(TeamStat).filter(
                and_(TeamStat.team == team, TeamStat.season == season)
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

    async def get_projection_trends(
        self, 
        player_id: str,
        stat_type: str,
        weeks: int = 8
    ) -> List[Dict]:
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
            return [{
                'season': stat.season,
                'week': stat.week,
                'value': stat.value
            } for stat in base_stats]
            
        except Exception as e:
            logger.error(f"Error getting projection trends: {str(e)}")
            return []

    async def _calculate_base_projection(
        self,
        player: Player,
        team_stats: TeamStat,
        base_stats: List[BaseStat],
        season: int
    ) -> Optional[Projection]:
        """Calculate baseline projection from historical data."""
        try:
            # Convert base stats to dictionary for easier access
            stats_dict = {
                stat.stat_type: stat.value 
                for stat in base_stats
            }
            
            # If no historical stats, estimate from team context
            if not stats_dict:
                stats_dict = self._estimate_stats_from_team_context(player, team_stats)
            
            # Create base projection
            projection = Projection(
                projection_id=str(uuid.uuid4()),
                player_id=player.player_id,
                season=season,
                games=17  # Full season
            )
            
            # Set position-specific stats using a polymorphic approach
            position_setters = {
                'QB': self._set_qb_stats,
                'RB': self._set_rb_stats,
                'WR': self._set_receiver_stats,
                'TE': self._set_receiver_stats
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

    def _estimate_stats_from_team_context(self, player: Player, team_stats: TeamStat) -> Dict:
        """Estimate baseline stats from team context when no historical data available."""
        position_estimators = {
            'QB': self._estimate_qb_stats,
            'RB': self._estimate_rb_stats,
            'WR': self._estimate_receiver_stats,
            'TE': self._estimate_receiver_stats
        }
        
        estimator = position_estimators.get(player.position)
        return estimator(team_stats) if estimator else {}

    def _estimate_qb_stats(self, team_stats: TeamStat) -> Dict:
        """Estimate QB stats based on team context."""
        return {
            'pass_attempts': team_stats.pass_attempts * 0.95,
            'completions': team_stats.receptions * 0.95,
            'pass_yards': team_stats.pass_yards * 0.95,
            'pass_td': team_stats.pass_td * 0.95,
            'interceptions': team_stats.pass_attempts * 0.02,
            'rush_attempts': 40,
            'rush_yards': 200,
            'rush_td': 2
        }

    def _estimate_rb_stats(self, team_stats: TeamStat) -> Dict:
        """Estimate RB stats based on team context."""
        return {
            'rush_attempts': team_stats.rush_attempts * 0.4,
            'rush_yards': team_stats.rush_yards * 0.4,
            'rush_td': team_stats.rush_td * 0.4,
            'targets': team_stats.targets * 0.1,
            'receptions': team_stats.receptions * 0.1,
            'rec_yards': team_stats.rec_yards * 0.08,
            'rec_td': team_stats.rec_td * 0.08
        }

    def _estimate_receiver_stats(self, team_stats: TeamStat) -> Dict:
        """Estimate WR/TE stats based on team context."""
        return {
            'targets': team_stats.targets * 0.15,
            'receptions': team_stats.receptions * 0.15,
            'rec_yards': team_stats.rec_yards * 0.15,
            'rec_td': team_stats.rec_td * 0.15,
            'rush_attempts': 0,
            'rush_yards': 0,
            'rush_td': 0
        }

    async def _adjust_stats(
        self, 
        projection: Projection, 
        team_stats: TeamStat, 
        adjustments: Dict[str, float]
    ) -> None:
        """Generic stat adjustment method based on player position."""
        position_adjusters = {
            'QB': self._adjust_qb_stats,
            'RB': self._adjust_rb_stats,
            'WR': self._adjust_receiver_stats,
            'TE': self._adjust_receiver_stats
        }
        
        adjuster = position_adjusters.get(projection.player.position)
        if adjuster:
            await adjuster(projection, team_stats, adjustments)

    async def _adjust_qb_stats(
        self, 
        projection: Projection,
        team_stats: TeamStat,
        adjustments: Dict[str, float]
    ) -> None:
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

    async def _adjust_rb_stats(
        self,
        projection: Projection,
        team_stats: TeamStat,
        adjustments: Dict[str, float]
    ) -> None:
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

    async def _adjust_receiver_stats(
        self,
        projection: Projection,
        team_stats: TeamStat,
        adjustments: Dict[str, float]
    ) -> None:
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

    async def _apply_team_adjustment(
        self,
        projection: Projection,
        team_stats: TeamStat,
        adjustments: Dict[str, float]
    ) -> Optional[Projection]:
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

    def _set_qb_stats(self, projection: Projection, stats_dict: Dict, team_stats: TeamStat) -> None:
        """Set QB-specific projection stats."""
        projection.pass_attempts = stats_dict.get('pass_attempts', team_stats.pass_attempts)
        projection.completions = stats_dict.get('completions', team_stats.receptions)
        projection.pass_yards = stats_dict.get('pass_yards', team_stats.pass_yards)
        projection.pass_td = stats_dict.get('pass_td', team_stats.pass_td)
        projection.interceptions = stats_dict.get('interceptions', 0)
        projection.carries = stats_dict.get('rush_attempts', 0)
        projection.rush_yards = stats_dict.get('rush_yards', 0)
        projection.rush_td = stats_dict.get('rush_td', 0)

    def _set_rb_stats(self, projection: Projection, stats_dict: Dict, team_stats: TeamStat) -> None:
        """Set RB-specific projection stats."""
        projection.carries = stats_dict.get('rush_attempts', 0)
        projection.rush_yards = stats_dict.get('rush_yards', 0)
        projection.rush_td = stats_dict.get('rush_td', 0)
        projection.targets = stats_dict.get('targets', 0)
        projection.receptions = stats_dict.get('receptions', 0)
        projection.rec_yards = stats_dict.get('rec_yards', 0)
        projection.rec_td = stats_dict.get('rec_td', 0)

    def _set_receiver_stats(self, projection: Projection, stats_dict: Dict, team_stats: TeamStat) -> None:
        """Set WR/TE-specific projection stats."""
        projection.targets = stats_dict.get('targets', 0)
        projection.receptions = stats_dict.get('receptions', 0)
        projection.rec_yards = stats_dict.get('rec_yards', 0)
        projection.rec_td = stats_dict.get('rec_td', 0)
        projection.carries = stats_dict.get('rush_attempts', 0)
        projection.rush_yards = stats_dict.get('rush_yards', 0)
        projection.rush_td = stats_dict.get('rush_td', 0)