import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import uuid
import json
from datetime import datetime

from backend.api.routes.projections import router
from backend.api.schemas import (
    ProjectionResponse,
    RookieProjectionResponse,
    TeamStatsResponse
)
from backend.services.projection_service import ProjectionService
from backend.services.projection_variance_service import ProjectionVarianceService
from backend.services.rookie_projection_service import RookieProjectionService
from backend.services.team_stat_service import TeamStatService

# Create isolated test app with just the projections router
app = FastAPI()
app.include_router(router)
client = TestClient(app)

class TestProjectionsRoutes:
    
    def test_get_projection(self):
        """Test retrieving a specific projection by ID."""
        projection_id = str(uuid.uuid4())
        player_id = str(uuid.uuid4())
        
        # Mock response from service
        mock_projection = {
            "projection_id": projection_id,
            "player_id": player_id,
            "scenario_id": None,
            "season": 2025,
            "games": 17,
            "half_ppr": 275.5,
            "pass_attempts": 575.0,
            "completions": 380.0,
            "pass_yards": 4500.0,
            "pass_td": 32.0,
            "interceptions": 12.0,
            "carries": 65.0,
            "rush_yards": 350.0,
            "rush_td": 3.0,
            "has_overrides": False
        }
        
        # Patch the service method
        with patch('backend.api.routes.projections.ProjectionService') as mock_service:
            service_instance = mock_service.return_value
            service_instance.get_projection = AsyncMock(return_value=mock_projection)
            
            # Make request
            response = client.get(f"/projections/{projection_id}")
            
            # Verify service was called correctly
            service_instance.get_projection.assert_called_once_with(projection_id)
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["projection_id"] == projection_id
            assert data["player_id"] == player_id
            assert data["pass_yards"] == 4500.0
            assert data["half_ppr"] == 275.5
    
    def test_get_projection_not_found(self):
        """Test handling of non-existent projection."""
        projection_id = str(uuid.uuid4())
        
        # Patch the service method to return None
        with patch('backend.api.routes.projections.ProjectionService') as mock_service:
            service_instance = mock_service.return_value
            service_instance.get_projection = AsyncMock(return_value=None)
            
            # Make request
            response = client.get(f"/projections/{projection_id}")
            
            # Verify response
            assert response.status_code == 404
            assert "Projection not found" in response.json()["detail"]
    
    def test_get_projections_with_filters(self):
        """Test retrieving projections with filters."""
        player_id = str(uuid.uuid4())
        season = 2025
        
        # Mock response from service
        mock_projections = [
            {
                "projection_id": str(uuid.uuid4()),
                "player_id": player_id,
                "scenario_id": None,
                "season": season,
                "games": 17,
                "half_ppr": 275.5,
                "pass_attempts": 575.0,
                "pass_td": 32.0
            },
            {
                "projection_id": str(uuid.uuid4()),
                "player_id": player_id,
                "scenario_id": str(uuid.uuid4()),
                "season": season,
                "games": 17,
                "half_ppr": 300.2,
                "pass_attempts": 600.0,
                "pass_td": 36.0
            }
        ]
        
        # Patch the service method
        with patch('backend.api.routes.projections.ProjectionService') as mock_service:
            service_instance = mock_service.return_value
            service_instance.get_player_projections = AsyncMock(return_value=mock_projections)
            
            # Make request with filters
            response = client.get(f"/projections/?player_id={player_id}&season={season}")
            
            # Verify service was called correctly
            service_instance.get_player_projections.assert_called_once_with(
                player_id=player_id,
                team=None,
                season=season,
                scenario_id=None
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["player_id"] == player_id
            assert data[1]["player_id"] == player_id
            assert data[0]["scenario_id"] is None
            assert data[1]["scenario_id"] is not None
    
    def test_create_projection(self):
        """Test creating a new projection."""
        player_id = str(uuid.uuid4())
        projection_id = str(uuid.uuid4())
        season = 2025
        
        # Request data
        request_data = {
            "player_id": player_id,
            "season": season
        }
        
        # Mock response from service
        mock_projection = {
            "projection_id": projection_id,
            "player_id": player_id,
            "scenario_id": None,
            "season": season,
            "games": 17,
            "half_ppr": 275.5,
            "pass_attempts": 575.0,
            "completions": 380.0,
            "pass_yards": 4500.0,
            "pass_td": 32.0
        }
        
        # Patch the service method
        with patch('backend.api.routes.projections.ProjectionService') as mock_service:
            service_instance = mock_service.return_value
            service_instance.create_base_projection = AsyncMock(return_value=mock_projection)
            
            # Make request
            response = client.post("/projections/create", json=request_data)
            
            # Verify service was called correctly
            service_instance.create_base_projection.assert_called_once_with(
                player_id=player_id,
                season=season
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["projection_id"] == projection_id
            assert data["player_id"] == player_id
            assert data["season"] == season
            assert data["half_ppr"] == 275.5
    
    def test_create_projection_failure(self):
        """Test handling failure when creating a projection."""
        player_id = str(uuid.uuid4())
        season = 2025
        
        # Request data
        request_data = {
            "player_id": player_id,
            "season": season
        }
        
        # Patch the service method to return None (failure)
        with patch('backend.api.routes.projections.ProjectionService') as mock_service:
            service_instance = mock_service.return_value
            service_instance.create_base_projection = AsyncMock(return_value=None)
            
            # Make request
            response = client.post("/projections/create", json=request_data)
            
            # Verify response
            assert response.status_code == 400
            assert "Failed to create projection" in response.json()["detail"]
    
    def test_adjust_projection(self):
        """Test adjusting an existing projection."""
        projection_id = str(uuid.uuid4())
        player_id = str(uuid.uuid4())
        
        # Request data
        request_data = {
            "adjustments": {
                "pass_attempts": 1.1,
                "rush_share": 0.9
            }
        }
        
        # Mock response from service
        mock_projection = {
            "projection_id": projection_id,
            "player_id": player_id,
            "scenario_id": None,
            "season": 2025,
            "games": 17,
            "half_ppr": 290.3, # Increased due to adjustments
            "pass_attempts": 632.5, # Increased by 10%
            "completions": 418.0,
            "pass_yards": 4950.0,
            "pass_td": 35.0
        }
        
        # Patch the service method
        with patch('backend.api.routes.projections.ProjectionService') as mock_service:
            service_instance = mock_service.return_value
            service_instance.update_projection = AsyncMock(return_value=mock_projection)
            
            # Make request
            response = client.put(f"/projections/{projection_id}/adjust", json=request_data)
            
            # Verify service was called correctly
            service_instance.update_projection.assert_called_once_with(
                projection_id=projection_id,
                adjustments=request_data["adjustments"]
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["projection_id"] == projection_id
            assert data["pass_attempts"] == 632.5
            assert data["half_ppr"] == 290.3
    
    def test_get_projection_range(self):
        """Test generating projection ranges with confidence intervals."""
        projection_id = str(uuid.uuid4())
        
        # Mock response from service
        mock_range = {
            "base": {
                "half_ppr": 275.5,
                "pass_yards": 4500.0,
                "pass_td": 32.0
            },
            "low": {
                "half_ppr": 240.2,
                "pass_yards": 4100.0,
                "pass_td": 28.0
            },
            "median": {
                "half_ppr": 275.5,
                "pass_yards": 4500.0,
                "pass_td": 32.0
            },
            "high": {
                "half_ppr": 310.8,
                "pass_yards": 4900.0,
                "pass_td": 36.0
            },
            "scenario_ids": None
        }
        
        # Patch the service method
        with patch('backend.api.routes.projections.ProjectionVarianceService') as mock_service:
            service_instance = mock_service.return_value
            service_instance.generate_projection_range = AsyncMock(return_value=mock_range)
            
            # Make request
            response = client.get(f"/projections/{projection_id}/range?confidence=0.85")
            
            # Verify service was called correctly
            service_instance.generate_projection_range.assert_called_once_with(
                projection_id=projection_id,
                confidence=0.85,
                scenarios=False
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert "base" in data
            assert "low" in data
            assert "median" in data
            assert "high" in data
            assert data["base"]["half_ppr"] == 275.5
            assert data["low"]["half_ppr"] == 240.2
            assert data["high"]["half_ppr"] == 310.8
    
    def test_get_team_stats(self):
        """Test retrieving team statistics."""
        team = "KC"
        season = 2025
        team_stat_id = str(uuid.uuid4())
        
        # Mock response from service
        mock_team_stats = [
            {
                "team_stat_id": team_stat_id,
                "team": team,
                "season": season,
                "plays": 1100.0,
                "pass_percentage": 0.62,
                "pass_attempts": 682.0,
                "pass_yards": 5200.0,
                "pass_td": 45.0,
                "pass_td_rate": 0.066,
                "rush_attempts": 418.0,
                "rush_yards": 1850.0,
                "rush_td": 18.0,
                "carries": 380.0,
                "rush_yards_per_carry": 4.8,
                "targets": 682.0,
                "receptions": 450.0,
                "rec_yards": 5100.0,
                "rec_td": 42.0,
                "rank": 1,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        ]
        
        # Patch the service method
        with patch('backend.api.routes.projections.TeamStatService') as mock_service:
            service_instance = mock_service.return_value
            service_instance.get_team_stats = AsyncMock(return_value=mock_team_stats)
            
            # Make request
            response = client.get(f"/projections/team/{team}/stats?season={season}")
            
            # Verify service was called correctly
            service_instance.get_team_stats.assert_called_once_with(
                team=team,
                season=season
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["team_stat_id"] == team_stat_id
            assert data["team"] == team
            assert data["season"] == season
            assert data["pass_percentage"] == 0.62
            assert data["rush_yards_per_carry"] == 4.8
            assert data["rank"] == 1
    
    def test_get_team_stats_not_found(self):
        """Test handling when team stats are not found."""
        team = "KC"
        season = 2025
        
        # Patch the service method to return empty list
        with patch('backend.api.routes.projections.TeamStatService') as mock_service:
            service_instance = mock_service.return_value
            service_instance.get_team_stats = AsyncMock(return_value=[])
            
            # Make request
            response = client.get(f"/projections/team/{team}/stats?season={season}")
            
            # Verify response
            assert response.status_code == 404
            assert "Team stats not found" in response.json()["detail"]
            
    def test_adjust_team_projections(self):
        """Test applying team-level adjustments to player projections."""
        team = "KC"
        season = 2025
        player_id_1 = str(uuid.uuid4())
        player_id_2 = str(uuid.uuid4())
        
        # Request data
        adjustments = {
            "pass_volume": 1.1,
            "rush_volume": 0.95
        }
        
        # Mock response from service
        mock_updated_projections = [
            {
                "projection_id": str(uuid.uuid4()),
                "player_id": player_id_1,
                "season": season,
                "half_ppr": 320.5,
                "pass_attempts": 715.0,
                "pass_yards": 5400.0
            },
            {
                "projection_id": str(uuid.uuid4()),
                "player_id": player_id_2,
                "season": season,
                "half_ppr": 180.2,
                "targets": 150.0,
                "receptions": 110.0
            }
        ]
        
        # Patch the service method
        with patch('backend.api.routes.projections.TeamStatService') as mock_service:
            service_instance = mock_service.return_value
            service_instance.apply_team_adjustments = AsyncMock(return_value=mock_updated_projections)
            
            # Make request
            response = client.put(f"/projections/team/{team}/adjust?season={season}", json=adjustments)
            
            # Verify service was called correctly
            service_instance.apply_team_adjustments.assert_called_once_with(
                team=team,
                season=season,
                adjustments=adjustments,
                player_shares=None
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["player_id"] == player_id_1
            assert data[1]["player_id"] == player_id_2
    
    def test_create_draft_based_rookie_projection(self):
        """Test creating a rookie projection based on draft position."""
        player_id = str(uuid.uuid4())
        draft_position = 25
        season = 2025
        
        # Mock response from service
        mock_projection = {
            "projection_id": str(uuid.uuid4()),
            "player_id": player_id,
            "season": season,
            "games": 14.0,
            "half_ppr": 85.2,
            "targets": 70.0,
            "receptions": 45.0,
            "rec_yards": 600.0,
            "rec_td": 4.0,
            "comp_level": "medium",
            "playing_time_pct": 0.6
        }
        
        # Patch the service method
        with patch('backend.api.routes.projections.RookieProjectionService') as mock_service:
            service_instance = mock_service.return_value
            service_instance.create_draft_based_projection = AsyncMock(return_value=mock_projection)
            
            # Make request
            response = client.post(f"/projections/rookies/draft-based?player_id={player_id}&draft_position={draft_position}&season={season}")
            
            # Verify service was called correctly
            service_instance.create_draft_based_projection.assert_called_once_with(
                player_id=player_id,
                draft_position=draft_position,
                season=season,
                scenario_id=None
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["player_id"] == player_id
            assert data["season"] == season
            assert data["targets"] == 70.0
            assert data["half_ppr"] == 85.2