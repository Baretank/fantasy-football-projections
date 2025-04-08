import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import uuid
import json
from datetime import datetime

from backend.api.routes.overrides import router
from backend.api.schemas import (
    StatOverrideRequest,
    StatOverrideResponse,
    BatchOverrideRequest,
    BatchOverrideResponse,
    SuccessResponse
)
from backend.services.override_service import OverrideService
from backend.database.models import StatOverride

# Create isolated test app with just the overrides router
app = FastAPI()
app.include_router(router)
client = TestClient(app)

class TestOverrideRoutes:
    
    def test_create_override_success(self):
        """Test successful creation of an override."""
        # Mock data for request
        override_request = {
            "player_id": str(uuid.uuid4()),
            "projection_id": str(uuid.uuid4()),
            "stat_name": "pass_attempts",
            "manual_value": 625.0,
            "notes": "Testing override creation"
        }
        
        # Mock response from service
        mock_override = StatOverride(
            override_id=str(uuid.uuid4()),
            player_id=override_request["player_id"],
            projection_id=override_request["projection_id"],
            stat_name=override_request["stat_name"],
            calculated_value=580.0,
            manual_value=override_request["manual_value"],
            notes=override_request["notes"],
            created_at=datetime.utcnow()
        )
        
        # Patch the service method
        with patch('backend.api.routes.overrides.OverrideService') as mock_service:
            service_instance = mock_service.return_value
            service_instance.create_override = AsyncMock(return_value=mock_override)
            
            # Make request
            response = client.post("/overrides/", json=override_request)
            
            # Verify service was called correctly
            service_instance.create_override.assert_called_once_with(
                player_id=override_request["player_id"],
                projection_id=override_request["projection_id"],
                stat_name=override_request["stat_name"],
                manual_value=override_request["manual_value"],
                notes=override_request["notes"]
            )
            
            # Verify response
            assert response.status_code == 201
            data = response.json()
            assert data["player_id"] == override_request["player_id"]
            assert data["projection_id"] == override_request["projection_id"]
            assert data["stat_name"] == override_request["stat_name"]
            assert data["manual_value"] == override_request["manual_value"]
            assert data["calculated_value"] == 580.0
            assert data["notes"] == override_request["notes"]
    
    def test_create_override_failure(self):
        """Test handling of failure when creating an override."""
        # Mock data for request
        override_request = {
            "player_id": str(uuid.uuid4()),
            "projection_id": str(uuid.uuid4()),
            "stat_name": "invalid_stat",
            "manual_value": 625.0,
            "notes": "Testing invalid stat"
        }
        
        # Patch the service method to return None (failure)
        with patch('backend.api.routes.overrides.OverrideService') as mock_service:
            service_instance = mock_service.return_value
            service_instance.create_override = AsyncMock(return_value=None)
            
            # Make request
            response = client.post("/overrides/", json=override_request)
            
            # Verify response
            assert response.status_code == 500
            assert "Error creating override" in response.json()["detail"]
    
    def test_get_player_overrides(self):
        """Test retrieving all overrides for a player."""
        player_id = str(uuid.uuid4())
        
        # Mock response from service
        mock_overrides = [
            StatOverride(
                override_id=str(uuid.uuid4()),
                player_id=player_id,
                projection_id=str(uuid.uuid4()),
                stat_name="pass_attempts",
                calculated_value=580.0,
                manual_value=625.0,
                notes="Testing player override 1",
                created_at=datetime.utcnow()
            ),
            StatOverride(
                override_id=str(uuid.uuid4()),
                player_id=player_id,
                projection_id=str(uuid.uuid4()),
                stat_name="pass_yards",
                calculated_value=4800.0,
                manual_value=5100.0,
                notes="Testing player override 2",
                created_at=datetime.utcnow()
            )
        ]
        
        # Patch the service method
        with patch('backend.api.routes.overrides.OverrideService') as mock_service:
            service_instance = mock_service.return_value
            service_instance.get_player_overrides = AsyncMock(return_value=mock_overrides)
            
            # Make request
            response = client.get(f"/overrides/player/{player_id}")
            
            # Verify service was called correctly
            service_instance.get_player_overrides.assert_called_once_with(player_id)
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["player_id"] == player_id
            assert data[1]["player_id"] == player_id
            assert data[0]["stat_name"] == "pass_attempts"
            assert data[1]["stat_name"] == "pass_yards"
    
    def test_get_projection_overrides(self):
        """Test retrieving all overrides for a projection."""
        projection_id = str(uuid.uuid4())
        player_id = str(uuid.uuid4())
        
        # Mock response from service
        mock_overrides = [
            StatOverride(
                override_id=str(uuid.uuid4()),
                player_id=player_id,
                projection_id=projection_id,
                stat_name="completions",
                calculated_value=380.0,
                manual_value=400.0,
                notes="Testing projection override 1",
                created_at=datetime.utcnow()
            ),
            StatOverride(
                override_id=str(uuid.uuid4()),
                player_id=player_id,
                projection_id=projection_id,
                stat_name="pass_td",
                calculated_value=38.0,
                manual_value=42.0,
                notes="Testing projection override 2",
                created_at=datetime.utcnow()
            )
        ]
        
        # Patch the service method
        with patch('backend.api.routes.overrides.OverrideService') as mock_service:
            service_instance = mock_service.return_value
            service_instance.get_projection_overrides = AsyncMock(return_value=mock_overrides)
            
            # Make request
            response = client.get(f"/overrides/projection/{projection_id}")
            
            # Verify service was called correctly
            service_instance.get_projection_overrides.assert_called_once_with(projection_id)
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["projection_id"] == projection_id
            assert data[1]["projection_id"] == projection_id
            assert data[0]["stat_name"] == "completions"
            assert data[1]["stat_name"] == "pass_td"
    
    def test_delete_override_success(self):
        """Test successfully deleting an override."""
        override_id = str(uuid.uuid4())
        
        # Patch the service method
        with patch('backend.api.routes.overrides.OverrideService') as mock_service:
            service_instance = mock_service.return_value
            service_instance.delete_override = AsyncMock(return_value=True)
            
            # Make request
            response = client.delete(f"/overrides/{override_id}")
            
            # Verify service was called correctly
            service_instance.delete_override.assert_called_once_with(override_id)
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "Override deleted successfully" in data["message"]
    
    def test_delete_override_not_found(self):
        """Test deleting a non-existent override."""
        override_id = str(uuid.uuid4())
        
        # Patch the service method to return False (not found)
        with patch('backend.api.routes.overrides.OverrideService') as mock_service:
            service_instance = mock_service.return_value
            service_instance.delete_override = AsyncMock(return_value=False)
            
            # Make request
            response = client.delete(f"/overrides/{override_id}")
            
            # Verify response
            assert response.status_code == 404
            assert "Override not found" in response.json()["detail"]
    
    def test_batch_override(self):
        """Test applying a batch override to multiple players."""
        # Mock data for request
        batch_request = {
            "player_ids": [str(uuid.uuid4()), str(uuid.uuid4())],
            "stat_name": "games",
            "value": {"method": "percentage", "amount": -5},
            "notes": "Testing batch override with percentage"
        }
        
        # Mock response from service that matches BatchOverrideResponse schema
        mock_results = {
            "results": {
                batch_request["player_ids"][0]: {
                    "player_id": batch_request["player_ids"][0],
                    "success": True,
                    "override_id": str(uuid.uuid4()),
                    "old_value": 17.0,
                    "new_value": 16.15
                },
                batch_request["player_ids"][1]: {
                    "player_id": batch_request["player_ids"][1],
                    "success": True,
                    "override_id": str(uuid.uuid4()),
                    "old_value": 16.0,
                    "new_value": 15.2
                }
            }
        }
        
        # Patch the service method
        with patch('backend.api.routes.overrides.OverrideService') as mock_service:
            service_instance = mock_service.return_value
            service_instance.batch_override = AsyncMock(return_value=mock_results)
            
            # Make request
            response = client.post("/overrides/batch", json=batch_request)
            
            # Verify service was called correctly
            service_instance.batch_override.assert_called_once_with(
                player_ids=batch_request["player_ids"],
                stat_name=batch_request["stat_name"],
                value=batch_request["value"],
                notes=batch_request["notes"]
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert batch_request["player_ids"][0] in data["results"]
            assert batch_request["player_ids"][1] in data["results"]
            assert data["results"][batch_request["player_ids"][0]]["success"] is True
            assert data["results"][batch_request["player_ids"][1]]["success"] is True
    
    def test_batch_override_validation_error(self):
        """Test batch override with invalid data."""
        # Mock data with invalid value
        batch_request = {
            "player_ids": [str(uuid.uuid4()), str(uuid.uuid4())],
            "stat_name": "games",
            "value": {"invalid_method": "wrong", "amount": -5},
            "notes": "Testing batch override with invalid method"
        }
        
        # Patch the service method to raise ValueError
        with patch('backend.api.routes.overrides.OverrideService') as mock_service:
            service_instance = mock_service.return_value
            service_instance.batch_override = AsyncMock(side_effect=ValueError("Invalid adjustment method"))
            
            # Make request
            response = client.post("/overrides/batch", json=batch_request)
            
            # Verify response
            assert response.status_code == 400
            assert "Invalid adjustment method" in response.json()["detail"]