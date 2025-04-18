import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import uuid
import json
from io import StringIO

from backend.api.routes.batch import router
from backend.api.schemas import BatchResponse
from backend.services.batch_service import BatchService
from backend.services.cache_service import CacheService

# Create isolated test app with just the batch router
app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestBatchRoutes:

    def test_batch_create_projections(self):
        """Test creating projections for multiple players in a batch."""
        player_id_1 = str(uuid.uuid4())
        player_id_2 = str(uuid.uuid4())
        season = 2025

        # Request data
        request_data = {
            "player_ids": [player_id_1, player_id_2],
            "season": season,
            "scenario_id": None,
        }

        # Mock response from service
        mock_result = {
            "success": 2,
            "failure": 0,
            "projection_ids": {player_id_1: str(uuid.uuid4()), player_id_2: str(uuid.uuid4())},
        }

        # Patch the service method
        with patch("backend.api.routes.batch.BatchService") as mock_service:
            service_instance = mock_service.return_value
            service_instance.batch_create_projections = AsyncMock(return_value=mock_result)

            # Make request
            response = client.post("/batch/projections/create", json=request_data)

            # Verify service was called correctly
            service_instance.batch_create_projections.assert_called_once_with(
                player_ids=request_data["player_ids"],
                season=request_data["season"],
                scenario_id=request_data["scenario_id"],
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == 2
            assert data["failure"] == 0
            assert player_id_1 in data["projection_ids"]
            assert player_id_2 in data["projection_ids"]

    def test_batch_create_projections_failure(self):
        """Test handling failure when creating batch projections."""
        player_id_1 = str(uuid.uuid4())
        player_id_2 = str(uuid.uuid4())
        season = 2025

        # Request data
        request_data = {
            "player_ids": [player_id_1, player_id_2],
            "season": season,
            "scenario_id": None,
        }

        # Mock response from service indicating all operations failed
        mock_result = {
            "success": 0,
            "failure": 2,
            "failed_players": [
                {"player_id": player_id_1, "error": "Player not found"},
                {"player_id": player_id_2, "error": "Invalid position"},
            ],
            "error": "Failed to create projections for any players",
        }

        # Patch the service method
        with patch("backend.api.routes.batch.BatchService") as mock_service:
            service_instance = mock_service.return_value
            service_instance.batch_create_projections = AsyncMock(return_value=mock_result)

            # Make request
            response = client.post("/batch/projections/create", json=request_data)

            # Verify response indicates failure
            assert response.status_code == 400
            data = response.json()
            assert "Failed to create any projections" in data["detail"]

    def test_batch_adjust_projections(self):
        """Test adjusting multiple projections in a batch."""
        projection_id_1 = str(uuid.uuid4())
        projection_id_2 = str(uuid.uuid4())

        # Request data
        request_data = {
            "adjustments": {
                projection_id_1: {"pass_attempts": 1.1, "pass_td_rate": 1.05},
                projection_id_2: {"rush_volume": 0.9, "snap_share": 0.95},
            }
        }

        # Mock response from service
        mock_result = {
            "success": 2,
            "failure": 0,
            "projection_ids": {projection_id_1: projection_id_1, projection_id_2: projection_id_2},
        }

        # Patch the service method
        with patch("backend.api.routes.batch.BatchService") as mock_service:
            service_instance = mock_service.return_value
            service_instance.batch_adjust_projections = AsyncMock(return_value=mock_result)

            # Make request
            response = client.post("/batch/projections/adjust", json=request_data)

            # Verify service was called correctly
            service_instance.batch_adjust_projections.assert_called_once_with(
                adjustments=request_data["adjustments"]
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == 2
            assert data["failure"] == 0
            assert projection_id_1 in data["projection_ids"]
            assert projection_id_2 in data["projection_ids"]

    def test_batch_create_scenarios(self):
        """Test creating multiple scenarios in a batch."""
        # Request data
        request_data = {
            "scenarios": [
                {
                    "name": "High Passing Volume",
                    "description": "Increased passing across the league",
                    "adjustments": {"pass_volume": 1.1, "pass_td_rate": 1.05},
                },
                {
                    "name": "High RB Usage",
                    "description": "Increased rushing volume",
                    "adjustments": {"rush_volume": 1.1, "rush_share": 1.05},
                },
            ]
        }

        # Mock response from service
        mock_result = {
            "success": 2,
            "failure": 0,
            "scenario_ids": {
                "High Passing Volume": str(uuid.uuid4()),
                "High RB Usage": str(uuid.uuid4()),
            },
        }

        # Patch the service method
        with patch("backend.api.routes.batch.BatchService") as mock_service:
            service_instance = mock_service.return_value
            service_instance.batch_create_scenarios = AsyncMock(return_value=mock_result)

            # Make request
            response = client.post("/batch/scenarios/create", json=request_data)

            # Verify service was called with any arguments
            assert service_instance.batch_create_scenarios.called
            # Don't assert exact arguments since the input may be converted to proper objects

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == 2
            assert data["failure"] == 0
            assert "High Passing Volume" in data["scenario_ids"]
            assert "High RB Usage" in data["scenario_ids"]

    def test_export_projections_csv(self):
        """Test exporting projections in CSV format."""
        # Request data
        request_data = {"filters": {"position": "QB", "team": "KC", "season": 2025}}

        # Mock CSV content
        mock_csv = (
            "player_id,name,team,position,half_ppr\n"
            + f"{str(uuid.uuid4())},Patrick Mahomes,KC,QB,350.5\n"
        )

        # Patch the service method
        with patch("backend.api.routes.batch.BatchService") as mock_service:
            service_instance = mock_service.return_value
            service_instance.export_projections = AsyncMock(
                return_value=("projections.csv", mock_csv)
            )

            # Make request
            response = client.post("/batch/export?format=csv", json=request_data)

            # Verify service was called correctly
            service_instance.export_projections.assert_called_once_with(
                format="csv", filters=request_data["filters"], include_metadata=False
            )

            # Verify response
            assert response.status_code == 200
            assert response.headers["Content-Disposition"] == "attachment; filename=projections.csv"
            assert "text/csv" in response.headers["content-type"]
            assert response.content.decode() == mock_csv

    def test_export_projections_json(self):
        """Test exporting projections in JSON format."""
        # Request data
        request_data = {"filters": {"position": "QB", "season": 2025}}

        # Mock JSON content
        mock_data = [
            {
                "player_id": str(uuid.uuid4()),
                "name": "Patrick Mahomes",
                "team": "KC",
                "position": "QB",
                "half_ppr": 350.5,
            },
            {
                "player_id": str(uuid.uuid4()),
                "name": "Josh Allen",
                "team": "BUF",
                "position": "QB",
                "half_ppr": 340.2,
            },
        ]
        mock_json = json.dumps(mock_data)

        # Patch the service method
        with patch("backend.api.routes.batch.BatchService") as mock_service:
            service_instance = mock_service.return_value
            service_instance.export_projections = AsyncMock(
                return_value=("projections.json", mock_json)
            )

            # Make request
            response = client.post("/batch/export?format=json", json=request_data)

            # Verify service was called correctly
            service_instance.export_projections.assert_called_once_with(
                format="json", filters=request_data["filters"], include_metadata=False
            )

            # Verify response
            assert response.status_code == 200
            assert (
                response.headers["Content-Disposition"] == "attachment; filename=projections.json"
            )
            assert response.headers["content-type"] == "application/json"
            assert json.loads(response.content.decode()) == mock_data

    def test_get_cache_stats(self):
        """Test retrieving cache statistics."""
        # Mock cache stats
        mock_stats = {
            "size": 250,
            "hits": 1500,
            "misses": 300,
            "hit_rate": 0.83,
            "oldest_entry_age": 3600,
            "newest_entry_age": 60,
        }

        # Patch the cache service
        with patch("backend.api.routes.batch.get_cache") as mock_get_cache:
            mock_cache = MagicMock()
            mock_cache.get_stats.return_value = mock_stats
            mock_get_cache.return_value = mock_cache

            # Make request
            response = client.get("/batch/cache/stats")

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["size"] == 250
            assert data["hits"] == 1500
            assert data["misses"] == 300
            assert data["hit_rate"] == 0.83

    def test_clear_cache(self):
        """Test clearing the cache."""
        # Patch the cache service
        with patch("backend.api.routes.batch.get_cache") as mock_get_cache:
            mock_cache = MagicMock()
            mock_cache.clear.return_value = None
            mock_get_cache.return_value = mock_cache

            # Make request
            response = client.post("/batch/cache/clear")

            # Verify cache was cleared
            mock_cache.clear.assert_called_once()

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["message"] == "Cache cleared"

    def test_clear_cache_with_pattern(self):
        """Test clearing the cache with a pattern."""
        pattern = "player_*"
        cleared_count = 15

        # Patch the cache service
        with patch("backend.api.routes.batch.get_cache") as mock_get_cache:
            mock_cache = MagicMock()
            mock_cache.clear_pattern.return_value = cleared_count
            mock_get_cache.return_value = mock_cache

            # Make request
            response = client.post(f"/batch/cache/clear?pattern={pattern}")

            # Verify cache pattern was cleared
            mock_cache.clear_pattern.assert_called_once_with(pattern)

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["cleared_entries"] == cleared_count
