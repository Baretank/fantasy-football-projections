import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import uuid
import json
from datetime import datetime, date

from backend.api.routes.players import router
from backend.api.schemas import (
    PlayerResponse,
    PlayerListResponse,
    OptimizedPlayerResponse,
    PlayerSearchResponse
)
from backend.services.query_service import QueryService

# Create isolated test app with just the players router
app = FastAPI()
app.include_router(router, prefix="/players")
client = TestClient(app)

class TestPlayersRoutes:
    
    def test_get_players_success(self):
        """Test successful retrieval of players with pagination."""
        # Mock data for players
        mock_player_1 = {
            "player_id": str(uuid.uuid4()),
            "name": "Patrick Mahomes",
            "team": "KC",
            "position": "QB",
            "date_of_birth": "1995-09-17",
            "height": 75,
            "weight": 225,
            "status": "Active",
            "depth_chart_position": "Starter",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        mock_player_2 = {
            "player_id": str(uuid.uuid4()),
            "name": "Travis Kelce",
            "team": "KC",
            "position": "TE",
            "date_of_birth": "1989-10-05",
            "height": 77,
            "weight": 250,
            "status": "Active",
            "depth_chart_position": "Starter",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        mock_players = [mock_player_1, mock_player_2]
        mock_total_count = 2
        
        # Patch the service method
        with patch('backend.api.routes.players.QueryService') as mock_service:
            service_instance = mock_service.return_value
            service_instance.get_players_optimized = AsyncMock(return_value=(mock_players, mock_total_count))
            
            # Make request
            response = client.get("/players/")
            
            # Verify service was called correctly
            service_instance.get_players_optimized.assert_called_once_with(
                filters={},
                include_projections=False,
                include_stats=False,
                page=1,
                page_size=20,
                sort_by="name",
                sort_dir="asc"
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert len(data["players"]) == 2
            assert data["players"][0]["name"] == "Patrick Mahomes"
            assert data["players"][1]["name"] == "Travis Kelce"
            assert data["pagination"]["page"] == 1
            assert data["pagination"]["total_count"] == 2
            assert data["pagination"]["has_next"] is False
    
    def test_get_players_with_filters(self):
        """Test retrieving players with filters applied."""
        # Mock data for filtered players
        mock_player = {
            "player_id": str(uuid.uuid4()),
            "name": "Patrick Mahomes",
            "team": "KC",
            "position": "QB",
            "status": "Active",
            "depth_chart_position": "Starter",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        mock_players = [mock_player]
        mock_total_count = 1
        
        # Patch the service method
        with patch('backend.api.routes.players.QueryService') as mock_service:
            service_instance = mock_service.return_value
            service_instance.get_players_optimized = AsyncMock(return_value=(mock_players, mock_total_count))
            
            # Make request with filters
            response = client.get("/players/?position=QB&team=KC&page_size=10")
            
            # Verify service was called correctly
            service_instance.get_players_optimized.assert_called_once_with(
                filters={"position": "QB", "team": "KC"},
                include_projections=False,
                include_stats=False,
                page=1,
                page_size=10,
                sort_by="name",
                sort_dir="asc"
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert len(data["players"]) == 1
            assert data["players"][0]["name"] == "Patrick Mahomes"
            assert data["players"][0]["position"] == "QB"
            assert data["players"][0]["team"] == "KC"
    
    def test_search_players(self):
        """Test searching for players by name."""
        player_id = str(uuid.uuid4())
        # Mock data for search results
        mock_players = [
            {
                "player_id": player_id,
                "name": "Patrick Mahomes",
                "team": "KC",
                "position": "QB"
            }
        ]
        
        # Patch the service method
        with patch('backend.api.routes.players.QueryService') as mock_service:
            service_instance = mock_service.return_value
            service_instance.search_players = AsyncMock(return_value=mock_players)
            
            # Make request
            response = client.get("/players/search?query=Mahomes")
            
            # Verify service was called correctly
            service_instance.search_players.assert_called_once_with(
                search_term="Mahomes",
                position=None,
                limit=20
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["query"] == "Mahomes"
            assert data["count"] == 1
            assert len(data["players"]) == 1
            assert data["players"][0]["name"] == "Patrick Mahomes"
            assert data["players"][0]["player_id"] == player_id
    
    def test_get_player_by_id(self):
        """Test retrieving a specific player by ID."""
        player_id = str(uuid.uuid4())
        
        # Mock response for player with stats and projections
        mock_player_data = {
            "player_id": player_id,
            "name": "Patrick Mahomes",
            "team": "KC",
            "position": "QB",
            "stats": {
                "passing": {"pass_yards": 5000, "pass_td": 35},
                "rushing": {"rush_yards": 300, "rush_td": 4}
            },
            "projection": {
                "pass_yards": 4800,
                "pass_td": 38,
                "half_ppr": 380.5
            }
        }
        
        # Patch the service method
        with patch('backend.api.routes.players.QueryService') as mock_service:
            service_instance = mock_service.return_value
            service_instance.get_player_stats_optimized = AsyncMock(return_value=mock_player_data)
            
            # Make request
            response = client.get(f"/players/{player_id}")
            
            # Verify service was called correctly
            service_instance.get_player_stats_optimized.assert_called_once_with(
                player_id=player_id
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["player_id"] == player_id
            assert data["name"] == "Patrick Mahomes"
            assert "stats" in data
            assert "projection" in data
            assert data["projection"]["half_ppr"] == 380.5
    
    def test_get_player_not_found(self):
        """Test handling of non-existent player."""
        player_id = str(uuid.uuid4())
        
        # Patch the service method to return None
        with patch('backend.api.routes.players.QueryService') as mock_service:
            service_instance = mock_service.return_value
            service_instance.get_player_stats_optimized = AsyncMock(return_value=None)
            
            # Make request
            response = client.get(f"/players/{player_id}")
            
            # Verify response
            assert response.status_code == 404
            assert "Player not found" in response.json()["detail"]
    
    def test_get_player_stats(self):
        """Test retrieving player stats with season filter."""
        player_id = str(uuid.uuid4())
        seasons = [2023]
        
        # Mock response for player stats
        mock_player_stats = {
            "player_id": player_id,
            "name": "Patrick Mahomes",
            "team": "KC",
            "position": "QB",
            "stats": {
                "2023": {
                    "pass_yards": 4800,
                    "pass_td": 38,
                    "interceptions": 14
                }
            }
        }
        
        # Patch the service method
        with patch('backend.api.routes.players.QueryService') as mock_service:
            service_instance = mock_service.return_value
            service_instance.get_player_stats_optimized = AsyncMock(return_value=mock_player_stats)
            
            # Make request
            response = client.get(f"/players/{player_id}/stats?seasons=2023")
            
            # Verify service was called correctly
            service_instance.get_player_stats_optimized.assert_called_once_with(
                player_id=player_id,
                seasons=seasons
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["player_id"] == player_id
            assert "stats" in data
            assert "2023" in data["stats"]
            assert data["stats"]["2023"]["pass_td"] == 38
    
    def test_get_available_seasons(self):
        """Test retrieving available seasons."""
        mock_seasons = [2021, 2022, 2023]
        
        # Patch the service method
        with patch('backend.api.routes.players.QueryService') as mock_service:
            service_instance = mock_service.return_value
            service_instance.get_available_seasons = AsyncMock(return_value=mock_seasons)
            
            # Make request
            response = client.get("/players/seasons")
            
            # Verify response
            assert response.status_code == 200
            seasons = response.json()
            assert len(seasons) == 3
            assert 2021 in seasons
            assert 2022 in seasons
            assert 2023 in seasons
    
    def test_get_rookies(self):
        """Test retrieving rookie players with filters."""
        # Mock data for DB query response
        mock_rookie = MagicMock()
        mock_rookie.player_id = str(uuid.uuid4())
        mock_rookie.name = "Caleb Williams"
        mock_rookie.team = "CHI"
        mock_rookie.position = "QB"
        mock_rookie.status = "Rookie"
        mock_rookie.depth_chart_position = "Starter"
        mock_rookie.draft_position = 1
        mock_rookie.draft_round = 1
        mock_rookie.draft_pick = 1
        mock_rookie.created_at = datetime.utcnow()
        mock_rookie.updated_at = datetime.utcnow()
        mock_rookies = [mock_rookie]
        
        # Patch the query builder
        with patch('backend.api.routes.players.db.query') as mock_query:
            mock_filter = MagicMock()
            mock_filter.filter.return_value = mock_filter
            mock_filter.all.return_value = mock_rookies
            mock_query.return_value = mock_filter
            
            # Make request
            response = client.get("/players/rookies?position=QB")
            
            # Verify response
            assert response.status_code == 200
            rookies = response.json()
            assert len(rookies) == 1
            assert rookies[0]["name"] == "Caleb Williams"
            assert rookies[0]["position"] == "QB"
            assert rookies[0]["status"] == "Rookie"
    
    def test_update_player_status(self):
        """Test updating a player's status."""
        player_id = str(uuid.uuid4())
        
        # Mock player object
        mock_player = MagicMock()
        mock_player.player_id = player_id
        mock_player.name = "Patrick Mahomes"
        mock_player.team = "KC"
        mock_player.position = "QB"
        mock_player.status = "Active"
        mock_player.updated_at = datetime.utcnow()
        
        # Patch the query builder
        with patch('backend.api.routes.players.db.query') as mock_query:
            mock_filter = MagicMock()
            mock_filter.first.return_value = mock_player
            mock_query.return_value.filter.return_value = mock_filter
            
            # Patch commit
            with patch('backend.api.routes.players.db.commit'):
                # Make request
                response = client.put(f"/players/{player_id}/status?status=Injured")
                
                # Verify player status was updated
                assert mock_player.status == "Injured"
                
                # Verify response
                assert response.status_code == 200
                player_data = response.json()
                assert player_data["player_id"] == player_id
                assert player_data["status"] == "Injured"
    
    def test_update_player_depth_chart(self):
        """Test updating a player's depth chart position."""
        player_id = str(uuid.uuid4())
        
        # Mock player object
        mock_player = MagicMock()
        mock_player.player_id = player_id
        mock_player.name = "Travis Kelce"
        mock_player.team = "KC"
        mock_player.position = "TE"
        mock_player.status = "Active"
        mock_player.depth_chart_position = "Backup"
        mock_player.updated_at = datetime.utcnow()
        
        # Patch the query builder
        with patch('backend.api.routes.players.db.query') as mock_query:
            mock_filter = MagicMock()
            mock_filter.first.return_value = mock_player
            mock_query.return_value.filter.return_value = mock_filter
            
            # Patch commit
            with patch('backend.api.routes.players.db.commit'):
                # Make request
                response = client.put(f"/players/{player_id}/depth-chart?position=Starter")
                
                # Verify player depth chart position was updated
                assert mock_player.depth_chart_position == "Starter"
                
                # Verify response
                assert response.status_code == 200
                player_data = response.json()
                assert player_data["player_id"] == player_id
                assert player_data["depth_chart_position"] == "Starter"
    
    def test_batch_update_players(self):
        """Test batch updating multiple players."""
        player_id_1 = str(uuid.uuid4())
        player_id_2 = str(uuid.uuid4())
        
        # Mock player objects
        mock_player_1 = MagicMock()
        mock_player_1.player_id = player_id_1
        mock_player_1.name = "Patrick Mahomes"
        mock_player_1.team = "KC"
        mock_player_1.position = "QB"
        mock_player_1.status = "Active"
        mock_player_1.updated_at = datetime.utcnow()
        
        mock_player_2 = MagicMock()
        mock_player_2.player_id = player_id_2
        mock_player_2.name = "Travis Kelce"
        mock_player_2.team = "KC"
        mock_player_2.position = "TE"
        mock_player_2.status = "Active"
        mock_player_2.updated_at = datetime.utcnow()
        
        # Patch the query builder for different player IDs
        with patch('backend.api.routes.players.db.query') as mock_query:
            mock_query1 = MagicMock()
            mock_filter1 = MagicMock()
            mock_filter1.first.return_value = mock_player_1
            
            mock_query2 = MagicMock()
            mock_filter2 = MagicMock()
            mock_filter2.first.return_value = mock_player_2
            
            # Configure two different query responses based on player_id
            def side_effect(*args, **kwargs):
                player_filter = args[0]
                if hasattr(player_filter, 'right') and hasattr(player_filter.right, 'value'):
                    if player_filter.right.value == player_id_1:
                        return mock_filter1
                    elif player_filter.right.value == player_id_2:
                        return mock_filter2
                return MagicMock()
            
            mock_query.return_value.filter.side_effect = side_effect
            
            # Patch commit
            with patch('backend.api.routes.players.db.commit'):
                # Batch update request
                updates = [
                    {"player_id": player_id_1, "status": "Injured"},
                    {"player_id": player_id_2, "depth_chart_position": "Starter", "team": "KC"}
                ]
                
                # Make request
                response = client.post("/players/batch-update", json=updates)
                
                # Verify players were updated
                assert mock_player_1.status == "Injured"
                assert mock_player_2.depth_chart_position == "Starter"
                assert mock_player_2.team == "KC"
                
                # Verify response
                assert response.status_code == 200
                result = response.json()
                assert result["status"] == "success"
                assert result["updated_count"] == 2
                assert len(result["errors"]) == 0