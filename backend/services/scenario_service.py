from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
import uuid
import logging

from backend.database.models import Scenario, Projection, Player, StatOverride
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
        is_baseline: bool = False
    ) -> Optional[Scenario]:
        """
        Create a new projection scenario.
        
        Args:
            name: Scenario name
            description: Optional description
            is_baseline: Whether this is a baseline scenario
            
        Returns:
            Created Scenario object or None if failed
        """
        try:
            scenario = Scenario(
                scenario_id=str(uuid.uuid4()),
                name=name,
                description=description,
                is_baseline=is_baseline
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
                    carries=source_proj.carries,
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
                    car_pct=source_proj.car_pct,
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
        # Implementation will be added in future development phase
        pass