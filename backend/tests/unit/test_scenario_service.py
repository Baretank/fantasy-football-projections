import pytest
import uuid
from sqlalchemy.orm import Session
from backend.services.scenario_service import ScenarioService
from backend.database.models import Scenario, Projection, Player, StatOverride

class TestScenarioService:
    @pytest.fixture(scope="function")
    def service(self, test_db):
        """Create ScenarioService instance for testing."""
        return ScenarioService(test_db)

    @pytest.fixture(scope="function")
    def baseline_scenario(self, service):
        """Create a baseline scenario for testing."""
        @pytest.mark.asyncio
        async def _create_baseline():
            scenario = await service.create_scenario(
                name="Baseline 2024",
                description="Standard baseline projections",
                is_baseline=True
            )
            return scenario
            
        return _create_baseline()

    @pytest.fixture(scope="function")
    def sample_projections(self, test_db, sample_players, baseline_scenario):
        """Create sample projections in the baseline scenario."""
        @pytest.mark.asyncio
        async def _create_projections():
            scenario = await baseline_scenario
            projections = []
            
            # Create QB projection
            mahomes_id = sample_players["ids"]["Patrick Mahomes"]
            qb_proj = Projection(
                projection_id=str(uuid.uuid4()),
                player_id=mahomes_id,
                scenario_id=scenario.scenario_id,
                season=2024,
                games=17,
                half_ppr=350.5,
                pass_attempts=600,
                completions=400,
                pass_yards=4800,
                pass_td=38,
                interceptions=10,
                has_overrides=False
            )
            projections.append(qb_proj)
            
            # Create RB projection
            mccaffrey_id = sample_players["ids"]["Christian McCaffrey"]
            rb_proj = Projection(
                projection_id=str(uuid.uuid4()),
                player_id=mccaffrey_id,
                scenario_id=scenario.scenario_id,
                season=2024,
                games=16,
                half_ppr=320.5,
                carries=280,
                rush_yards=1400,
                rush_td=14,
                targets=110,
                receptions=88,
                rec_yards=750,
                rec_td=5,
                has_overrides=False
            )
            projections.append(rb_proj)
            
            # Create TE projection
            kelce_id = sample_players["ids"]["Travis Kelce"]
            te_proj = Projection(
                projection_id=str(uuid.uuid4()),
                player_id=kelce_id,
                scenario_id=scenario.scenario_id,
                season=2024,
                games=16,
                half_ppr=245.0,
                targets=140,
                receptions=98,
                rec_yards=1200,
                rec_td=10,
                has_overrides=False
            )
            projections.append(te_proj)
            
            for proj in projections:
                test_db.add(proj)
            
            test_db.commit()
            return {"scenario": scenario, "projections": projections}
            
        return _create_projections()

    @pytest.fixture(scope="function")
    def scenario_with_overrides(self, test_db, service, sample_projections):
        """Create a scenario with some overrides applied."""
        @pytest.mark.asyncio
        async def _create_scenario_with_overrides():
            result = await sample_projections
            projections = result["projections"]
            qb_proj = projections[0]
            
            # Create an override
            override = StatOverride(
                override_id=str(uuid.uuid4()),
                player_id=qb_proj.player_id,
                projection_id=qb_proj.projection_id,
                stat_name="pass_td",
                calculated_value=38.0,
                manual_value=45.0,
                notes="Added more TDs for testing"
            )
            
            # Update the projection to reflect the override
            qb_proj.pass_td = 45
            qb_proj.has_overrides = True
            
            test_db.add(override)
            test_db.commit()
            
            return {"scenario": result["scenario"], "projections": projections, "override": override}
            
        return _create_scenario_with_overrides()

    @pytest.mark.asyncio
    async def test_create_scenario(self, service):
        """Test creating a new scenario."""
        scenario = await service.create_scenario(
            name="Test Scenario",
            description="A test scenario",
            is_baseline=False
        )
        
        assert scenario is not None
        assert scenario.name == "Test Scenario"
        assert scenario.description == "A test scenario"
        assert scenario.is_baseline is False
        
        # Verify it exists in the database
        stored_scenario = await service.get_scenario(scenario.scenario_id)
        assert stored_scenario is not None
        assert stored_scenario.scenario_id == scenario.scenario_id

    @pytest.mark.asyncio
    async def test_get_scenario_projections(self, service, sample_projections):
        """Test retrieving projections for a scenario."""
        result = await sample_projections
        scenario = result["scenario"]
        
        # Get all projections
        projections = await service.get_scenario_projections(scenario.scenario_id)
        assert len(projections) == 3  # We created 3 projections
        
        # Filter by position
        qb_projections = await service.get_scenario_projections(
            scenario.scenario_id, 
            position="QB"
        )
        assert len(qb_projections) == 1
        assert qb_projections[0].player.position == "QB"
        
        # Filter by team
        kc_projections = await service.get_scenario_projections(
            scenario.scenario_id, 
            team="KC"
        )
        assert len(kc_projections) == 2  # Mahomes and Kelce are on KC
        
        # Filter by position and team
        kc_qb_projections = await service.get_scenario_projections(
            scenario.scenario_id, 
            position="QB", 
            team="KC"
        )
        assert len(kc_qb_projections) == 1
        assert kc_qb_projections[0].player.name == "Patrick Mahomes"

    @pytest.mark.asyncio
    async def test_clone_scenario(self, service, scenario_with_overrides):
        """Test cloning a scenario with all its projections and overrides."""
        result = await scenario_with_overrides
        source_scenario = result["scenario"]
        
        # Clone the scenario
        cloned_scenario = await service.clone_scenario(
            source_scenario_id=source_scenario.scenario_id,
            new_name="Cloned Scenario",
            new_description="A clone for testing"
        )
        
        assert cloned_scenario is not None
        assert cloned_scenario.name == "Cloned Scenario"
        assert cloned_scenario.base_scenario_id == source_scenario.scenario_id
        
        # Verify projections were cloned
        source_projections = await service.get_scenario_projections(source_scenario.scenario_id)
        cloned_projections = await service.get_scenario_projections(cloned_scenario.scenario_id)
        
        assert len(cloned_projections) == len(source_projections)
        
        # Check that the QB projection with override was cloned correctly
        source_qb_proj = next(p for p in source_projections if p.player.position == "QB")
        cloned_qb_proj = next(p for p in cloned_projections if p.player.position == "QB")
        
        assert source_qb_proj.pass_td == cloned_qb_proj.pass_td == 45
        assert source_qb_proj.has_overrides == cloned_qb_proj.has_overrides is True
        
        # Verify that overrides were cloned
        cloned_overrides = await service.override_service.get_projection_overrides(
            cloned_qb_proj.projection_id
        )
        
        assert len(cloned_overrides) == 1
        assert cloned_overrides[0].stat_name == "pass_td"
        assert cloned_overrides[0].manual_value == 45.0

    @pytest.mark.asyncio
    async def test_update_scenario(self, service, baseline_scenario):
        """Test updating scenario properties."""
        scenario = await baseline_scenario
        
        # Update the scenario
        updated_scenario = await service.update_scenario(
            scenario_id=scenario.scenario_id,
            data={
                "name": "Updated Baseline",
                "description": "Updated description",
                "is_baseline": False
            }
        )
        
        assert updated_scenario is not None
        assert updated_scenario.name == "Updated Baseline"
        assert updated_scenario.description == "Updated description"
        assert updated_scenario.is_baseline is False

    @pytest.mark.asyncio
    async def test_delete_scenario(self, service, scenario_with_overrides):
        """Test deleting a scenario and all its projections and overrides."""
        result = await scenario_with_overrides
        scenario = result["scenario"]
        
        # Verify the scenario exists with projections and overrides
        projections = await service.get_scenario_projections(scenario.scenario_id)
        assert len(projections) == 3
        
        qb_proj = next(p for p in projections if p.player.position == "QB")
        overrides = await service.override_service.get_projection_overrides(qb_proj.projection_id)
        assert len(overrides) == 1
        
        # Delete the scenario
        success = await service.delete_scenario(scenario.scenario_id)
        assert success is True
        
        # Verify the scenario no longer exists
        deleted_scenario = await service.get_scenario(scenario.scenario_id)
        assert deleted_scenario is None
        
        # Verify projections were deleted
        remaining_projections = service.db.query(Projection).filter(
            Projection.scenario_id == scenario.scenario_id
        ).count()
        assert remaining_projections == 0
        
        # Verify overrides were deleted
        remaining_overrides = service.db.query(StatOverride).filter(
            StatOverride.projection_id == qb_proj.projection_id
        ).count()
        assert remaining_overrides == 0

    @pytest.mark.asyncio
    async def test_compare_scenarios(self, service, baseline_scenario, sample_projections):
        """Test comparing projections across scenarios."""
        base_scenario = await baseline_scenario
        base_result = await sample_projections
        
        # Create a second scenario with slightly different projections
        alt_scenario = await service.create_scenario(
            name="Alternative Scenario",
            description="Higher scoring environment",
            is_baseline=False
        )
        
        # Clone base projections to alternative scenario
        cloned_scenario = await service.clone_scenario(
            source_scenario_id=base_scenario.scenario_id,
            new_name=alt_scenario.name,
            new_description=alt_scenario.description
        )
        
        # Modify a projection in the alternative scenario
        alt_projections = await service.get_scenario_projections(cloned_scenario.scenario_id)
        qb_proj = next(p for p in alt_projections if p.player.position == "QB")
        
        # Apply an override to increase passing TDs
        override = await service.override_service.create_override(
            player_id=qb_proj.player_id,
            projection_id=qb_proj.projection_id,
            stat_name="pass_td",
            manual_value=48,  # Higher than the 38 in baseline
            notes="Aggressive TD projection"
        )
        
        # Now compare the scenarios
        comparison = await service.compare_scenarios(
            scenario_ids=[base_scenario.scenario_id, cloned_scenario.scenario_id]
        )
        
        assert "scenarios" in comparison
        assert "players" in comparison
        assert len(comparison["scenarios"]) == 2
        assert len(comparison["players"]) == 3  # We have 3 players
        
        # Find the QB player in the comparison
        qb_comparison = next(p for p in comparison["players"] if p["position"] == "QB")
        
        # Verify both scenarios are present with different values
        assert "Baseline 2024" in qb_comparison["scenarios"]
        assert "Alternative Scenario" in qb_comparison["scenarios"]
        
        base_pass_td = qb_comparison["scenarios"]["Baseline 2024"]["pass_td"]
        alt_pass_td = qb_comparison["scenarios"]["Alternative Scenario"]["pass_td"]
        
        assert base_pass_td == 38
        assert alt_pass_td == 48
        
        # Verify fantasy points increased in alternative scenario
        base_half_ppr = qb_comparison["scenarios"]["Baseline 2024"]["half_ppr"]
        alt_half_ppr = qb_comparison["scenarios"]["Alternative Scenario"]["half_ppr"]
        
        assert alt_half_ppr > base_half_ppr
        
    @pytest.mark.asyncio
    async def test_get_all_scenarios(self, service, baseline_scenario):
        """Test retrieving all scenarios."""
        base_scenario = await baseline_scenario
        
        # Create a second scenario
        alt_scenario = await service.create_scenario(
            name="Alternative Scenario",
            description="Another test scenario",
            is_baseline=False
        )
        
        # Get all scenarios
        scenarios = await service.get_all_scenarios()
        
        assert len(scenarios) >= 2  # At least our two scenarios
        assert any(s.scenario_id == base_scenario.scenario_id for s in scenarios)
        assert any(s.scenario_id == alt_scenario.scenario_id for s in scenarios)