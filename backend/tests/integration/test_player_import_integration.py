import pytest
import os
import tempfile
import pandas as pd
import uuid
import json
from pathlib import Path
from sqlalchemy.orm import Session
import logging
from datetime import date

from backend.database.models import Player
from backend.services.player_import_service import PlayerImportService
from backend.services.rookie_import_service import RookieImportService

logger = logging.getLogger(__name__)

# Test file paths
TEST_DATA_DIR = "/tmp/test_data"
ROOKIE_CSV_PATH = os.path.join(TEST_DATA_DIR, "test_rookies.csv")
ROOKIE_JSON_PATH = os.path.join(TEST_DATA_DIR, "test_rookies.json")
VETERAN_CSV_PATH = os.path.join(TEST_DATA_DIR, "test_veterans.csv")


@pytest.fixture
def rookie_import_service(test_db):
    """Create rookie import service with test db."""
    return RookieImportService(test_db)


@pytest.fixture
def player_import_service(test_db):
    """Create player import service with test db."""
    return PlayerImportService(test_db)


@pytest.mark.asyncio
async def test_rookie_csv_import(test_db, rookie_import_service):
    """Test importing rookies from a CSV file."""
    # Ensure the test file exists
    assert os.path.exists(ROOKIE_CSV_PATH), f"Test file not found: {ROOKIE_CSV_PATH}"

    # Import rookies
    success_count, errors = await rookie_import_service.import_rookies_from_csv(ROOKIE_CSV_PATH)

    # Verify results
    assert success_count == 8, f"Expected 8 players to be imported, got {success_count}"
    assert len(errors) == 0, f"Expected no errors, got: {errors}"

    # Check database state
    rookies = test_db.query(Player).filter(Player.status == "Rookie").all()
    assert len(rookies) == 8

    # Verify a specific rookie's data
    caleb = test_db.query(Player).filter(Player.name == "Caleb Williams").first()
    assert caleb is not None
    assert caleb.position == "QB"
    assert caleb.team == "CHI"
    assert caleb.height == 74
    assert caleb.weight == 215
    assert caleb.draft_team == "CHI"
    assert caleb.draft_round == 1
    assert caleb.draft_pick == 1
    assert caleb.date_of_birth == date(2001, 11, 18)


@pytest.mark.asyncio
async def test_rookie_json_import(test_db, rookie_import_service):
    """Test importing rookies from a JSON file."""
    # Ensure the test file exists
    assert os.path.exists(ROOKIE_JSON_PATH), f"Test file not found: {ROOKIE_JSON_PATH}"

    # Import rookies
    success_count, errors = await rookie_import_service.import_rookies_from_json(ROOKIE_JSON_PATH)

    # Verify results
    assert success_count == 3, f"Expected 3 players to be imported, got {success_count}"
    assert len(errors) == 0, f"Expected no errors, got: {errors}"

    # Check database state
    rookies = test_db.query(Player).filter(Player.status == "Rookie").all()
    assert len(rookies) == 3

    # Verify a specific rookie's data
    nabers = test_db.query(Player).filter(Player.name == "Malik Nabers").first()
    assert nabers is not None
    assert nabers.position == "WR"
    assert nabers.team == "NYG"
    assert nabers.height == 72
    assert nabers.weight == 200
    assert nabers.draft_team == "NYG"
    assert nabers.draft_round == 1
    assert nabers.draft_pick == 6
    assert nabers.draft_position == 6


@pytest.mark.asyncio
async def test_auto_format_detection(test_db, rookie_import_service):
    """Test the automatic format detection for rookie imports."""
    # Test CSV detection
    success_count, errors = await rookie_import_service.import_rookies(ROOKIE_CSV_PATH)
    assert success_count == 8, f"Failed to auto-detect CSV format, imported {success_count}"

    # Clear database
    test_db.query(Player).delete()
    test_db.commit()

    # Test JSON detection
    success_count, errors = await rookie_import_service.import_rookies(ROOKIE_JSON_PATH)
    assert success_count == 3, f"Failed to auto-detect JSON format, imported {success_count}"


@pytest.mark.asyncio
async def test_veteran_import(test_db, player_import_service):
    """Test importing veteran players from CSV."""
    # Ensure the test file exists
    assert os.path.exists(VETERAN_CSV_PATH), f"Test file not found: {VETERAN_CSV_PATH}"

    # Import veterans
    success_count, errors = await player_import_service.import_players_from_csv(VETERAN_CSV_PATH)

    # Verify results
    assert success_count == 7, f"Expected 7 players to be imported, got {success_count}"
    assert len(errors) == 0, f"Expected no errors, got: {errors}"

    # Check database state
    veterans = test_db.query(Player).filter(Player.status == "Active").all()
    assert len(veterans) == 7

    # Verify a specific veteran's data
    mahomes = test_db.query(Player).filter(Player.name == "Patrick Mahomes").first()
    assert mahomes is not None
    assert mahomes.position == "QB"
    assert mahomes.team == "KC"
    assert mahomes.height == 75
    assert mahomes.weight == 227
    assert mahomes.status == "Active"
    assert mahomes.depth_chart_position == "Starter"


@pytest.mark.asyncio
async def test_update_existing_players(test_db, player_import_service):
    """Test updating existing players with new information."""
    # First create a player
    existing_player = Player(
        player_id=str(uuid.uuid4()),
        name="Patrick Mahomes",
        team="KC",
        position="QB",
        status="Active",
        height=75,
        weight=225,  # Different weight than in test file
    )
    test_db.add(existing_player)
    test_db.commit()

    original_id = existing_player.player_id

    # Now import players which should update the existing one
    success_count, errors = await player_import_service.import_players_from_csv(VETERAN_CSV_PATH)

    # Verify player was updated, not created anew
    updated_player = test_db.query(Player).filter(Player.name == "Patrick Mahomes").first()
    assert updated_player.player_id == original_id, "Player ID should not change"
    assert updated_player.weight == 227, "Player weight should be updated"
    assert (
        updated_player.depth_chart_position == "Starter"
    ), "Depth chart position should be updated"


@pytest.mark.asyncio
async def test_rookie_to_veteran_transition(test_db, rookie_import_service, player_import_service):
    """Test the workflow of a rookie transitioning to veteran status."""
    # First import as rookie
    await rookie_import_service.import_rookies_from_csv(ROOKIE_CSV_PATH)

    # Verify rookie status
    caleb = test_db.query(Player).filter(Player.name == "Caleb Williams").first()
    assert caleb.status == "Rookie"
    original_id = caleb.player_id

    # Create a temporary CSV with the player as a veteran
    temp_csv_path = os.path.join(TEST_DATA_DIR, "temp_transition.csv")
    pd.DataFrame(
        [
            {
                "name": "Caleb Williams",
                "team": "CHI",
                "position": "QB",
                "status": "Active",
                "depth_chart_position": "Starter",
            }
        ]
    ).to_csv(temp_csv_path, index=False)

    # Import as veteran
    await player_import_service.import_players_from_csv(temp_csv_path)

    # Verify status changed to Active
    updated_caleb = test_db.query(Player).filter(Player.name == "Caleb Williams").first()
    assert updated_caleb.player_id == original_id, "Player ID should not change"
    assert updated_caleb.status == "Active", "Status should be updated to Active"
    assert updated_caleb.depth_chart_position == "Starter", "Depth chart position should be updated"

    # Clean up
    os.remove(temp_csv_path)


@pytest.mark.asyncio
async def test_error_handling_invalid_data(test_db, rookie_import_service):
    """Test error handling with invalid data."""
    # Create invalid CSV with missing required fields
    temp_invalid_csv = os.path.join(TEST_DATA_DIR, "invalid_rookies.csv")
    pd.DataFrame(
        [
            {
                "name": "Missing Position Player"
                # Missing 'position' field which is required
            }
        ]
    ).to_csv(temp_invalid_csv, index=False)

    # Import should return error
    success_count, errors = await rookie_import_service.import_rookies_from_csv(temp_invalid_csv)

    # Verify results
    assert success_count == 0, "No players should be imported"
    assert len(errors) > 0, "Should have error messages"
    assert "missing required columns" in errors[0].lower(), f"Unexpected error: {errors[0]}"

    # Clean up
    os.remove(temp_invalid_csv)


@pytest.mark.asyncio
async def test_duplicate_handling(test_db, rookie_import_service):
    """Test handling of duplicate player imports."""
    # Import rookies
    await rookie_import_service.import_rookies_from_csv(ROOKIE_CSV_PATH)

    # Count before reimport
    original_count = test_db.query(Player).count()

    # Reimport the same file
    success_count, errors = await rookie_import_service.import_rookies_from_csv(ROOKIE_CSV_PATH)

    # Verify no new players were created
    new_count = test_db.query(Player).count()
    assert new_count == original_count, "No new players should be created on duplicate import"

    # But import should still succeed since it updates existing players
    assert success_count == 8, "All players should be processed as updates"
