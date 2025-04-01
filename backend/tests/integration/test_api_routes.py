import pytest
from fastapi.testclient import TestClient
import uuid
from datetime import datetime
from typing import Dict, List, Any, Generator
import logging

from backend.database.models import Player, BaseStat, TeamStat, Projection, Scenario, StatOverride

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_health_endpoint(client, log_route_endpoints):
    """Test the health endpoint."""
    response = client.get("/api/health")
    logger.debug(f"Health endpoint status: {response.status_code}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    
    # Log all API routes for debugging
    logger.debug(f"API routes check:")
    routes = [r for r in log_route_endpoints if r["path"].startswith("/api/")]
    logger.debug(f"Found {len(routes)} API routes")
    for route in routes:
        logger.debug(f"{route['path']}")
    
    # Verify we have routes for all key resources
    player_routes = [r for r in routes if r["path"].startswith("/api/players")]
    assert len(player_routes) > 0, "No player API routes found"

class TestPlayerRoutes:
    """Integration tests for player-related routes"""
    
    def test_get_players(self, client, sample_players):
        """Test getting all players with pagination."""
        response = client.get("/api/players/players/")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check pagination
        assert "pagination" in data
        assert data["pagination"]["total_count"] == len(sample_players["players"])
        
        # Check player data
        assert "players" in data
        player_names = [p["name"] for p in data["players"]]
        for player in sample_players["players"]:
            assert player.name in player_names
    
    def test_player_by_id(self, client, sample_players):
        """Test getting a player by ID."""
        player_id = sample_players["ids"]["Patrick Mahomes"]
        
        response = client.get(f"/api/players/players/{player_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["player_id"] == player_id
        assert data["name"] == "Patrick Mahomes"
        assert data["position"] == "QB"
        assert data["team"] == "KC"
    
    def test_player_search(self, client, sample_players):
        """Test player search functionality."""
        # Search by name
        response = client.get("/api/players/players/search?query=Maho")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] > 0
        assert "Patrick Mahomes" in [p["name"] for p in data["players"]]
        
        # Search with position filter
        response = client.get("/api/players/players/search?query=Ma&position=QB")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] > 0
        player_positions = [p["position"] for p in data["players"]]
        assert all(pos == "QB" for pos in player_positions)
    
    def test_update_player_status(self, client, sample_players, test_db):
        """Test updating a player's status."""
        player_id = sample_players["ids"]["Patrick Mahomes"]
        
        # Update status to Injured
        response = client.put(f"/api/players/players/{player_id}/status?status=Injured")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "Injured"
        
        # Verify in database
        player = test_db.query(Player).filter(Player.player_id == player_id).first()
        assert player.status == "Injured"

class TestProjectionRoutes:
    """Integration tests for projection-related routes"""
    
    def test_get_projection_by_id(self, client, test_db, sample_players):
        """Test getting a projection by ID."""
        # Create a projection first
        player_id = sample_players["ids"]["Patrick Mahomes"]
        projection = Projection(
            projection_id=str(uuid.uuid4()),
            player_id=player_id,
            season=2025,
            games=17,
            half_ppr=350.5,
            pass_attempts=600.0,
            completions=410.0,
            pass_yards=4800.0,
            pass_td=38.0,
            interceptions=10.0,
            rush_attempts=60.0,  # Changed from carries to rush_attempts
            rush_yards=350.0,
            rush_td=3.0
        )
        test_db.add(projection)
        test_db.commit()
        
        # Get the projection
        response = client.get(f"/api/projections/projections/{projection.projection_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["projection_id"] == projection.projection_id
        assert data["player_id"] == player_id
        assert data["half_ppr"] == 350.5
    
    def test_get_projections_with_filters(self, client, test_db, sample_players):
        """Test filtering projections."""
        # Create projections for multiple players
        projections = []
        for player in sample_players["players"]:
            if player.position == "QB":
                proj = Projection(
                    projection_id=str(uuid.uuid4()),
                    player_id=player.player_id,
                    season=2025,
                    games=17,
                    half_ppr=350.0,
                    pass_attempts=600.0,
                    completions=410.0,
                    pass_yards=4800.0,
                    pass_td=38.0,
                    interceptions=10.0,
                    rush_attempts=60.0,  # Changed from carries to rush_attempts
                    rush_yards=350.0,
                    rush_td=3.0
                )
            else:
                proj = Projection(
                    projection_id=str(uuid.uuid4()),
                    player_id=player.player_id,
                    season=2025,
                    games=17,
                    half_ppr=200.0
                )
            projections.append(proj)
            test_db.add(proj)
        test_db.commit()
        
        # Test filtering by position (using team to filter)
        qb_player = next(p for p in sample_players["players"] if p.position == "QB")
        response = client.get(f"/api/projections/projections/?team={qb_player.team}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        
        # Test filtering by player_id
        response = client.get(f"/api/projections/projections/?player_id={qb_player.player_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["player_id"] == qb_player.player_id
        
class TestScenarioRoutes:
    """Integration tests for scenario-related routes"""
    
    def test_create_and_get_scenario(self, client, test_db):
        """Test creating and retrieving a scenario."""
        # Create a scenario
        scenario_data = {
            "name": "Test Scenario",
            "description": "A test scenario",
            "is_baseline": False
        }
        
        # Create
        response = client.post("/api/scenarios/scenarios/", json=scenario_data)
        
        assert response.status_code == 201
        data = response.json()
        scenario_id = data["scenario_id"]
        assert data["name"] == "Test Scenario"
        
        # Get scenario by ID
        response = client.get(f"/api/scenarios/scenarios/{scenario_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["scenario_id"] == scenario_id
        assert data["name"] == "Test Scenario"
        
        # Get all scenarios
        response = client.get("/api/scenarios/scenarios/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(s["scenario_id"] == scenario_id for s in data)
    
    def test_delete_scenario(self, client, test_db):
        """Test deleting a scenario."""
        # Create a scenario first
        scenario = Scenario(
            scenario_id=str(uuid.uuid4()),
            name="Test Delete Scenario",
            description="A scenario to delete",
            is_baseline=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        test_db.add(scenario)
        test_db.commit()
        
        # Delete the scenario
        response = client.delete(f"/api/scenarios/scenarios/{scenario.scenario_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        # Verify it's gone
        deleted_scenario = test_db.query(Scenario).filter(Scenario.scenario_id == scenario.scenario_id).first()
        assert deleted_scenario is None
        
class TestOverrideRoutes:
    """Integration tests for override-related routes"""
    
    def test_create_and_get_override(self, client, test_db, sample_players):
        """Test creating and retrieving an override."""
        # Create a projection first
        player_id = sample_players["ids"]["Patrick Mahomes"]
        projection = Projection(
            projection_id=str(uuid.uuid4()),
            player_id=player_id,
            season=2025,
            games=17,
            half_ppr=350.5,
            pass_attempts=600.0,
            completions=410.0,
            pass_yards=4800.0,
            pass_td=38.0,
            interceptions=10.0,
            rush_attempts=60.0,  # Changed from carries to rush_attempts
            rush_yards=350.0,
            rush_td=3.0
        )
        test_db.add(projection)
        test_db.commit()
        
        # Create an override
        override_data = {
            "player_id": player_id,
            "projection_id": projection.projection_id,
            "stat_name": "pass_td",
            "manual_value": 45.0,
            "notes": "Testing override"
        }
        
        response = client.post("/api/overrides/overrides/", json=override_data)
        
        assert response.status_code == 201
        data = response.json()
        override_id = data["override_id"]
        assert data["player_id"] == player_id
        assert data["stat_name"] == "pass_td"
        assert data["manual_value"] == 45.0
        
        # Get overrides for player
        response = client.get(f"/api/overrides/overrides/player/{player_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(o["override_id"] == override_id for o in data)
        
        # Delete the override
        response = client.delete(f"/api/overrides/overrides/{override_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        # Verify it's gone
        overrides = client.get(f"/api/overrides/overrides/player/{player_id}").json()
        assert not any(o["override_id"] == override_id for o in overrides)

# For now, only include API route verification without complex batch operations
class TestBatchEndpoints:
    """Simple route existence tests for batch operations endpoints"""
    
    def test_batch_endpoints_exist(self, client):
        """Verify that batch endpoints exist and respond"""
        # Just test that the endpoint exists
        response = client.options("/api/batch/batch/projections/create")
        assert response.status_code in [200, 204, 405], f"Status code: {response.status_code}"
        
        # Check cache endpoints
        response = client.get("/api/batch/batch/cache/stats")
        assert response.status_code in [200, 403, 500], f"Status code: {response.status_code}"