import pytest
import uuid
from datetime import datetime
from sqlalchemy import and_

from backend.services.scenario_service import ScenarioService
from backend.services.projection_service import ProjectionService
from backend.database.models import Player, Projection, Scenario

class TestScenarios:
    @pytest.fixture(scope="function")
    def services(self, test_db):
        """Create services needed for testing."""
        return {
            "scenario": ScenarioService(test_db),
            "projection": ProjectionService(test_db)
        }
    
    @pytest.fixture(scope="function")
    def setup_scenario_data(self, test_db):
        """Set up minimal test data for scenario testing."""
        # Create test players
        players = [
            Player(player_id=str(uuid.uuid4()), name="Test QB", team="KC", position="QB"),
            Player(player_id=str(uuid.uuid4()), name="Test RB", team="KC", position="RB"),
            Player(player_id=str(uuid.uuid4()), name="Test WR1", team="KC", position="WR"),
            Player(player_id=str(uuid.uuid4()), name="Test WR2", team="KC", position="WR"),
            Player(player_id=str(uuid.uuid4()), name="Test TE", team="KC", position="TE")
        ]
        
        # Add players to database
        for player in players:
            test_db.add(player)
        
        # Current season
        current_season = datetime.now().year
        
        # Create base projections
        projections = []
        for player in players:
            if player.position == "QB":
                proj = Projection(
                    projection_id=str(uuid.uuid4()),
                    player_id=player.player_id,
                    season=current_season,
                    games=17,
                    completions=390,
                    pass_attempts=600,
                    pass_yards=4500,
                    pass_td=35,
                    interceptions=10,
                    carries=50,
                    rush_yards=250,
                    rush_td=2,
                    half_ppr=300
                )
            elif player.position == "RB":
                proj = Projection(
                    projection_id=str(uuid.uuid4()),
                    player_id=player.player_id,
                    season=current_season,
                    games=16,
                    carries=250,
                    rush_yards=1200,
                    rush_td=10,
                    targets=60,
                    receptions=50,
                    rec_yards=400,
                    rec_td=2,
                    half_ppr=245
                )
            elif player.position == "WR" and player.name.endswith("WR1"):
                proj = Projection(
                    projection_id=str(uuid.uuid4()),
                    player_id=player.player_id,
                    season=current_season,
                    games=17,
                    targets=150,
                    receptions=100,
                    rec_yards=1400,
                    rec_td=10,
                    carries=10,
                    rush_yards=60,
                    rush_td=0,
                    half_ppr=250
                )
            elif player.position == "WR" and player.name.endswith("WR2"):
                proj = Projection(
                    projection_id=str(uuid.uuid4()),
                    player_id=player.player_id,
                    season=current_season,
                    games=17,
                    targets=120,
                    receptions=80,
                    rec_yards=1000,
                    rec_td=7,
                    carries=5,
                    rush_yards=25,
                    rush_td=0,
                    half_ppr=182
                )
            elif player.position == "TE":
                proj = Projection(
                    projection_id=str(uuid.uuid4()),
                    player_id=player.player_id,
                    season=current_season,
                    games=16,
                    targets=100,
                    receptions=75,
                    rec_yards=850,
                    rec_td=8,
                    half_ppr=170.5
                )
            
            projections.append(proj)
            test_db.add(proj)
        
        test_db.commit()
        
        return {
            "players": {p.position + (p.name[-1] if p.position == "WR" else ""): p for p in players},
            "player_list": players,
            "projections": {p.player_id: proj for p, proj in zip(players, projections)},
            "projection_list": projections,
            "current_season": current_season
        }
    
    @pytest.mark.asyncio
    async def test_create_scenario(self, services, setup_scenario_data, test_db):
        """Test creating a new scenario."""
        # Create a new scenario
        scenario = await services["scenario"].create_scenario(
            name="Test Scenario",
            description="A test scenario for unit testing"
        )
        
        # Verify the scenario was created
        assert scenario is not None
        assert scenario.name == "Test Scenario"
        assert scenario.description == "A test scenario for unit testing"
        assert scenario.scenario_id  # Should have an ID
        
        # Verify it's in the database
        db_scenario = test_db.query(Scenario).filter(
            Scenario.scenario_id == scenario.scenario_id
        ).first()
        
        assert db_scenario is not None
        assert db_scenario.name == scenario.name
    
    @pytest.mark.asyncio
    async def test_add_player_to_scenario(self, services, setup_scenario_data, test_db):
        """Test adding a player to a scenario with adjustments."""
        # Create a new scenario
        scenario = await services["scenario"].create_scenario(
            name="QB Injury Scenario",
            description="QB misses 4 games"
        )
        
        # Get a QB player and their original projection
        qb_player = setup_scenario_data["players"]["QB"]
        original_proj = setup_scenario_data["projections"][qb_player.player_id]
        
        # Add player to scenario with 25% reduction in key stats due to injury
        adjustments = {
            'games': original_proj.games * 0.75,  # Missing 4 games in a 16-game season
            'pass_attempts': original_proj.pass_attempts * 0.75,
            'pass_yards': original_proj.pass_yards * 0.75,
            'pass_td': original_proj.pass_td * 0.75
        }
        
        scenario_proj = await services["scenario"].add_player_to_scenario(
            scenario_id=scenario.scenario_id,
            player_id=qb_player.player_id,
            adjustments=adjustments
        )
        
        # Verify the projection was created and adjustments applied
        assert scenario_proj is not None
        assert scenario_proj.scenario_id == scenario.scenario_id
        assert scenario_proj.player_id == qb_player.player_id
        
        # Verify stats reflect the adjustments
        assert abs(scenario_proj.games - adjustments['games']) < 0.01
        assert abs(scenario_proj.pass_attempts - adjustments['pass_attempts']) < 0.01
        assert abs(scenario_proj.pass_yards - adjustments['pass_yards']) < 0.01
        assert abs(scenario_proj.pass_td - adjustments['pass_td']) < 0.01
        
        # Fantasy points should be lower than original
        assert scenario_proj.half_ppr < original_proj.half_ppr
    
    @pytest.mark.asyncio
    async def test_get_player_scenario_projection(self, services, setup_scenario_data, test_db):
        """Test retrieving a player's scenario projection."""
        # Create a new scenario
        scenario = await services["scenario"].create_scenario(
            name="WR Improvement Scenario",
            description="WR2 gets more targets"
        )
        
        # Get a WR player and their original projection
        wr_player = setup_scenario_data["players"]["WR2"]
        original_proj = setup_scenario_data["projections"][wr_player.player_id]
        
        # Add player to scenario with 20% increase in targets and yards
        adjustments = {
            'targets': original_proj.targets * 1.2,
            'receptions': original_proj.receptions * 1.2,
            'rec_yards': original_proj.rec_yards * 1.2,
            'rec_td': original_proj.rec_td * 1.2
        }
        
        # Add to scenario
        await services["scenario"].add_player_to_scenario(
            scenario_id=scenario.scenario_id,
            player_id=wr_player.player_id,
            adjustments=adjustments
        )
        
        # Now retrieve the projection
        scenario_proj = await services["scenario"].get_player_scenario_projection(
            scenario_id=scenario.scenario_id,
            player_id=wr_player.player_id
        )
        
        # Verify the projection was retrieved
        assert scenario_proj is not None
        assert scenario_proj.scenario_id == scenario.scenario_id
        assert scenario_proj.player_id == wr_player.player_id
        
        # Verify stats reflect the adjustments
        assert abs(scenario_proj.targets - adjustments['targets']) < 0.01
        assert abs(scenario_proj.receptions - adjustments['receptions']) < 0.01
        assert abs(scenario_proj.rec_yards - adjustments['rec_yards']) < 0.01
        assert abs(scenario_proj.rec_td - adjustments['rec_td']) < 0.01
        
        # Fantasy points should be higher than original
        assert scenario_proj.half_ppr > original_proj.half_ppr
    
    @pytest.mark.asyncio
    async def test_update_player_in_scenario(self, services, setup_scenario_data, test_db):
        """Test updating a player already in a scenario."""
        # Create a new scenario
        scenario = await services["scenario"].create_scenario(
            name="RB Usage Changes",
            description="RB gets more usage"
        )
        
        # Get a RB player and their original projection
        rb_player = setup_scenario_data["players"]["RB"]
        original_proj = setup_scenario_data["projections"][rb_player.player_id]
        
        # Initial adjustments
        initial_adjustments = {
            'carries': original_proj.carries * 1.1,
            'rush_yards': original_proj.rush_yards * 1.1
        }
        
        # Add to scenario
        await services["scenario"].add_player_to_scenario(
            scenario_id=scenario.scenario_id,
            player_id=rb_player.player_id,
            adjustments=initial_adjustments
        )
        
        # New adjustments - increase even more and add TD adjustment
        new_adjustments = {
            'carries': original_proj.carries * 1.2,
            'rush_yards': original_proj.rush_yards * 1.2,
            'rush_td': original_proj.rush_td * 1.15
        }
        
        # Update player in scenario
        updated_proj = await services["scenario"].add_player_to_scenario(
            scenario_id=scenario.scenario_id,
            player_id=rb_player.player_id,
            adjustments=new_adjustments
        )
        
        # Verify the updated projection
        assert updated_proj is not None
        assert updated_proj.scenario_id == scenario.scenario_id
        assert updated_proj.player_id == rb_player.player_id
        
        # Verify stats reflect the new adjustments
        assert abs(updated_proj.carries - new_adjustments['carries']) < 0.01
        assert abs(updated_proj.rush_yards - new_adjustments['rush_yards']) < 0.01
        assert abs(updated_proj.rush_td - new_adjustments['rush_td']) < 0.01
        
        # Should be different from the initial adjustment
        assert updated_proj.carries > original_proj.carries * 1.1
    
    @pytest.mark.asyncio
    async def test_complex_multi_player_scenario(self, services, setup_scenario_data, test_db):
        """Test a more complex scenario with multiple players affected."""
        # Create a scenario where the QB is injured, WR1 loses value, and RB gains value
        scenario = await services["scenario"].create_scenario(
            name="Complex Team Scenario",
            description="QB injured, RB gains value, WR1 loses value"
        )
        
        # Get the players and their original projections
        qb_player = setup_scenario_data["players"]["QB"]
        rb_player = setup_scenario_data["players"]["RB"]
        wr1_player = setup_scenario_data["players"]["WR1"]
        
        qb_proj = setup_scenario_data["projections"][qb_player.player_id]
        rb_proj = setup_scenario_data["projections"][rb_player.player_id]
        wr1_proj = setup_scenario_data["projections"][wr1_player.player_id]
        
        # 1. QB misses time
        qb_adjustments = {
            'games': qb_proj.games * 0.75,
            'pass_attempts': qb_proj.pass_attempts * 0.75,
            'pass_yards': qb_proj.pass_yards * 0.75,
            'pass_td': qb_proj.pass_td * 0.75
        }
        
        await services["scenario"].add_player_to_scenario(
            scenario_id=scenario.scenario_id,
            player_id=qb_player.player_id,
            adjustments=qb_adjustments
        )
        
        # 2. Team becomes more run-focused with backup QB, RB benefits
        rb_adjustments = {
            'carries': rb_proj.carries * 1.2,
            'rush_yards': rb_proj.rush_yards * 1.2,
            'rush_td': rb_proj.rush_td * 1.25
        }
        
        await services["scenario"].add_player_to_scenario(
            scenario_id=scenario.scenario_id,
            player_id=rb_player.player_id,
            adjustments=rb_adjustments
        )
        
        # 3. WR1 loses value with backup QB
        wr1_adjustments = {
            'targets': wr1_proj.targets * 0.85,
            'receptions': wr1_proj.receptions * 0.8,  # Worse catch rate with backup
            'rec_yards': wr1_proj.rec_yards * 0.8,
            'rec_td': wr1_proj.rec_td * 0.7  # Big drop in TDs
        }
        
        await services["scenario"].add_player_to_scenario(
            scenario_id=scenario.scenario_id,
            player_id=wr1_player.player_id,
            adjustments=wr1_adjustments
        )
        
        # Get all scenario projections and verify
        qb_scenario_proj = await services["scenario"].get_player_scenario_projection(
            scenario_id=scenario.scenario_id,
            player_id=qb_player.player_id
        )
        
        rb_scenario_proj = await services["scenario"].get_player_scenario_projection(
            scenario_id=scenario.scenario_id,
            player_id=rb_player.player_id
        )
        
        wr1_scenario_proj = await services["scenario"].get_player_scenario_projection(
            scenario_id=scenario.scenario_id,
            player_id=wr1_player.player_id
        )
        
        # Verify all projections exist
        assert qb_scenario_proj is not None
        assert rb_scenario_proj is not None
        assert wr1_scenario_proj is not None
        
        # Verify fantasy points reflect the narrative
        assert qb_scenario_proj.half_ppr < qb_proj.half_ppr  # QB loses value
        assert rb_scenario_proj.half_ppr > rb_proj.half_ppr  # RB gains value
        assert wr1_scenario_proj.half_ppr < wr1_proj.half_ppr  # WR1 loses value
        
        # Sanity check the consistency of the scenario
        # QB passing yards + WR receiving yards should be consistent
        # Sum of QB passing TDs should be <= passing attempts, etc.
        
        # Verify that the relative changes make sense
        # QB and WR1 should both lose value by similar percentages
        qb_value_change = qb_scenario_proj.half_ppr / qb_proj.half_ppr
        wr1_value_change = wr1_scenario_proj.half_ppr / wr1_proj.half_ppr
        
        # Both should lose roughly 25% of value
        assert 0.7 <= qb_value_change <= 0.8
        assert 0.7 <= wr1_value_change <= 0.8
        
        # RB should gain value
        rb_value_change = rb_scenario_proj.half_ppr / rb_proj.half_ppr
        assert rb_value_change > 1.1