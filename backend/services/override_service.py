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
            'carries': ['rush_yards', 'yards_per_carry'],
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
            
            # Recalculate fantasy points
            projection.half_ppr = projection.calculate_fantasy_points()
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
                
            # Recalculate fantasy points
            projection.half_ppr = projection.calculate_fantasy_points()
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
            
            # Recalculate fantasy points
            projection.half_ppr = projection.calculate_fantasy_points()
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
        # Skip if the changed stat has no dependencies
        if changed_stat not in self.dependent_stats:
            return
            
        # Get the player for position-specific calculations
        player = self.db.query(Player).filter(
            Player.player_id == projection.player_id
        ).first()
        
        if not player:
            logger.error(f"Player {projection.player_id} not found")
            return
            
        # Get current values
        current_values = {}
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
        # Handle rushing efficiency metrics
        if changed_stat in ['carries', 'rush_yards']:
            if projection.carries and projection.carries > 0:
                projection.yards_per_carry = (
                    projection.rush_yards / projection.carries 
                    if projection.rush_yards else 0.0
                )
        
        if changed_stat in ['carries', 'rush_td']:
            if projection.carries and projection.carries > 0:
                projection.rush_td_rate = (
                    projection.rush_td / projection.carries 
                    if projection.rush_td else 0.0
                )
        
        # Handle fumble metrics
        if changed_stat == 'fumbles':
            if projection.fumbles is not None and projection.carries:
                projection.fumble_rate = (
                    projection.fumbles / projection.carries 
                    if projection.carries > 0 else 0.0
                )
        
        if changed_stat in ['rush_yards', 'fumbles']:
            # Estimate yards lost due to fumbles (approximately 5 yards per fumble)
            if projection.rush_yards is not None:
                fumble_yards = projection.fumbles * 5.0 if projection.fumbles else 0.0
                projection.net_rush_yards = projection.rush_yards - fumble_yards
                
                # Recalculate net yards per carry
                if projection.carries and projection.carries > 0:
                    projection.net_yards_per_carry = (
                        projection.net_rush_yards / projection.carries
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
        # Efficiency metrics are similar to RB receiving stats
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