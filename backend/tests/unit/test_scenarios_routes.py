import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import uuid
import json
from datetime import datetime

from backend.api.routes.scenarios import router
from backend.api.schemas import (
    ScenarioResponse,
    ProjectionResponse,
    ScenarioComparisonResponse
)
from backend.services.scenario_service import ScenarioService

# Create isolated test app with just the scenarios router
app = FastAPI()
app.include_router(router)
client = TestClient(app)

class TestScenariosRoutes:
    
    def test_create_scenario(self):
        """Test creating a new scenario."""
        # Request data
        request_data = {
            "name": "High Passing Volume",
            "description": "Increased passing across the league",
            "is_baseline": False,
            "base_scenario_id": None
        }
        
        # Mock response from service
        mock_scenario = {
            "scenario_id": str(uuid.uuid4()),
            "name": request_data["name"],
            "description": request_data["description"],
            "is_baseline": request_data["is_baseline"],
            "base_scenario_id": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Patch the service method
        with patch('backend.api.routes.scenarios.ScenarioService') as mock_service:
            service_instance = mock_service.return_value
            service_instance.create_scenario = AsyncMock(return_value=mock_scenario)
            
            # Make request
            response = client.post("/", json=request_data)
            
            # Verify service was called correctly
            service_instance.create_scenario.assert_called_once_with(
                name=request_data["name"],
                description=request_data["description"],
                is_baseline=request_data["is_baseline"]
            )
            
            # Verify response
            assert response.status_code == 201
            data = response.json()
            assert data["name"] == request_data["name"]
            assert data["description"] == request_data["description"]
            assert data["is_baseline"] == request_data["is_baseline"]
            assert "scenario_id" in data
            assert "created_at" in data
    
    def test_create_scenario_failure(self):
        """Test handling failure when creating a scenario."""
        # Request data
        request_data = {
            "name": "Invalid Scenario",
            "description": "This will fail",
            "is_baseline": True
        }
        
        # Patch the service method to return None (failure)
        with patch('backend.api.routes.scenarios.ScenarioService') as mock_service:
            service_instance = mock_service.return_value
            service_instance.create_scenario = AsyncMock(return_value=None)
            
            # Make request
            response = client.post("/", json=request_data)
            
            # Verify response
            assert response.status_code == 400
            assert "Could not create scenario" in response.json()["detail"]
    
    def test_get_all_scenarios(self):
        """Test retrieving all scenarios."""
        # Mock response from service
        mock_scenarios = [
            {
                "scenario_id": str(uuid.uuid4()),
                "name": "Baseline 2025",
                "description": "Default projections for 2025",
                "is_baseline": True,
                "base_scenario_id": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "scenario_id": str(uuid.uuid4()),
                "name": "High RB Usage",
                "description": "Increased rushing volume",
                "is_baseline": False,
                "base_scenario_id": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        ]
        
        # Patch the service method
        with patch('backend.api.routes.scenarios.ScenarioService') as mock_service:
            service_instance = mock_service.return_value
            service_instance.get_all_scenarios = AsyncMock(return_value=mock_scenarios)
            
            # Make request
            response = client.get("/")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["name"] == "Baseline 2025"
            assert data[1]["name"] == "High RB Usage"
            assert data[0]["is_baseline"] is True
            assert data[1]["is_baseline"] is False
    
    def test_get_scenario(self):
        """Test retrieving a specific scenario by ID."""
        scenario_id = str(uuid.uuid4())
        
        # Mock response from service
        mock_scenario = {
            "scenario_id": scenario_id,
            "name": "High QB Rushing",
            "description": "Increased rushing for QBs",
            "is_baseline": False,
            "base_scenario_id": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Patch the service method
        with patch('backend.api.routes.scenarios.ScenarioService') as mock_service:
            service_instance = mock_service.return_value
            service_instance.get_scenario = AsyncMock(return_value=mock_scenario)
            
            # Make request
            response = client.get(f"/{scenario_id}")
            
            # Verify service was called correctly
            service_instance.get_scenario.assert_called_once_with(scenario_id)
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["scenario_id"] == scenario_id
            assert data["name"] == "High QB Rushing"
    
    def test_get_scenario_not_found(self):
        """Test handling of non-existent scenario."""
        scenario_id = str(uuid.uuid4())
        
        # Patch the service method to return None
        with patch('backend.api.routes.scenarios.ScenarioService') as mock_service:
            service_instance = mock_service.return_value
            service_instance.get_scenario = AsyncMock(return_value=None)
            
            # Make request
            response = client.get(f"/{scenario_id}")
            
            # Verify response
            assert response.status_code == 404
            assert "Scenario not found" in response.json()["detail"]
    
    def test_get_scenario_projections(self):
        """Test retrieving projections for a specific scenario."""
        scenario_id = str(uuid.uuid4())
        player_id_1 = str(uuid.uuid4())
        player_id_2 = str(uuid.uuid4())
        
        # Mock responses from service
        mock_scenario = {
            "scenario_id": scenario_id,
            "name": "High Passing Volume",
            "description": "Increased passing across the league",
            "is_baseline": False,
            "base_scenario_id": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        mock_projections = [
            {
                "projection_id": str(uuid.uuid4()),
                "player_id": player_id_1,
                "scenario_id": scenario_id,
                "season": 2025,
                "games": 17,
                "half_ppr": 320.5,
                "pass_attempts": 650.0,
                "pass_yards": 5000.0,
                "pass_td": 40.0
            },
            {
                "projection_id": str(uuid.uuid4()),
                "player_id": player_id_2,
                "scenario_id": scenario_id,
                "season": 2025,
                "games": 17,
                "half_ppr": 150.5,
                "targets": 160.0,
                "receptions": 110.0,
                "rec_yards": 1500.0,
                "rec_td": 12.0
            }
        ]
        
        # Patch the service methods
        with patch('backend.api.routes.scenarios.ScenarioService') as mock_service:
            service_instance = mock_service.return_value
            service_instance.get_scenario = AsyncMock(return_value=mock_scenario)
            service_instance.get_scenario_projections = AsyncMock(return_value=mock_projections)
            
            # Make request
            response = client.get(f"/{scenario_id}/projections?position=QB")
            
            # Verify service was called correctly
            service_instance.get_scenario.assert_called_once_with(scenario_id)
            service_instance.get_scenario_projections.assert_called_once_with(
                scenario_id=scenario_id,
                position="QB",
                team=None
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["scenario_id"] == scenario_id
            assert data[1]["scenario_id"] == scenario_id
            assert data[0]["player_id"] == player_id_1
            assert data[1]["player_id"] == player_id_2
            assert data[0]["pass_yards"] == 5000.0
    
    def test_clone_scenario(self):
        """Test cloning a scenario."""
        source_scenario_id = str(uuid.uuid4())
        new_scenario_id = str(uuid.uuid4())
        
        # Mock responses from service
        mock_source_scenario = {
            "scenario_id": source_scenario_id,
            "name": "Baseline 2025",
            "description": "Default projections for 2025",
            "is_baseline": True,
            "base_scenario_id": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        mock_new_scenario = {
            "scenario_id": new_scenario_id,
            "name": "High Usage Clone",
            "description": "Clone of baseline with increased usage",
            "is_baseline": False,
            "base_scenario_id": source_scenario_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Patch the service methods
        with patch('backend.api.routes.scenarios.ScenarioService') as mock_service:
            service_instance = mock_service.return_value
            service_instance.get_scenario = AsyncMock(return_value=mock_source_scenario)
            service_instance.clone_scenario = AsyncMock(return_value=mock_new_scenario)
            
            # Make request
            new_name = "High Usage Clone"
            new_description = "Clone of baseline with increased usage"
            response = client.post(f"/{source_scenario_id}/clone?name={new_name}&description={new_description}")
            
            # Verify service was called correctly
            service_instance.get_scenario.assert_called_once_with(source_scenario_id)
            service_instance.clone_scenario.assert_called_once_with(
                source_scenario_id=source_scenario_id,
                new_name=new_name,
                new_description=new_description
            )
            
            # Verify response
            assert response.status_code == 201
            data = response.json()
            assert data["scenario_id"] == new_scenario_id
            assert data["name"] == new_name
            assert data["description"] == new_description
            assert data["base_scenario_id"] == source_scenario_id
    
    def test_delete_scenario(self):
        """Test deleting a scenario."""
        scenario_id = str(uuid.uuid4())
        
        # Mock response from service
        mock_scenario = {
            "scenario_id": scenario_id,
            "name": "Outdated Scenario",
            "description": "This will be deleted",
            "is_baseline": False,
            "base_scenario_id": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Patch the service methods
        with patch('backend.api.routes.scenarios.ScenarioService') as mock_service:
            service_instance = mock_service.return_value
            service_instance.get_scenario = AsyncMock(return_value=mock_scenario)
            service_instance.delete_scenario = AsyncMock(return_value=True)
            
            # Make request
            response = client.delete(f"/{scenario_id}")
            
            # Verify service was called correctly
            service_instance.get_scenario.assert_called_once_with(scenario_id)
            service_instance.delete_scenario.assert_called_once_with(scenario_id)
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "Scenario deleted successfully" in data["message"]
    
    def test_delete_scenario_not_found(self):
        """Test attempting to delete a non-existent scenario."""
        scenario_id = str(uuid.uuid4())
        
        # Patch the service method to return None
        with patch('backend.api.routes.scenarios.ScenarioService') as mock_service:
            service_instance = mock_service.return_value
            service_instance.get_scenario = AsyncMock(return_value=None)
            
            # Make request
            response = client.delete(f"/{scenario_id}")
            
            # Verify response
            assert response.status_code == 404
            assert "Scenario not found" in response.json()["detail"]
    
    def test_compare_scenarios(self):
        """Test comparing projections across multiple scenarios."""
        scenario_id_1 = str(uuid.uuid4())
        scenario_id_2 = str(uuid.uuid4())
        player_id = str(uuid.uuid4())
        
        # Request data
        request_data = {
            "scenario_ids": [scenario_id_1, scenario_id_2],
            "position": "QB"
        }
        
        # Mock response from service
        mock_comparison = {
            "scenarios": [
                {"id": scenario_id_1, "name": "Baseline 2025"},
                {"id": scenario_id_2, "name": "High Passing Volume"}
            ],
            "players": [
                {
                    "player_id": player_id,
                    "name": "Patrick Mahomes",
                    "team": "KC",
                    "position": "QB",
                    "scenarios": {
                        "Baseline 2025": {
                            "half_ppr": 350.5,
                            "pass_yards": 4800,
                            "pass_td": 38
                        },
                        "High Passing Volume": {
                            "half_ppr": 390.2,
                            "pass_yards": 5200,
                            "pass_td": 42
                        }
                    }
                }
            ]
        }
        
        # Patch the service method
        with patch('backend.api.routes.scenarios.ScenarioService') as mock_service:
            service_instance = mock_service.return_value
            service_instance.compare_scenarios = AsyncMock(return_value=mock_comparison)
            
            # Make request
            response = client.post("/compare", json=request_data)
            
            # Verify service was called correctly
            service_instance.compare_scenarios.assert_called_once_with(
                scenario_ids=request_data["scenario_ids"],
                position=request_data["position"]
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert len(data["scenarios"]) == 2
            assert data["scenarios"][0]["id"] == scenario_id_1
            assert data["scenarios"][1]["id"] == scenario_id_2
            assert len(data["players"]) == 1
            assert data["players"][0]["player_id"] == player_id
            assert data["players"][0]["name"] == "Patrick Mahomes"
            assert "Baseline 2025" in data["players"][0]["scenarios"]
            assert "High Passing Volume" in data["players"][0]["scenarios"]
            assert data["players"][0]["scenarios"]["High Passing Volume"]["pass_yards"] == 5200