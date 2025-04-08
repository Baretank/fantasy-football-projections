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
    
    async def get_projection_by_player(self, player_id: str, season: int) -> Optional[Projection]:
        """Get a projection for a specific player and season."""
        projections = await self.get_player_projections(player_id=player_id, season=season)
        return projections[0] if projections else None

    async def create_base_projection(self, player_id: str, season: int, scenario_id: Optional[str] = None) -> Optional[Projection]:
        """Create baseline projection from historical data."""
        try:
            # Get player and their historical stats
            player = self.db.get(Player, player_id)
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
        self, 
        projection_id: str,
        adjustments: Dict[str, float]
    ) -> Optional[Projection]:
        """Update an existing projection with adjustments."""
        try:
            # Use a join to get both the projection and the player in one query
            projection = self.db.query(Projection).join(Player).filter(
                Projection.projection_id == projection_id
            ).first()
            
            if not projection:
                return None
                
            # Get the player object
            player = projection.player
            
            # Validate adjustments
            if not await self.validate_adjustments(projection.player_id, adjustments):
                logger.error("Invalid adjustments provided")
                return None
                
            # Get team context
            team_stats = self.db.query(TeamStat).filter(
                and_(TeamStat.team == player.team,
                     TeamStat.season == projection.season)
            ).first()
            
            # Make a deep copy of the projection for modification
            # We'll modify this copy and then persist it
            projection_values = {
                'projection_id': projection_id,
                'player_id': projection.player_id,
                'scenario_id': projection.scenario_id,
                'season': projection.season,
                'games': projection.games,
                'half_ppr': projection.half_ppr,
                
                # Copy all the fields that might be adjusted
                'pass_attempts': projection.pass_attempts,
                'completions': projection.completions,
                'pass_yards': projection.pass_yards,
                'pass_td': projection.pass_td,
                'interceptions': projection.interceptions,
                'rush_attempts': projection.rush_attempts,
                'rush_yards': projection.rush_yards,
                'rush_td': projection.rush_td,
                'targets': projection.targets,
                'receptions': projection.receptions,
                'rec_yards': projection.rec_yards,
                'rec_td': projection.rec_td,
                
                # Efficiency metrics
                'yards_per_att': projection.yards_per_att,
                'comp_pct': projection.comp_pct,
                'pass_td_rate': projection.pass_td_rate,
                'yards_per_carry': projection.yards_per_carry,
                'catch_pct': projection.catch_pct,
                'yards_per_target': projection.yards_per_target,
                'rec_td_rate': projection.rec_td_rate,
                
                # Other fields
                'snap_share': projection.snap_share,
                'target_share': projection.target_share,
                'rush_share': projection.rush_share,
                
                # Mark as updated
                'updated_at': datetime.utcnow()
            }
            
            logger.debug(f"Adjusting {player.name} ({player.position}) with: {adjustments}")
            logger.debug(f"Before adjustments: pass_td={projection_values.get('pass_td', 'N/A')}, rush_td={projection_values.get('rush_td', 'N/A')}, rec_td={projection_values.get('rec_td', 'N/A')}")
            
            # Apply adjustments based on player position
            if player.position == 'QB':
                # QB adjustments
                if 'pass_volume' in adjustments:
                    factor = adjustments['pass_volume']
                    projection_values['pass_attempts'] *= factor
                    projection_values['completions'] *= factor
                    projection_values['pass_yards'] *= factor
                    if projection_values['pass_attempts'] > 0:
                        projection_values['yards_per_att'] = projection_values['pass_yards'] / projection_values['pass_attempts']
                        projection_values['comp_pct'] = projection_values['completions'] / projection_values['pass_attempts'] * 100
                
                if 'td_rate' in adjustments:
                    factor = adjustments['td_rate']
                    old_pass_td = projection_values['pass_td']
                    projection_values['pass_td'] *= factor
                    logger.debug(f"QB td_rate adjustment: {old_pass_td} -> {projection_values['pass_td']} (factor: {factor})")
                    if projection_values['pass_attempts'] > 0:
                        projection_values['pass_td_rate'] = projection_values['pass_td'] / projection_values['pass_attempts']
                
                if 'int_rate' in adjustments:
                    projection_values['interceptions'] *= adjustments['int_rate']
                    
                if 'rush_volume' in adjustments:
                    factor = adjustments['rush_volume']
                    projection_values['rush_attempts'] *= factor
                    projection_values['rush_yards'] *= factor
                    projection_values['rush_td'] *= factor
                    if projection_values['rush_attempts'] > 0:
                        projection_values['yards_per_carry'] = projection_values['rush_yards'] / projection_values['rush_attempts']
                
            elif player.position == 'RB':
                # RB adjustments
                if 'rush_volume' in adjustments:
                    factor = adjustments['rush_volume']
                    projection_values['rush_attempts'] *= factor
                    projection_values['rush_yards'] *= factor
                    projection_values['rush_td'] *= factor
                    if projection_values['rush_attempts'] > 0:
                        projection_values['yards_per_carry'] = projection_values['rush_yards'] / projection_values['rush_attempts']
                
                if 'target_share' in adjustments:
                    factor = adjustments['target_share']
                    projection_values['targets'] *= factor
                    projection_values['receptions'] *= (factor * 0.95)
                    projection_values['rec_yards'] *= factor
                    projection_values['rec_td'] *= factor
                    if projection_values['targets'] > 0:
                        projection_values['catch_pct'] = projection_values['receptions'] / projection_values['targets'] * 100
                        projection_values['yards_per_target'] = projection_values['rec_yards'] / projection_values['targets']
                        projection_values['rec_td_rate'] = projection_values['rec_td'] / projection_values['targets']
                
                # Apply td_rate adjustment for RBs 
                if 'td_rate' in adjustments:
                    factor = adjustments['td_rate']
                    old_rush_td = projection_values['rush_td']
                    old_rec_td = projection_values.get('rec_td', 0)
                    projection_values['rush_td'] *= factor
                    if 'rec_td' in projection_values and projection_values['rec_td'] is not None:
                        projection_values['rec_td'] *= factor
                    logger.debug(f"RB td_rate adjustment: rush_td {old_rush_td} -> {projection_values['rush_td']}, rec_td {old_rec_td} -> {projection_values.get('rec_td', 'N/A')} (factor: {factor})")
            
            elif player.position in ['WR', 'TE']:
                # WR/TE adjustments
                if 'target_share' in adjustments:
                    factor = adjustments['target_share']
                    # Store the target_share value directly
                    projection_values['target_share'] = factor
                    projection_values['targets'] *= factor
                    projection_values['receptions'] *= (factor * 0.95)
                    projection_values['rec_yards'] *= factor
                    projection_values['rec_td'] *= factor
                    if projection_values['targets'] > 0:
                        projection_values['catch_pct'] = projection_values['receptions'] / projection_values['targets'] * 100
                        projection_values['yards_per_target'] = projection_values['rec_yards'] / projection_values['targets']
                        projection_values['rec_td_rate'] = projection_values['rec_td'] / projection_values['targets']
                
                if 'td_rate' in adjustments:
                    factor = adjustments['td_rate']
                    old_rec_td = projection_values.get('rec_td', 0)
                    if 'rec_td' in projection_values and projection_values['rec_td'] is not None:
                        projection_values['rec_td'] *= factor
                    logger.debug(f"WR/TE td_rate adjustment: rec_td {old_rec_td} -> {projection_values.get('rec_td', 'N/A')} (factor: {factor})")
                
                if 'snap_share' in adjustments:
                    projection_values['snap_share'] = min(1.0, (projection_values['snap_share'] or 0.0) * adjustments['snap_share'])
            
            # Calculate fantasy points
            # First, update the projection with our adjusted values
            for key, value in projection_values.items():
                setattr(projection, key, value)
            
            # Calculate fantasy points
            original_half_ppr = projection.half_ppr if projection.half_ppr else 0.0
            calculated_half_ppr = projection.calculate_fantasy_points()
            projection_values['half_ppr'] = calculated_half_ppr
            
            logger.info(f"Fantasy points: original={original_half_ppr}, new={calculated_half_ppr}")
            logger.info(f"TD values: rush_td={projection.rush_td}, rec_td={projection.rec_td}")
            
            # Persist the changes - update the existing record with our values
            update_stmt = {key: value for key, value in projection_values.items() 
                          if key != 'projection_id'}  # exclude primary key
            
            logger.debug(f"Updating with statement: {update_stmt}")
            
            self.db.query(Projection).filter(
                Projection.projection_id == projection_id
            ).update(update_stmt)
            
            self.db.commit()
            
            # Get a completely fresh version of the projection from the database
            # This ensures we don't run into stale/cached data issues from SQLAlchemy
            self.db.expire_all()  # Clear any cached state on the session
            # Force a new query to get the latest data from database
            updated = self.db.query(Projection).filter(Projection.projection_id == projection_id).first()
            logger.info(f"Updated projection half_ppr: {updated.half_ppr}")
            logger.debug(f"Final values: pass_td={getattr(updated, 'pass_td', 'N/A')}, rush_td={getattr(updated, 'rush_td', 'N/A')}, rec_td={getattr(updated, 'rec_td', 'N/A')}")
            return updated
            
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
            
        # Create a new instance with the same ID to ensure updates are tracked by SQLAlchemy
        # The adjustment changes weren't being persisted because we're modifying the same object
        projection.updated_at = datetime.utcnow()
        self.db.flush()

    async def _adjust_qb_stats(
        self, 
        projection: Projection,
        team_stats: TeamStat,
        adjustments: Dict[str, float]
    ) -> None:
        """Adjust QB-specific statistics."""
        if 'pass_volume' in adjustments:
            factor = adjustments['pass_volume']
            projection.pass_attempts = projection.pass_attempts * factor
            projection.completions = projection.completions * factor
            projection.pass_yards = projection.pass_yards * factor
            
        if 'td_rate' in adjustments:
            projection.pass_td = projection.pass_td * adjustments['td_rate']
            if projection.pass_attempts > 0:
                projection.pass_td_rate = projection.pass_td / projection.pass_attempts
            
        if 'int_rate' in adjustments:
            projection.interceptions = projection.interceptions * adjustments['int_rate']
            
        if 'rush_share' in adjustments:
            factor = adjustments['rush_share']
            projection.rush_attempts = projection.rush_attempts * factor
            projection.rush_yards = projection.rush_yards * factor
            projection.rush_td = projection.rush_td * factor

    async def _adjust_rb_stats(
        self,
        projection: Projection,
        team_stats: TeamStat,
        adjustments: Dict[str, float]
    ) -> None:
        """Adjust RB-specific statistics."""
        if 'rush_share' in adjustments:
            factor = adjustments['rush_share']
            projection.rush_attempts = projection.rush_attempts * factor
            projection.rush_yards = projection.rush_yards * factor
            projection.rush_td = projection.rush_td * factor
            if projection.rush_attempts > 0:
                projection.yards_per_carry = projection.rush_yards / projection.rush_attempts
                projection.rush_td_rate = projection.rush_td / projection.rush_attempts
            
        if 'target_share' in adjustments:
            factor = adjustments['target_share']
            projection.targets = projection.targets * factor
            projection.receptions = projection.receptions * (factor * 0.95)  # Slight reduction in catch rate
            projection.rec_yards = projection.rec_yards * factor
            projection.rec_td = projection.rec_td * factor
            if projection.targets > 0:
                projection.catch_pct = projection.receptions / projection.targets * 100
                projection.yards_per_target = projection.rec_yards / projection.targets
                projection.rec_td_rate = projection.rec_td / projection.targets

    async def _adjust_receiver_stats(
        self,
        projection: Projection,
        team_stats: TeamStat,
        adjustments: Dict[str, float]
    ) -> None:
        """Adjust WR/TE-specific statistics."""
        if 'target_share' in adjustments:
            factor = adjustments['target_share']
            projection.targets = projection.targets * factor
            projection.receptions = projection.receptions * (factor * 0.95)
            projection.rec_yards = projection.rec_yards * factor
            projection.rec_td = projection.rec_td * factor
            if projection.targets > 0:
                projection.catch_pct = projection.receptions / projection.targets * 100
                projection.yards_per_target = projection.rec_yards / projection.targets
                projection.rec_td_rate = projection.rec_td / projection.targets
            
        if 'snap_share' in adjustments:
            factor = adjustments['snap_share']
            projection.snap_share = min(1.0, (projection.snap_share or 0.0) * factor)

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
                projection.pass_attempts = projection.pass_attempts * factor
                projection.completions = projection.completions * factor
                projection.pass_yards = projection.pass_yards * factor
                if projection.pass_attempts > 0:
                    projection.yards_per_att = projection.pass_yards / projection.pass_attempts
                
            # Adjust receiver targets based on pass volume
            if 'pass_volume' in adjustments and projection.player.position in ['WR', 'TE', 'RB']:
                factor = adjustments['pass_volume']
                if projection.targets is not None:
                    projection.targets = projection.targets * factor
                    projection.receptions = projection.receptions * factor
                    projection.rec_yards = projection.rec_yards * factor
                    if projection.targets > 0:
                        projection.yards_per_target = projection.rec_yards / projection.targets
                
            if 'rush_volume' in adjustments:
                factor = adjustments['rush_volume']
                if projection.rush_attempts is not None:
                    projection.rush_attempts = projection.rush_attempts * factor
                    projection.rush_yards = projection.rush_yards * factor
                    if projection.rush_attempts > 0:
                        projection.yards_per_carry = projection.rush_yards / projection.rush_attempts
                    
            if 'scoring_rate' in adjustments:
                factor = adjustments['scoring_rate']
                if projection.pass_td is not None:
                    projection.pass_td = projection.pass_td * factor
                    if projection.pass_attempts > 0:
                        projection.pass_td_rate = projection.pass_td / projection.pass_attempts
                if projection.rush_td is not None:
                    projection.rush_td = projection.rush_td * factor
                    if projection.rush_attempts and projection.rush_attempts > 0:
                        projection.rush_td_rate = projection.rush_td / projection.rush_attempts
                if projection.rec_td is not None:
                    projection.rec_td = projection.rec_td * factor
                    if projection.targets and projection.targets > 0:
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

    def _set_qb_stats(self, projection: Projection, stats_dict: Dict, team_stats: TeamStat) -> None:
        """Set QB-specific projection stats."""
        projection.pass_attempts = stats_dict.get('pass_attempts', team_stats.pass_attempts)
        projection.completions = stats_dict.get('completions', team_stats.receptions)
        projection.pass_yards = stats_dict.get('pass_yards', team_stats.pass_yards)
        projection.pass_td = stats_dict.get('pass_td', team_stats.pass_td)
        projection.interceptions = stats_dict.get('interceptions', 0)
        projection.rush_attempts = stats_dict.get('rush_attempts', 0)
        projection.rush_yards = stats_dict.get('rush_yards', 0)
        projection.rush_td = stats_dict.get('rush_td', 0)
        
        # Calculate efficiency metrics
        if projection.pass_attempts > 0:
            projection.yards_per_att = projection.pass_yards / projection.pass_attempts
            projection.comp_pct = projection.completions / projection.pass_attempts * 100
            projection.pass_td_rate = projection.pass_td / projection.pass_attempts
            
        if projection.rush_attempts > 0:
            projection.yards_per_carry = projection.rush_yards / projection.rush_attempts

    def _set_rb_stats(self, projection: Projection, stats_dict: Dict, team_stats: TeamStat) -> None:
        """Set RB-specific projection stats."""
        projection.rush_attempts = stats_dict.get('rush_attempts', 0)
        projection.rush_yards = stats_dict.get('rush_yards', 0)
        projection.rush_td = stats_dict.get('rush_td', 0)
        projection.targets = stats_dict.get('targets', 0)
        projection.receptions = stats_dict.get('receptions', 0)
        projection.rec_yards = stats_dict.get('rec_yards', 0)
        projection.rec_td = stats_dict.get('rec_td', 0)
        
        # Calculate efficiency metrics
        if projection.rush_attempts > 0:
            projection.yards_per_carry = projection.rush_yards / projection.rush_attempts
            projection.rush_td_rate = projection.rush_td / projection.rush_attempts
            
        if projection.targets > 0:
            projection.catch_pct = projection.receptions / projection.targets * 100
            projection.yards_per_target = projection.rec_yards / projection.targets
            projection.rec_td_rate = projection.rec_td / projection.targets
            
    def _set_receiver_stats(self, projection: Projection, stats_dict: Dict, team_stats: TeamStat) -> None:
        """Set WR/TE-specific projection stats."""
        projection.targets = stats_dict.get('targets', 0)
        projection.receptions = stats_dict.get('receptions', 0)
        projection.rec_yards = stats_dict.get('rec_yards', 0)
        projection.rec_td = stats_dict.get('rec_td', 0)
        projection.rush_attempts = stats_dict.get('rush_attempts', 0)
        projection.rush_yards = stats_dict.get('rush_yards', 0)
        projection.rush_td = stats_dict.get('rush_td', 0)
        
        # Calculate efficiency metrics
        if projection.targets > 0:
            projection.catch_pct = projection.receptions / projection.targets * 100
            projection.yards_per_target = projection.rec_yards / projection.targets
            projection.rec_td_rate = projection.rec_td / projection.targets
            
        if projection.rush_attempts > 0:
            projection.yards_per_carry = projection.rush_yards / projection.rush_attempts