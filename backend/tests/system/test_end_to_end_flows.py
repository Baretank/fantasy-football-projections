import pytest
import json
import uuid
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.database.models import Player, TeamStat, BaseStat, Projection, Scenario
from backend.database.database import SessionLocal

class TestEndToEndFlows:
    @pytest.fixture(scope="function")
    def test_client(self):
        """Create a FastAPI test client."""
        return TestClient(app)
    
    @pytest.fixture(scope="function")
    def setup_test_data(self):
        """Set up necessary test data for end-to-end tests."""
        # Use a separate database session for setup
        db = SessionLocal()
        
        try:
            # Create test data
            season = 2023  # Historical season
            projection_season = 2024  # Projection season
            
            # Create a test team
            team = "KC"
            
            # Create team stats for both seasons
            team_stat_2023 = TeamStat(
                team_stat_id=str(uuid.uuid4()),
                team=team,
                season=season,
                plays=1000,
                pass_percentage=0.6,
                pass_attempts=600,
                pass_yards=4200,
                pass_td=30,
                pass_td_rate=0.05,
                rush_attempts=400,
                rush_yards=1800,
                rush_td=15,
                carries=400,
                rush_yards_per_carry=4.5,
                targets=600,
                receptions=390,
                rec_yards=4200,
                rec_td=30,
                rank=1
            )
            
            team_stat_2024 = TeamStat(
                team_stat_id=str(uuid.uuid4()),
                team=team,
                season=projection_season,
                plays=1000,
                pass_percentage=0.6,
                pass_attempts=600,
                pass_yards=4200,
                pass_td=30,
                pass_td_rate=0.05,
                rush_attempts=400,
                rush_yards=1800,
                rush_td=15,
                carries=400,
                rush_yards_per_carry=4.5,
                targets=600,
                receptions=390,
                rec_yards=4200,
                rec_td=30,
                rank=1
            )
            
            db.add(team_stat_2023)
            db.add(team_stat_2024)
            
            # Create test players
            qb = Player(
                player_id=str(uuid.uuid4()),
                name="Test QB",
                team=team,
                position="QB"
            )
            
            rb = Player(
                player_id=str(uuid.uuid4()),
                name="Test RB",
                team=team,
                position="RB"
            )
            
            wr = Player(
                player_id=str(uuid.uuid4()),
                name="Test WR",
                team=team,
                position="WR"
            )
            
            db.add(qb)
            db.add(rb)
            db.add(wr)
            db.commit()  # Commit to get player IDs
            
            # Create historical stats for players
            qb_stats = [
                BaseStat(player_id=qb.player_id, season=season, stat_type="games", value=17.0),
                BaseStat(player_id=qb.player_id, season=season, stat_type="completions", value=380.0),
                BaseStat(player_id=qb.player_id, season=season, stat_type="pass_attempts", value=580.0),
                BaseStat(player_id=qb.player_id, season=season, stat_type="pass_yards", value=4100.0),
                BaseStat(player_id=qb.player_id, season=season, stat_type="pass_td", value=28.0),
                BaseStat(player_id=qb.player_id, season=season, stat_type="interceptions", value=10.0),
                BaseStat(player_id=qb.player_id, season=season, stat_type="rush_attempts", value=55.0),
                BaseStat(player_id=qb.player_id, season=season, stat_type="rush_yards", value=250.0),
                BaseStat(player_id=qb.player_id, season=season, stat_type="rush_td", value=2.0)
            ]
            
            rb_stats = [
                BaseStat(player_id=rb.player_id, season=season, stat_type="games", value=16.0),
                BaseStat(player_id=rb.player_id, season=season, stat_type="rush_attempts", value=240.0),
                BaseStat(player_id=rb.player_id, season=season, stat_type="rush_yards", value=1100.0),
                BaseStat(player_id=rb.player_id, season=season, stat_type="rush_td", value=9.0),
                BaseStat(player_id=rb.player_id, season=season, stat_type="targets", value=60.0),
                BaseStat(player_id=rb.player_id, season=season, stat_type="receptions", value=48.0),
                BaseStat(player_id=rb.player_id, season=season, stat_type="rec_yards", value=380.0),
                BaseStat(player_id=rb.player_id, season=season, stat_type="rec_td", value=2.0)
            ]
            
            wr_stats = [
                BaseStat(player_id=wr.player_id, season=season, stat_type="games", value=17.0),
                BaseStat(player_id=wr.player_id, season=season, stat_type="targets", value=150.0),
                BaseStat(player_id=wr.player_id, season=season, stat_type="receptions", value=105.0),
                BaseStat(player_id=wr.player_id, season=season, stat_type="rec_yards", value=1300.0),
                BaseStat(player_id=wr.player_id, season=season, stat_type="rec_td", value=10.0),
                BaseStat(player_id=wr.player_id, season=season, stat_type="rush_attempts", value=10.0),
                BaseStat(player_id=wr.player_id, season=season, stat_type="rush_yards", value=60.0),
                BaseStat(player_id=wr.player_id, season=season, stat_type="rush_td", value=0.0)
            ]
            
            for stat in qb_stats + rb_stats + wr_stats:
                db.add(stat)
            
            # Create a base scenario
            base_scenario = Scenario(
                scenario_id=str(uuid.uuid4()),
                name="Base 2024",
                description="Base projections for 2024 season"
            )
            
            db.add(base_scenario)
            db.commit()
            
            # Return test data context
            return {
                "team": team,
                "qb": qb,
                "rb": rb,
                "wr": wr,
                "base_scenario": base_scenario,
                "season": season,
                "projection_season": projection_season
            }
        
        except Exception as e:
            db.rollback()
            raise e
        
        finally:
            db.close()
    
    def test_player_listing_and_filtering(self, test_client, setup_test_data):
        """Test player listing and filtering API endpoints."""
        # Get all players
        response = test_client.get("/api/players/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3  # At least our test players
        
        # Filter by team
        response = test_client.get(f"/api/players/?team={setup_test_data['team']}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3  # Our 3 test players
        team_names = [p["name"] for p in data]
        assert setup_test_data["qb"].name in team_names
        assert setup_test_data["rb"].name in team_names
        assert setup_test_data["wr"].name in team_names
        
        # Filter by position
        response = test_client.get("/api/players/?position=QB")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(p["name"] == setup_test_data["qb"].name for p in data)
    
    def test_projection_creation_and_retrieval(self, test_client, setup_test_data):
        """Test creating and retrieving projections."""
        qb = setup_test_data["qb"]
        projection_season = setup_test_data["projection_season"]
        
        # Create a base projection
        response = test_client.post(
            f"/api/projections/create",
            json={
                "player_id": qb.player_id,
                "season": projection_season
            }
        )
        assert response.status_code == 200
        projection_data = response.json()
        assert projection_data["player_id"] == qb.player_id
        assert projection_data["season"] == projection_season
        projection_id = projection_data["projection_id"]
        
        # Retrieve the projection
        response = test_client.get(f"/api/projections/{projection_id}")
        assert response.status_code == 200
        retrieved_projection = response.json()
        assert retrieved_projection["projection_id"] == projection_id
        assert retrieved_projection["player_id"] == qb.player_id
        
        # Get projections by player
        response = test_client.get(f"/api/projections/player/{qb.player_id}")
        assert response.status_code == 200
        player_projections = response.json()
        assert len(player_projections) >= 1
        assert any(p["projection_id"] == projection_id for p in player_projections)
        
        # Get projections by team
        response = test_client.get(f"/api/projections/?team={setup_test_data['team']}&season={projection_season}")
        assert response.status_code == 200
        team_projections = response.json()
        assert len(team_projections) >= 1
        assert any(p["projection_id"] == projection_id for p in team_projections)
    
    def test_projection_adjustment_flow(self, test_client, setup_test_data):
        """Test the workflow of creating and adjusting projections."""
        qb = setup_test_data["qb"]
        projection_season = setup_test_data["projection_season"]
        
        # Create a base projection
        response = test_client.post(
            f"/api/projections/create",
            json={
                "player_id": qb.player_id,
                "season": projection_season
            }
        )
        assert response.status_code == 200
        projection_data = response.json()
        projection_id = projection_data["projection_id"]
        
        # Store original values
        original_pass_attempts = projection_data["pass_attempts"]
        original_pass_td = projection_data["pass_td"]
        
        # Apply adjustments
        adjustments = {
            'pass_volume': 1.10,  # 10% increase in passing volume
            'td_rate': 1.20       # 20% increase in TD rate
        }
        
        response = test_client.post(
            f"/api/projections/{projection_id}/adjust",
            json={"adjustments": adjustments}
        )
        assert response.status_code == 200
        updated_projection = response.json()
        
        # Verify adjustments were applied
        assert updated_projection["pass_attempts"] > original_pass_attempts
        assert updated_projection["pass_td"] > original_pass_td
        
        # Verify adjustment factors
        assert abs(updated_projection["pass_attempts"] / original_pass_attempts - 1.10) < 0.01
        assert abs(updated_projection["pass_td"] / original_pass_td - 1.20) < 0.01
    
    def test_scenario_creation_and_management(self, test_client, setup_test_data):
        """Test creating and managing projection scenarios."""
        base_scenario = setup_test_data["base_scenario"]
        qb = setup_test_data["qb"]
        rb = setup_test_data["rb"]
        projection_season = setup_test_data["projection_season"]
        
        # Create base projections for players
        response = test_client.post(
            f"/api/projections/create",
            json={
                "player_id": qb.player_id,
                "season": projection_season,
                "scenario_id": base_scenario.scenario_id
            }
        )
        assert response.status_code == 200
        
        response = test_client.post(
            f"/api/projections/create",
            json={
                "player_id": rb.player_id,
                "season": projection_season,
                "scenario_id": base_scenario.scenario_id
            }
        )
        assert response.status_code == 200
        
        # Create a new scenario
        new_scenario_name = "High Scoring 2024"
        response = test_client.post(
            "/api/scenarios/",
            json={
                "name": new_scenario_name,
                "description": "Projections with increased scoring",
                "base_scenario_id": base_scenario.scenario_id
            }
        )
        assert response.status_code == 200
        new_scenario = response.json()
        new_scenario_id = new_scenario["scenario_id"]
        
        # Get scenarios
        response = test_client.get("/api/scenarios/")
        assert response.status_code == 200
        scenarios = response.json()
        assert len(scenarios) >= 2  # Our two scenarios
        assert any(s["name"] == new_scenario_name for s in scenarios)
        
        # Apply team-level adjustments to the new scenario
        response = test_client.post(
            f"/api/teams/{setup_test_data['team']}/adjust",
            json={
                "season": projection_season,
                "scenario_id": new_scenario_id,
                "adjustments": {
                    "pass_volume": 1.05,
                    "scoring_rate": 1.10
                }
            }
        )
        assert response.status_code == 200
        
        # Get projections for the new scenario
        response = test_client.get(f"/api/projections/?scenario_id={new_scenario_id}")
        assert response.status_code == 200
        scenario_projections = response.json()
        
        # Verify projections exist for the new scenario
        assert len(scenario_projections) >= 2  # At least our QB and RB
    
    def test_complete_user_workflow(self, test_client, setup_test_data):
        """Test a complete user workflow from player listing to final projections."""
        team = setup_test_data["team"]
        projection_season = setup_test_data["projection_season"]
        
        # Step 1: List players by team
        response = test_client.get(f"/api/players/?team={team}")
        assert response.status_code == 200
        players = response.json()
        assert len(players) == 3  # Our 3 test players
        
        # Step 2: Create base projections for all players
        projection_ids = []
        for player in players:
            response = test_client.post(
                "/api/projections/create",
                json={
                    "player_id": player["player_id"],
                    "season": projection_season
                }
            )
            assert response.status_code == 200
            projection = response.json()
            projection_ids.append(projection["projection_id"])
        
        # Step 3: Adjust a specific player projection
        qb = next(p for p in players if p["position"] == "QB")
        qb_projection_id = next(p_id for i, p_id in enumerate(projection_ids) if players[i]["position"] == "QB")
        
        response = test_client.post(
            f"/api/projections/{qb_projection_id}/adjust",
            json={
                "adjustments": {
                    "pass_volume": 1.08,
                    "td_rate": 1.10
                }
            }
        )
        assert response.status_code == 200
        
        # Step 4: Create a new scenario
        response = test_client.post(
            "/api/scenarios/",
            json={
                "name": "High Volume Offense",
                "description": "Projections with increased offensive volume"
            }
        )
        assert response.status_code == 200
        scenario = response.json()
        
        # Step 5: Apply team-wide adjustments in the new scenario
        response = test_client.post(
            f"/api/teams/{team}/adjust",
            json={
                "season": projection_season,
                "scenario_id": scenario["scenario_id"],
                "adjustments": {
                    "pass_volume": 1.06,
                    "rush_volume": 1.04,
                    "scoring_rate": 1.08
                }
            }
        )
        assert response.status_code == 200
        
        # Step 6: Get final projections for the scenario
        response = test_client.get(
            f"/api/projections/?team={team}&season={projection_season}&scenario_id={scenario['scenario_id']}"
        )
        assert response.status_code == 200
        final_projections = response.json()
        
        # Verify we have projections for all players
        assert len(final_projections) == 3
        
        # Verify position-specific projections make sense
        for proj in final_projections:
            if proj["player"]["position"] == "QB":
                assert proj["pass_attempts"] > 0
                assert proj["pass_yards"] > 0
                assert proj["half_ppr"] > 0
            
            elif proj["player"]["position"] == "RB":
                assert proj["carries"] > 0
                assert proj["rush_yards"] > 0
                assert proj["half_ppr"] > 0
            
            elif proj["player"]["position"] == "WR":
                assert proj["targets"] > 0
                assert proj["rec_yards"] > 0
                assert proj["half_ppr"] > 0