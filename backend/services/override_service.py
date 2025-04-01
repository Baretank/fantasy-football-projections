from typing import Dict, List, Optional, Union, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
import uuid
import logging

from backend.database.models import StatOverride, Projection, Player

logger = logging.getLogger(__name__)

class OverrideService:
    """
    Service for managing manual overrides to projections.
    Handles creating, retrieving, and applying overrides.
    """
    
    def __init__(self, db: Session):
        self.db = db
        
        # Define stat dependencies for recalculation
        self.dependent_stats = {
            # Passing dependencies
            'pass_attempts': ['completions', 'pass_yards', 'pass_td', 'interceptions', 'pass_td_rate', 'int_rate'],
            'completions': ['comp_pct'],
            'pass_yards': ['yards_per_att', 'yards_per_target'],
            'pass_td': ['pass_td_rate'],
            'interceptions': ['int_rate'],
            'sacks': ['sack_yards', 'net_pass_yards', 'sack_rate'],
            
            # Rushing dependencies
            'rush_attempts': ['rush_yards', 'yards_per_carry'],
            'rush_yards': ['yards_per_carry', 'net_rush_yards'],
            'rush_td': ['rush_td_rate'],
            'fumbles': ['fumble_rate', 'net_rush_yards'],
            
            # Receiving dependencies
            'targets': ['receptions', 'rec_yards', 'rec_td', 'catch_pct', 'yards_per_target', 'rec_td_rate'],
            'receptions': ['catch_pct'],
            'rec_yards': ['yards_per_target'],
            'rec_td': ['rec_td_rate']
        }
    
    async def create_override(
        self, 
        player_id: str,
        projection_id: str,
        stat_name: str,
        manual_value: float,
        notes: Optional[str] = None
    ) -> Optional[StatOverride]:
        """
        Create a new stat override for a projection.
        
        Args:
            player_id: Player ID
            projection_id: Projection ID
            stat_name: Name of the stat to override
            manual_value: User-provided value
            notes: Optional notes about the override
            
        Returns:
            Created StatOverride object or None if failed
        """
        try:
            # Get projection to get original value
            projection = self.db.query(Projection).filter(
                Projection.projection_id == projection_id
            ).first()
            
            if not projection:
                logger.error(f"Projection {projection_id} not found")
                return None
                
            # Validate that this stat exists on the projection
            if not hasattr(projection, stat_name):
                logger.error(f"Invalid stat name: {stat_name}")
                return None
                
            # Get calculated value
            calculated_value = getattr(projection, stat_name)
            
            logger.info(f"CREATE OVERRIDE: stat={stat_name}, original={calculated_value}, new={manual_value}")
            
            # Store original value with a special attribute name for dependent stat calculation
            setattr(projection, f"{stat_name}_before_override", calculated_value)
            
            # Create override
            override = StatOverride(
                override_id=str(uuid.uuid4()),
                player_id=player_id,
                projection_id=projection_id,
                stat_name=stat_name,
                calculated_value=calculated_value if calculated_value is not None else 0.0,
                manual_value=manual_value,
                notes=notes
            )
            
            self.db.add(override)
            
            # Mark projection as having overrides
            projection.has_overrides = True
            
            # Update the projection with the new value
            setattr(projection, stat_name, manual_value)
            
            # Recalculate dependent stats
            await self._recalculate_dependent_stats(projection, stat_name)
            
            # Recalculate fantasy points for all scoring formats
            projection.half_ppr = projection.calculate_fantasy_points(scoring_type='half')
            # No need to explicitly set standard and ppr as they're calculated on demand via properties
            projection.updated_at = datetime.utcnow()
            
            self.db.commit()
            return override
            
        except Exception as e:
            logger.error(f"Error creating override: {str(e)}")
            self.db.rollback()
            return None
    
    async def get_player_overrides(self, player_id: str) -> List[StatOverride]:
        """Get all overrides for a player."""
        return self.db.query(StatOverride).filter(
            StatOverride.player_id == player_id
        ).all()
    
    async def get_projection_overrides(self, projection_id: str) -> List[StatOverride]:
        """Get all overrides for a projection."""
        return self.db.query(StatOverride).filter(
            StatOverride.projection_id == projection_id
        ).all()
        
    async def get_overrides_for_projection(self, projection_id: str) -> List[StatOverride]:
        """Get all overrides for a projection (alias for get_projection_overrides)."""
        return await self.get_projection_overrides(projection_id)
    
    async def apply_overrides_to_projection(self, projection: Projection) -> Projection:
        """
        Apply all overrides to a projection and recalculate dependent stats.
        
        Args:
            projection: Projection object to update
            
        Returns:
            Updated projection
        """
        try:
            # Get overrides for this projection
            overrides = await self.get_projection_overrides(projection.projection_id)
            
            if not overrides:
                return projection
                
            # Apply each override
            for override in overrides:
                setattr(projection, override.stat_name, override.manual_value)
                
                # Recalculate dependent stats
                await self._recalculate_dependent_stats(projection, override.stat_name)
                
            # Recalculate fantasy points for all scoring formats
            projection.half_ppr = projection.calculate_fantasy_points(scoring_type='half')
            # No need to explicitly set standard and ppr as they're calculated on demand via properties
            projection.updated_at = datetime.utcnow()
            
            self.db.commit()
            return projection
            
        except Exception as e:
            logger.error(f"Error applying overrides: {str(e)}")
            self.db.rollback()
            return projection
    
    async def delete_override(self, override_id: str) -> bool:
        """
        Delete an override and restore the calculated value.
        
        Args:
            override_id: Override ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            override = self.db.query(StatOverride).filter(
                StatOverride.override_id == override_id
            ).first()
            
            if not override:
                logger.error(f"Override {override_id} not found")
                return False
                
            # Get projection
            projection = self.db.query(Projection).filter(
                Projection.projection_id == override.projection_id
            ).first()
            
            if not projection:
                logger.error(f"Projection {override.projection_id} not found")
                return False
                
            # Restore original value
            setattr(projection, override.stat_name, override.calculated_value)
            
            # Recalculate dependent stats
            await self._recalculate_dependent_stats(projection, override.stat_name)
            
            # Check if there are any other overrides
            other_overrides = self.db.query(StatOverride).filter(
                and_(
                    StatOverride.projection_id == override.projection_id,
                    StatOverride.override_id != override_id
                )
            ).count()
            
            # Update has_overrides flag
            projection.has_overrides = other_overrides > 0
            
            # Recalculate fantasy points for all scoring formats
            projection.half_ppr = projection.calculate_fantasy_points(scoring_type='half')
            # No need to explicitly set standard and ppr as they're calculated on demand via properties
            projection.updated_at = datetime.utcnow()
            
            # Delete the override
            self.db.delete(override)
            self.db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting override: {str(e)}")
            self.db.rollback()
            return False
    
    async def batch_override(
        self, 
        player_ids: List[str],
        stat_name: str,
        value: Union[float, Dict[str, Any]],
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Apply the same override to multiple players.
        
        Args:
            player_ids: List of player IDs
            stat_name: Name of the stat to override
            value: Either a fixed value or an adjustment method 
                  (e.g., {'method': 'percentage', 'amount': 10})
            notes: Optional notes about the overrides
            
        Returns:
            Dictionary with results per player
        """
        results = {}
        
        for player_id in player_ids:
            try:
                # Get the latest projection for this player
                projection = self.db.query(Projection).filter(
                    Projection.player_id == player_id
                ).order_by(Projection.created_at.desc()).first()
                
                if not projection:
                    results[player_id] = {
                        "success": False,
                        "message": "No projection found"
                    }
                    continue
                    
                # Check if the stat exists for this player's position
                if not hasattr(projection, stat_name) or getattr(projection, stat_name) is None:
                    results[player_id] = {
                        "success": False,
                        "message": f"Stat {stat_name} not applicable"
                    }
                    continue
                
                # Calculate the value to apply
                current_value = getattr(projection, stat_name) or 0.0
                override_value = current_value
                
                if isinstance(value, dict) and 'method' in value:
                    if value['method'] == 'percentage':
                        # Apply a percentage change
                        pct_change = value.get('amount', 0.0) / 100.0
                        override_value = current_value * (1 + pct_change)
                    elif value['method'] == 'increment':
                        # Add/subtract a fixed amount
                        override_value = current_value + value.get('amount', 0.0)
                else:
                    # Use the fixed value
                    override_value = float(value)
                
                # Create the override
                override = await self.create_override(
                    player_id=player_id,
                    projection_id=projection.projection_id,
                    stat_name=stat_name,
                    manual_value=override_value,
                    notes=notes
                )
                
                if override:
                    results[player_id] = {
                        "success": True,
                        "override_id": override.override_id,
                        "old_value": current_value,
                        "new_value": override_value
                    }
                else:
                    results[player_id] = {
                        "success": False,
                        "message": "Failed to create override"
                    }
                    
            except Exception as e:
                logger.error(f"Error in batch override for player {player_id}: {str(e)}")
                results[player_id] = {
                    "success": False,
                    "message": str(e)
                }
        
        return {"results": results}
    
    async def _recalculate_dependent_stats(
        self, 
        projection: Projection, 
        changed_stat: str
    ) -> None:
        """
        Recalculate stats that depend on an overridden value.
        
        Args:
            projection: Projection object to update
            changed_stat: Name of the stat that was changed
        """
        # Handle games change first - it affects almost all cumulative stats
        if changed_stat == 'games' and projection.games:
            # Get original games value from the attribute we saved during override creation
            original_games = getattr(projection, 'games_before_override', None)
            
            if original_games is None:
                # Try to get from database override
                try:
                    games_override = self.db.query(StatOverride).filter(
                        StatOverride.projection_id == projection.projection_id,
                        StatOverride.stat_name == 'games'
                    ).first()
                    
                    if games_override:
                        original_games = games_override.calculated_value
                except Exception as e:
                    logger.error(f"Error retrieving games override: {str(e)}")
            
            logger.info(f"GAMES OVERRIDE: original_games={original_games}, new_games={projection.games}")
            
            # If we don't have an override, we can't properly adjust - skip
            if not original_games or original_games == 0:
                logger.warning("Could not find original games value for adjustment")
                return
                
            # Calculate the ratio for adjustment
            games_ratio = projection.games / original_games
            logger.info(f"GAMES OVERRIDE: adjustment ratio={games_ratio}")
            
            # Store original values before adjustment if not already stored
            for stat_name in [
                'pass_attempts', 'completions', 'pass_yards', 'pass_td', 'interceptions',
                'rush_attempts', 'rush_yards', 'rush_td',
                'targets', 'receptions', 'rec_yards', 'rec_td'
            ]:
                if (hasattr(projection, stat_name) and 
                    getattr(projection, stat_name) is not None and 
                    not hasattr(projection, f"{stat_name}_before_games_override")):
                    # Save original value
                    setattr(projection, f"{stat_name}_before_games_override", getattr(projection, stat_name))
            
            # Adjust all cumulative stats proportionally
            for stat_name in [
                'pass_attempts', 'completions', 'pass_yards', 'pass_td', 'interceptions',
                'rush_attempts', 'rush_yards', 'rush_td',
                'targets', 'receptions', 'rec_yards', 'rec_td'
            ]:
                if hasattr(projection, stat_name) and getattr(projection, stat_name) is not None:
                    original_value = getattr(projection, f"{stat_name}_before_games_override", 
                                            getattr(projection, stat_name))
                    
                    new_value = original_value * games_ratio
                    
                    logger.info(f"GAMES OVERRIDE: Adjusting {stat_name} from {original_value} to {new_value}")
                    setattr(projection, stat_name, new_value)
        
        # Skip if the changed stat has no direct dependencies
        if changed_stat not in self.dependent_stats and changed_stat != 'games':
            return
            
        # Get the player for position-specific calculations
        player = self.db.query(Player).filter(
            Player.player_id == projection.player_id
        ).first()
        
        if not player:
            logger.error(f"Player {projection.player_id} not found")
            return
            
        # Get current values for tracking
        current_values = {}
        if changed_stat in self.dependent_stats:
            for stat in self.dependent_stats[changed_stat]:
                if hasattr(projection, stat):
                    current_values[stat] = getattr(projection, stat)
        
        # Recalculate dependent stats based on the position
        if player.position == 'QB':
            await self._recalculate_qb_stats(projection, changed_stat)
        elif player.position == 'RB':
            await self._recalculate_rb_stats(projection, changed_stat)
        elif player.position in ['WR', 'TE']:
            await self._recalculate_receiver_stats(projection, changed_stat)
    
    async def _recalculate_qb_stats(
        self, 
        projection: Projection, 
        changed_stat: str
    ) -> None:
        """Recalculate QB-specific stats after an override."""
        # When pass_attempts change, adjust all dependent passing stats proportionally
        if changed_stat == 'pass_attempts' and projection.pass_attempts:
            # First, save current completion rate, yards per attempt, TD rate, INT rate
            original_comp_rate = projection.comp_pct if hasattr(projection, 'comp_pct') and projection.comp_pct else (
                projection.completions / projection.pass_attempts if projection.completions and projection.pass_attempts else 0.0
            )
            
            original_yards_per_att = projection.yards_per_att if hasattr(projection, 'yards_per_att') and projection.yards_per_att else (
                projection.pass_yards / projection.pass_attempts if projection.pass_yards and projection.pass_attempts else 0.0
            )
            
            original_td_rate = projection.pass_td_rate if hasattr(projection, 'pass_td_rate') and projection.pass_td_rate else (
                projection.pass_td / projection.pass_attempts if projection.pass_td and projection.pass_attempts else 0.0
            )
            
            original_int_rate = projection.int_rate if hasattr(projection, 'int_rate') and projection.int_rate else (
                projection.interceptions / projection.pass_attempts if projection.interceptions and projection.pass_attempts else 0.0
            )
            
            # Apply the same rates to new attempts
            if original_comp_rate and projection.pass_attempts:
                projection.completions = projection.pass_attempts * original_comp_rate
                
            if original_yards_per_att and projection.pass_attempts:
                projection.pass_yards = projection.pass_attempts * original_yards_per_att
                
            if original_td_rate and projection.pass_attempts:
                projection.pass_td = projection.pass_attempts * original_td_rate
                
            if original_int_rate and projection.pass_attempts:
                projection.interceptions = projection.pass_attempts * original_int_rate
        
        # Handle passing efficiency metrics
        if changed_stat in ['pass_attempts', 'completions']:
            if projection.pass_attempts and projection.pass_attempts > 0:
                projection.comp_pct = (
                    projection.completions / projection.pass_attempts 
                    if projection.completions else 0.0
                )
        
        if changed_stat in ['pass_attempts', 'pass_yards']:
            if projection.pass_attempts and projection.pass_attempts > 0:
                projection.yards_per_att = (
                    projection.pass_yards / projection.pass_attempts 
                    if projection.pass_yards else 0.0
                )
        
        if changed_stat in ['pass_attempts', 'pass_td']:
            if projection.pass_attempts and projection.pass_attempts > 0:
                projection.pass_td_rate = (
                    projection.pass_td / projection.pass_attempts 
                    if projection.pass_td else 0.0
                )
        
        if changed_stat in ['pass_attempts', 'interceptions']:
            if projection.pass_attempts and projection.pass_attempts > 0:
                projection.int_rate = (
                    projection.interceptions / projection.pass_attempts 
                    if projection.interceptions else 0.0
                )
        
        # Handle sack-related metrics
        if changed_stat in ['pass_attempts', 'sacks']:
            if projection.sacks is not None and projection.pass_attempts:
                total_dropbacks = projection.pass_attempts + projection.sacks
                projection.sack_rate = projection.sacks / total_dropbacks if total_dropbacks > 0 else 0.0
        
        if changed_stat == 'sacks':
            if projection.sacks is not None:
                # Average sack yards loss is around 7 yards
                projection.sack_yards = projection.sacks * 7.0
        
        if changed_stat in ['pass_yards', 'sack_yards']:
            if projection.pass_yards is not None and projection.sack_yards is not None:
                projection.net_pass_yards = projection.pass_yards - projection.sack_yards
                
                # Recalculate net yards per attempt
                if projection.pass_attempts and projection.pass_attempts > 0:
                    projection.net_yards_per_att = (
                        projection.net_pass_yards / projection.pass_attempts
                    )
    
    async def _recalculate_rb_stats(
        self, 
        projection: Projection, 
        changed_stat: str
    ) -> None:
        """Recalculate RB-specific stats after an override."""
        # When rush_attempts change, adjust rush_yards and rush_td proportionally
        if changed_stat == 'rush_attempts' and projection.rush_attempts:
            # First, save current yards per carry and TD rate
            original_ypc = projection.yards_per_carry if hasattr(projection, 'yards_per_carry') and projection.yards_per_carry else (
                projection.rush_yards / projection.rush_attempts if projection.rush_yards and projection.rush_attempts else 0.0
            )
            
            original_rush_td_rate = projection.rush_td_rate if hasattr(projection, 'rush_td_rate') and projection.rush_td_rate else (
                projection.rush_td / projection.rush_attempts if projection.rush_td and projection.rush_attempts else 0.0
            )
            
            # Apply the same YPC to new rush attempts
            if original_ypc and projection.rush_attempts:
                projection.rush_yards = projection.rush_attempts * original_ypc
                
            # Apply the same TD rate to new rush attempts
            if original_rush_td_rate and projection.rush_attempts:
                projection.rush_td = projection.rush_attempts * original_rush_td_rate
        
        # When targets change, adjust receptions and receiving yards proportionally
        if changed_stat == 'targets' and projection.targets:
            # First, save current catch rate and yards per target
            original_catch_rate = projection.catch_pct if hasattr(projection, 'catch_pct') and projection.catch_pct else (
                projection.receptions / projection.targets if projection.receptions and projection.targets else 0.0
            )
            
            original_yards_per_target = projection.yards_per_target if hasattr(projection, 'yards_per_target') and projection.yards_per_target else (
                projection.rec_yards / projection.targets if projection.rec_yards and projection.targets else 0.0
            )
            
            original_td_rate = projection.rec_td_rate if hasattr(projection, 'rec_td_rate') and projection.rec_td_rate else (
                projection.rec_td / projection.targets if projection.rec_td and projection.targets else 0.0
            )
            
            # Apply the same catch rate to new targets
            if original_catch_rate and projection.targets:
                projection.receptions = projection.targets * original_catch_rate
                
            # Apply the same yards per target to new targets
            if original_yards_per_target and projection.targets:
                projection.rec_yards = projection.targets * original_yards_per_target
                
            # Apply the same TD rate to new targets
            if original_td_rate and projection.targets:
                projection.rec_td = projection.targets * original_td_rate
        
        # Handle rushing efficiency metrics
        if changed_stat in ['rush_attempts', 'rush_yards']:
            if projection.rush_attempts and projection.rush_attempts > 0:
                projection.yards_per_carry = (
                    projection.rush_yards / projection.rush_attempts 
                    if projection.rush_yards else 0.0
                )
        
        if changed_stat in ['rush_attempts', 'rush_td']:
            if projection.rush_attempts and projection.rush_attempts > 0:
                projection.rush_td_rate = (
                    projection.rush_td / projection.rush_attempts 
                    if projection.rush_td else 0.0
                )
        
        # Handle fumble metrics
        if changed_stat == 'fumbles':
            if projection.fumbles is not None and projection.rush_attempts:
                projection.fumble_rate = (
                    projection.fumbles / projection.rush_attempts 
                    if projection.rush_attempts > 0 else 0.0
                )
        
        if changed_stat in ['rush_yards', 'fumbles']:
            # Estimate yards lost due to fumbles (approximately 5 yards per fumble)
            if projection.rush_yards is not None:
                fumble_yards = projection.fumbles * 5.0 if projection.fumbles else 0.0
                projection.net_rush_yards = projection.rush_yards - fumble_yards
                
                # Recalculate net yards per carry
                if projection.rush_attempts and projection.rush_attempts > 0:
                    projection.net_yards_per_carry = (
                        projection.net_rush_yards / projection.rush_attempts
                    )
        
        # Handle receiving efficiency metrics
        if changed_stat in ['targets', 'receptions']:
            if projection.targets and projection.targets > 0:
                projection.catch_pct = (
                    projection.receptions / projection.targets 
                    if projection.receptions else 0.0
                )
        
        if changed_stat in ['targets', 'rec_yards']:
            if projection.targets and projection.targets > 0:
                projection.yards_per_target = (
                    projection.rec_yards / projection.targets 
                    if projection.rec_yards else 0.0
                )
        
        if changed_stat in ['targets', 'rec_td']:
            if projection.targets and projection.targets > 0:
                projection.rec_td_rate = (
                    projection.rec_td / projection.targets 
                    if projection.rec_td else 0.0
                )
    
    async def _recalculate_receiver_stats(
        self, 
        projection: Projection, 
        changed_stat: str
    ) -> None:
        """Recalculate WR/TE-specific stats after an override."""
        # When targets change, we need to adjust receptions and yards proportionally
        if changed_stat == 'targets' and projection.targets:
            # Log current values for debugging
            logger.info(f"RECALC RECEIVER: targets={projection.targets}, receptions={projection.receptions}")
            logger.info(f"RECALC RECEIVER: catch_pct={getattr(projection, 'catch_pct', None)}")
            
            if not hasattr(projection, 'catch_pct') or projection.catch_pct is None:
                # Calculate catch rate directly from the stat values
                if projection.receptions is not None and projection.targets is not None:
                    projection.catch_pct = projection.receptions / projection.targets if projection.targets > 0 else 0.0
                    logger.info(f"RECALC RECEIVER: Calculated catch_pct as {projection.catch_pct}")
            
            # Simple direct calculation based on current data
            original_targets = getattr(projection, 'targets_before_override', projection.targets)
            original_receptions = getattr(projection, 'receptions_before_override', projection.receptions)
            
            # Store original values for debugging and future calculations
            if not hasattr(projection, 'targets_before_override'):
                projection.targets_before_override = original_targets
                projection.receptions_before_override = original_receptions
                
            logger.info(f"RECALC RECEIVER: original_targets={original_targets}, original_receptions={original_receptions}")
            
            # Calculate the scale factor from the original stats
            if original_targets and original_targets > 0 and original_receptions is not None:
                catch_rate = original_receptions / original_targets
                
                # Apply direct proportion calculation
                new_receptions = projection.targets * catch_rate
                
                logger.info(f"RECALC RECEIVER: catch_rate={catch_rate}, new_receptions={new_receptions}")
                
                # Update the projection with new values
                projection.receptions = new_receptions
                
                # Apply the same catch rate to other receiving stats
                if hasattr(projection, 'rec_yards') and projection.rec_yards is not None:
                    original_yards = getattr(projection, 'rec_yards_before_override', projection.rec_yards)
                    if not hasattr(projection, 'rec_yards_before_override'):
                        projection.rec_yards_before_override = original_yards
                    
                    if original_receptions > 0:
                        yards_per_rec = original_yards / original_receptions
                        projection.rec_yards = new_receptions * yards_per_rec
                        logger.info(f"RECALC RECEIVER: yards_per_rec={yards_per_rec}, new_rec_yards={projection.rec_yards}")
                
                if hasattr(projection, 'rec_td') and projection.rec_td is not None:
                    original_td = getattr(projection, 'rec_td_before_override', projection.rec_td)
                    if not hasattr(projection, 'rec_td_before_override'):
                        projection.rec_td_before_override = original_td
                    
                    if original_receptions > 0:
                        td_per_rec = original_td / original_receptions
                        projection.rec_td = new_receptions * td_per_rec
                        logger.info(f"RECALC RECEIVER: td_per_rec={td_per_rec}, new_rec_td={projection.rec_td}")
        
        # Calculate efficiency metrics
        if changed_stat in ['targets', 'receptions'] or changed_stat == 'targets':
            if projection.targets and projection.targets > 0:
                projection.catch_pct = (
                    projection.receptions / projection.targets 
                    if projection.receptions else 0.0
                )
        
        if changed_stat in ['targets', 'rec_yards'] or changed_stat == 'targets':
            if projection.targets and projection.targets > 0:
                projection.yards_per_target = (
                    projection.rec_yards / projection.targets 
                    if projection.rec_yards else 0.0
                )
        
        if changed_stat in ['targets', 'rec_td'] or changed_stat == 'targets':
            if projection.targets and projection.targets > 0:
                projection.rec_td_rate = (
                    projection.rec_td / projection.targets 
                    if projection.rec_td else 0.0
                )