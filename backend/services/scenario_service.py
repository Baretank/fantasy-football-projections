from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
import uuid
import logging

from backend.database.models import Scenario, Projection, Player, StatOverride, TeamStat
from backend.services.projection_service import ProjectionService
from backend.services.override_service import OverrideService

logger = logging.getLogger(__name__)

class ScenarioService:
    """
    Service for managing projection scenarios.
    Handles scenario creation, cloning, and application.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.projection_service = ProjectionService(db)
        self.override_service = OverrideService(db)
    
    async def create_scenario(
        self, 
        name: str, 
        description: Optional[str] = None,
        is_baseline: bool = False,
        base_scenario_id: Optional[str] = None
    ) -> Optional[Scenario]:
        """
        Create a new projection scenario.
        
        Args:
            name: Scenario name
            description: Optional description
            is_baseline: Whether this is a baseline scenario
            base_scenario_id: Optional base scenario ID
            
        Returns:
            Created Scenario object or None if failed
        """
        try:
            scenario = Scenario(
                scenario_id=str(uuid.uuid4()),
                name=name,
                description=description,
                is_baseline=is_baseline,
                base_scenario_id=base_scenario_id
            )
            
            self.db.add(scenario)
            self.db.commit()
            
            return scenario
            
        except Exception as e:
            logger.error(f"Error creating scenario: {str(e)}")
            self.db.rollback()
            return None
    
    async def get_scenario(self, scenario_id: str) -> Optional[Scenario]:
        """Get a scenario by ID."""
        return self.db.query(Scenario).filter(
            Scenario.scenario_id == scenario_id
        ).first()
    
    async def get_all_scenarios(self) -> List[Scenario]:
        """Get all scenarios."""
        return self.db.query(Scenario).all()
    
    async def get_scenario_projections(
        self, 
        scenario_id: str, 
        position: Optional[str] = None,
        team: Optional[str] = None
    ) -> List[Projection]:
        """
        Get all projections for a scenario with optional filters.
        
        Args:
            scenario_id: Scenario ID
            position: Optional position filter
            team: Optional team filter
            
        Returns:
            List of Projection objects
        """
        query = self.db.query(Projection).filter(
            Projection.scenario_id == scenario_id
        )
        
        if position or team:
            query = query.join(Player)
            
            if position:
                query = query.filter(Player.position == position)
                
            if team:
                query = query.filter(Player.team == team)
                
        return query.all()
    
    async def clone_scenario(
        self, 
        source_scenario_id: str, 
        new_name: str, 
        new_description: Optional[str] = None
    ) -> Optional[Scenario]:
        """
        Clone an existing scenario with all its projections and overrides.
        
        Args:
            source_scenario_id: Source scenario ID to clone
            new_name: Name for the new scenario
            new_description: Optional description for the new scenario
            
        Returns:
            Newly created Scenario object or None if failed
        """
        try:
            # Get source scenario
            source_scenario = await self.get_scenario(source_scenario_id)
            if not source_scenario:
                logger.error(f"Source scenario {source_scenario_id} not found")
                return None
                
            # Create new scenario
            new_scenario = await self.create_scenario(
                name=new_name,
                description=new_description,
                is_baseline=False
            )
            
            if not new_scenario:
                return None
                
            # Set base scenario reference
            new_scenario.base_scenario_id = source_scenario_id
            
            # Clone all projections
            source_projections = await self.get_scenario_projections(source_scenario_id)
            
            for source_proj in source_projections:
                # Clone the projection
                new_proj = Projection(
                    projection_id=str(uuid.uuid4()),
                    player_id=source_proj.player_id,
                    scenario_id=new_scenario.scenario_id,
                    season=source_proj.season,
                    games=source_proj.games,
                    half_ppr=source_proj.half_ppr,
                    
                    # Copy all stats
                    # Passing
                    pass_attempts=source_proj.pass_attempts,
                    completions=source_proj.completions,
                    pass_yards=source_proj.pass_yards,
                    pass_td=source_proj.pass_td,
                    interceptions=source_proj.interceptions,
                    
                    # Enhanced passing
                    gross_pass_yards=source_proj.gross_pass_yards,
                    sacks=source_proj.sacks,
                    sack_yards=source_proj.sack_yards,
                    net_pass_yards=source_proj.net_pass_yards,
                    pass_td_rate=source_proj.pass_td_rate,
                    int_rate=source_proj.int_rate,
                    sack_rate=source_proj.sack_rate,
                    
                    # Rushing
                    rush_attempts=source_proj.rush_attempts,
                    rush_yards=source_proj.rush_yards,
                    rush_td=source_proj.rush_td,
                    
                    # Enhanced rushing
                    gross_rush_yards=source_proj.gross_rush_yards,
                    fumbles=source_proj.fumbles,
                    fumble_rate=source_proj.fumble_rate,
                    net_rush_yards=source_proj.net_rush_yards,
                    rush_td_rate=source_proj.rush_td_rate,
                    
                    # Receiving
                    targets=source_proj.targets,
                    receptions=source_proj.receptions,
                    rec_yards=source_proj.rec_yards,
                    rec_td=source_proj.rec_td,
                    
                    # Usage
                    snap_share=source_proj.snap_share,
                    target_share=source_proj.target_share,
                    rush_share=source_proj.rush_share,
                    redzone_share=source_proj.redzone_share,
                    
                    # Efficiency
                    pass_att_pct=source_proj.pass_att_pct,
                    comp_pct=source_proj.comp_pct,
                    yards_per_att=source_proj.yards_per_att,
                    net_yards_per_att=source_proj.net_yards_per_att,
                    rush_att_pct=source_proj.rush_att_pct,
                    yards_per_carry=source_proj.yards_per_carry,
                    net_yards_per_carry=source_proj.net_yards_per_carry,
                    tar_pct=source_proj.tar_pct,
                    catch_pct=source_proj.catch_pct,
                    yards_per_target=source_proj.yards_per_target,
                    rec_td_rate=source_proj.rec_td_rate,
                    
                    # Override flags
                    has_overrides=source_proj.has_overrides,
                    is_fill_player=source_proj.is_fill_player
                )
                
                self.db.add(new_proj)
                
                # If source had overrides, clone those too
                if source_proj.has_overrides:
                    source_overrides = await self.override_service.get_projection_overrides(
                        source_proj.projection_id
                    )
                    
                    for override in source_overrides:
                        new_override = StatOverride(
                            override_id=str(uuid.uuid4()),
                            player_id=override.player_id,
                            projection_id=new_proj.projection_id,
                            stat_name=override.stat_name,
                            calculated_value=override.calculated_value,
                            manual_value=override.manual_value,
                            notes=f"Cloned from scenario: {source_scenario.name}"
                        )
                        
                        self.db.add(new_override)
            
            self.db.commit()
            return new_scenario
            
        except Exception as e:
            logger.error(f"Error cloning scenario: {str(e)}")
            self.db.rollback()
            return None
    
    async def update_scenario(
        self, 
        scenario_id: str, 
        data: Dict
    ) -> Optional[Scenario]:
        """
        Update scenario properties.
        
        Args:
            scenario_id: Scenario ID to update
            data: Dictionary of fields to update
            
        Returns:
            Updated Scenario object or None if failed
        """
        try:
            scenario = await self.get_scenario(scenario_id)
            if not scenario:
                logger.error(f"Scenario {scenario_id} not found")
                return None
                
            # Update fields
            for key, value in data.items():
                if hasattr(scenario, key):
                    setattr(scenario, key, value)
                    
            self.db.commit()
            return scenario
            
        except Exception as e:
            logger.error(f"Error updating scenario: {str(e)}")
            self.db.rollback()
            return None
    
    async def delete_scenario(self, scenario_id: str) -> bool:
        """
        Delete a scenario and all its projections.
        
        Args:
            scenario_id: Scenario ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            scenario = await self.get_scenario(scenario_id)
            if not scenario:
                logger.error(f"Scenario {scenario_id} not found")
                return False
                
            # Get all projections for this scenario
            projections = await self.get_scenario_projections(scenario_id)
            
            # Delete all overrides for each projection
            for projection in projections:
                overrides = await self.override_service.get_projection_overrides(
                    projection.projection_id
                )
                
                for override in overrides:
                    self.db.delete(override)
                    
                self.db.delete(projection)
                
            # Delete the scenario
            self.db.delete(scenario)
            self.db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting scenario: {str(e)}")
            self.db.rollback()
            return False
    
    async def compare_scenarios(
        self, 
        scenario_ids: List[str],
        position: Optional[str] = None
    ) -> Dict:
        """
        Compare projections across multiple scenarios.
        
        Args:
            scenario_ids: List of scenario IDs to compare
            position: Optional position filter
            
        Returns:
            Dictionary with comparison data
        """
        try:
            scenarios = []
            comparison_data = {}
            
            for scenario_id in scenario_ids:
                scenario = await self.get_scenario(scenario_id)
                if not scenario:
                    continue
                    
                scenarios.append(scenario)
                
                # Get projections for this scenario
                projections = await self.get_scenario_projections(
                    scenario_id, position=position
                )
                
                # Add projections to comparison data by player
                for proj in projections:
                    player_id = proj.player_id
                    
                    if player_id not in comparison_data:
                        # Initialize player entry with player info
                        player = self.db.query(Player).get(player_id)
                        if not player:
                            continue
                            
                        comparison_data[player_id] = {
                            "player_id": player_id,
                            "name": player.name,
                            "team": player.team,
                            "position": player.position,
                            "scenarios": {}
                        }
                    
                    # Add scenario data
                    comparison_data[player_id]["scenarios"][scenario.name] = {
                        "projection_id": proj.projection_id,
                        "half_ppr": proj.half_ppr,
                        "has_overrides": proj.has_overrides,
                        
                        # Add position-specific key stats
                        # QB stats
                        "pass_yards": proj.pass_yards,
                        "pass_td": proj.pass_td,
                        "interceptions": proj.interceptions,
                        
                        # Rushing stats
                        "rush_yards": proj.rush_yards,
                        "rush_td": proj.rush_td,
                        
                        # Receiving stats
                        "receptions": proj.receptions,
                        "rec_yards": proj.rec_yards,
                        "rec_td": proj.rec_td
                    }
            
            return {
                "scenarios": [{"id": s.scenario_id, "name": s.name} for s in scenarios],
                "players": list(comparison_data.values())
            }
            
        except Exception as e:
            logger.error(f"Error comparing scenarios: {str(e)}")
            return {"scenarios": [], "players": []}
    
    async def generate_fill_players(
        self, 
        scenario_id: str, 
        team: str, 
        season: int
    ) -> List[Projection]:
        """
        Generate fill players to reconcile team and player projections.
        
        Args:
            scenario_id: Scenario ID
            team: Team abbreviation
            season: Season year
            
        Returns:
            List of created fill player projections
        """
        try:
            # Verify scenario exists
            scenario = await self.get_scenario(scenario_id)
            if not scenario:
                logger.error(f"Scenario {scenario_id} not found")
                return []
                
            # Get team statistics
            team_stats = self.db.query(TeamStat).filter(
                and_(TeamStat.team == team, TeamStat.season == season)
            ).first()
            
            if not team_stats:
                logger.error(f"Team stats for {team} in {season} not found")
                return []
                
            # Get existing team projections for this scenario
            team_projections = await self.get_scenario_projections(
                scenario_id=scenario_id,
                team=team
            )
            
            # Calculate team totals from existing projections
            team_totals = {
                "pass_attempts": 0,
                "pass_yards": 0,
                "pass_td": 0,
                "rush_attempts": 0,
                "rush_yards": 0,
                "rush_td": 0,
                "targets": 0,
                "receptions": 0,
                "rec_yards": 0,
                "rec_td": 0
            }
            
            for proj in team_projections:
                for stat in team_totals:
                    if getattr(proj, stat) is not None:
                        team_totals[stat] += getattr(proj, stat)
            
            # Check if we need to create fill projections
            differences = {
                "pass_attempts": team_stats.pass_attempts - team_totals["pass_attempts"],
                "pass_yards": team_stats.pass_yards - team_totals["pass_yards"],
                "pass_td": team_stats.pass_td - team_totals["pass_td"],
                "rush_attempts": team_stats.rush_attempts - team_totals["rush_attempts"],
                "rush_yards": team_stats.rush_yards - team_totals["rush_yards"],
                "rush_td": team_stats.rush_td - team_totals["rush_td"],
                "targets": team_stats.targets - team_totals["targets"],
                "receptions": team_stats.receptions - team_totals["receptions"],
                "rec_yards": team_stats.rec_yards - team_totals["rec_yards"],
                "rec_td": team_stats.rec_td - team_totals["rec_td"]
            }
            
            # No need to create fill projections if everything balances
            if all(abs(v) < 0.1 for v in differences.values()):
                return []
                
            # Create fill players by position
            fill_projections = []
            
            # QB fill player (if needed)
            if differences["pass_attempts"] > 0 or differences["pass_yards"] > 0 or differences["pass_td"] > 0:
                qb_fill = await self._create_fill_player(
                    scenario_id=scenario_id,
                    team=team,
                    position="QB",
                    season=season,
                    stats={
                        "pass_attempts": max(0, differences["pass_attempts"]),
                        "pass_yards": max(0, differences["pass_yards"]),
                        "pass_td": max(0, differences["pass_td"]),
                        "rush_attempts": 0,
                        "rush_yards": 0,
                        "rush_td": 0
                    }
                )
                if qb_fill:
                    fill_projections.append(qb_fill)
            
            # RB fill player (if needed)
            if differences["rush_attempts"] > 0 or differences["rush_yards"] > 0 or differences["rush_td"] > 0:
                rb_fill = await self._create_fill_player(
                    scenario_id=scenario_id,
                    team=team,
                    position="RB",
                    season=season,
                    stats={
                        "rush_attempts": max(0, differences["rush_attempts"]),
                        "rush_yards": max(0, differences["rush_yards"]),
                        "rush_td": max(0, differences["rush_td"]),
                        "targets": 0,
                        "receptions": 0,
                        "rec_yards": 0,
                        "rec_td": 0
                    }
                )
                if rb_fill:
                    fill_projections.append(rb_fill)
            
            # WR fill player (if needed)
            if differences["targets"] > 0 or differences["receptions"] > 0 or differences["rec_yards"] > 0 or differences["rec_td"] > 0:
                wr_fill = await self._create_fill_player(
                    scenario_id=scenario_id,
                    team=team,
                    position="WR",
                    season=season,
                    stats={
                        "targets": max(0, differences["targets"]),
                        "receptions": max(0, differences["receptions"]),
                        "rec_yards": max(0, differences["rec_yards"]),
                        "rec_td": max(0, differences["rec_td"])
                    }
                )
                if wr_fill:
                    fill_projections.append(wr_fill)
                    
            return fill_projections
            
        except Exception as e:
            logger.error(f"Error generating fill players: {str(e)}")
            self.db.rollback()
            return []
            
    async def add_player_to_scenario(
        self,
        scenario_id: str,
        player_id: str,
        adjustments: Dict[str, float]
    ) -> Optional[Projection]:
        """
        Add a player to a scenario with specific stat adjustments.
        
        Args:
            scenario_id: The scenario ID
            player_id: The player ID to add to scenario
            adjustments: Dictionary of stat adjustments to apply
            
        Returns:
            Created scenario projection or None if failed
        """
        try:
            # Verify scenario exists
            scenario = await self.get_scenario(scenario_id)
            if not scenario:
                logger.error(f"Scenario {scenario_id} not found")
                return None
                
            # Get the player
            player = self.db.query(Player).filter(Player.player_id == player_id).first()
            if not player:
                logger.error(f"Player {player_id} not found")
                return None
                
            # Check if player already has a projection in this scenario
            existing_proj = self.db.query(Projection).filter(
                and_(
                    Projection.player_id == player_id,
                    Projection.scenario_id == scenario_id
                )
            ).first()
            
            if existing_proj:
                # Update existing projection
                for stat, value in adjustments.items():
                    if hasattr(existing_proj, stat):
                        setattr(existing_proj, stat, value)
                
                # Recalculate fantasy points
                if hasattr(existing_proj, "calculate_fantasy_points"):
                    existing_proj.half_ppr = existing_proj.calculate_fantasy_points()
                
                self.db.commit()
                return existing_proj
            
            # Find the base projection for this player
            base_proj = self.db.query(Projection).filter(
                and_(
                    Projection.player_id == player_id,
                    Projection.scenario_id.is_(None)
                )
            ).order_by(Projection.created_at.desc()).first()
            
            if not base_proj:
                logger.error(f"No base projection found for player {player_id}")
                return None
                
            # Create a new projection for this scenario
            new_proj = Projection(
                projection_id=str(uuid.uuid4()),
                player_id=player_id,
                scenario_id=scenario_id,
                season=base_proj.season,
                games=base_proj.games,
                half_ppr=base_proj.half_ppr
            )
            
            # Copy all stats from base projection
            for column in Projection.__table__.columns:
                if column.name not in ['projection_id', 'player_id', 'scenario_id', 'created_at', 'updated_at']:
                    setattr(new_proj, column.name, getattr(base_proj, column.name))
            
            # Apply adjustments
            for stat, value in adjustments.items():
                if hasattr(new_proj, stat):
                    setattr(new_proj, stat, value)
            
            # Recalculate fantasy points
            if hasattr(new_proj, "calculate_fantasy_points"):
                new_proj.half_ppr = new_proj.calculate_fantasy_points()
            
            self.db.add(new_proj)
            self.db.commit()
            
            return new_proj
            
        except Exception as e:
            logger.error(f"Error adding player to scenario: {str(e)}")
            self.db.rollback()
            return None
    
    async def get_player_scenario_projection(
        self,
        scenario_id: str,
        player_id: str
    ) -> Optional[Projection]:
        """
        Get a player's projection for a specific scenario.
        
        Args:
            scenario_id: The scenario ID
            player_id: The player ID
            
        Returns:
            Projection object or None if not found
        """
        try:
            return self.db.query(Projection).filter(
                and_(
                    Projection.player_id == player_id,
                    Projection.scenario_id == scenario_id
                )
            ).first()
        except Exception as e:
            logger.error(f"Error getting player scenario projection: {str(e)}")
            return None
            
    async def _create_fill_player(
        self,
        scenario_id: str,
        team: str,
        position: str,
        season: int,
        stats: Dict
    ) -> Optional[Projection]:
        """
        Helper method to create a fill player projection.
        
        Args:
            scenario_id: Scenario ID
            team: Team abbreviation
            position: Player position
            season: Season year
            stats: Dictionary of stats to set
            
        Returns:
            Created Projection object or None if failed
        """
        try:
            # Create a fill player
            player_name = f"{team} Fill {position}"
            player_id = None
            
            # Check if fill player already exists
            existing_player = self.db.query(Player).filter(
                and_(Player.name == player_name, Player.team == team)
            ).first()
            
            if existing_player:
                player_id = existing_player.player_id
            else:
                # Create new fill player
                new_player = Player(
                    player_id=str(uuid.uuid4()),
                    name=player_name,
                    team=team,
                    position=position,
                    is_fill_player=True
                )
                self.db.add(new_player)
                self.db.flush()
                player_id = new_player.player_id
                
            # Check if this player already has a projection in this scenario
            existing_projection = self.db.query(Projection).filter(
                and_(
                    Projection.player_id == player_id,
                    Projection.scenario_id == scenario_id
                )
            ).first()
            
            if existing_projection:
                # Update existing projection
                for stat, value in stats.items():
                    if hasattr(existing_projection, stat):
                        setattr(existing_projection, stat, value)
                
                existing_projection.is_fill_player = True
                self.db.commit()
                return existing_projection
            else:
                # Create new projection with fill stats
                projection = Projection(
                    projection_id=str(uuid.uuid4()),
                    player_id=player_id,
                    scenario_id=scenario_id,
                    season=season,
                    games=17,  # Default to full season
                    is_fill_player=True,
                    has_overrides=False
                )
                
                # Set all the stats
                for stat, value in stats.items():
                    if hasattr(projection, stat):
                        setattr(projection, stat, value)
                        
                # Calculate half_ppr points
                half_ppr = 0
                if position == "QB":
                    half_ppr = (
                        stats.get("pass_td", 0) * 4 +
                        stats.get("pass_yards", 0) * 0.04 +
                        stats.get("rush_td", 0) * 6 +
                        stats.get("rush_yards", 0) * 0.1
                    )
                elif position in ["RB", "WR", "TE"]:
                    half_ppr = (
                        stats.get("rush_td", 0) * 6 +
                        stats.get("rush_yards", 0) * 0.1 +
                        stats.get("rec_td", 0) * 6 +
                        stats.get("rec_yards", 0) * 0.1 +
                        stats.get("receptions", 0) * 0.5
                    )
                    
                projection.half_ppr = half_ppr
                
                self.db.add(projection)
                self.db.commit()
                return projection
                
        except Exception as e:
            logger.error(f"Error creating fill player: {str(e)}")
            self.db.rollback()
            return None