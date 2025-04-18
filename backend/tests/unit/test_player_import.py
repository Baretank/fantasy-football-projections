import os
import sys
import tempfile
import pytest
import pandas as pd
from datetime import datetime, date
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)

from backend.services.rookie_import_service import RookieImportService
from backend.scripts.convert_rookies import convert_to_json
from backend.scripts.seed_database import seed_players_from_csv


@pytest.fixture
def mock_db_session():
    """Create a mock database session for testing."""
    mock_session = MagicMock()
    mock_session.commit = MagicMock()
    mock_session.rollback = MagicMock()
    mock_session.close = MagicMock()
    mock_session.query = MagicMock()

    # Configure the query mock to return a filter mock
    mock_filter = MagicMock()
    mock_session.query.return_value.filter.return_value = mock_filter

    # Configure the filter mock to return None for .first()
    mock_filter.first.return_value = None

    return mock_session


@pytest.mark.asyncio
async def test_import_rookies_from_csv(mock_db_session):
    """Test importing rookies from a CSV file."""
    # Create a temporary CSV file
    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w+", delete=False) as tmp:
        tmp.write("name,position,team,height,weight,date_of_birth\n")
        tmp.write("Test Rookie,QB,DAL,75,220,1999-01-01\n")
        tmp_path = tmp.name

    try:
        # Create service with mock db
        service = RookieImportService(mock_db_session)

        # Call the method
        success_count, errors = await service.import_rookies_from_csv(tmp_path)

        # Assertions
        assert success_count == 1
        assert len(errors) == 0
        assert mock_db_session.add.called
        assert mock_db_session.commit.called

        # Check the player data
        player_data = mock_db_session.add.call_args[0][0]
        assert player_data.name == "Test Rookie"
        assert player_data.position == "QB"
        assert player_data.team == "DAL"
        assert player_data.height == 75
        assert player_data.weight == 220
        assert player_data.date_of_birth == date(1999, 1, 1)
        assert player_data.status == "Rookie"
    finally:
        # Clean up
        os.unlink(tmp_path)


@pytest.mark.asyncio
async def test_import_rookies_from_excel(mock_db_session):
    """Test importing rookies from an Excel file."""
    # Create a temporary Excel file
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp_path = tmp.name

    # Create Excel file with test data
    df = pd.DataFrame(
        {
            "Name": ["Test Rookie Excel"],
            "Pos": ["WR"],
            "Team": ["SEA"],
            "Height": ["6-2"],  # Test feet-inches format
            "Weight": [195],
            "DOB": ["2000-03-15"],
        }
    )
    df.to_excel(tmp_path, index=False)

    try:
        # Create service with mock db
        service = RookieImportService(mock_db_session)

        # Call the method
        success_count, errors = await service.import_rookies_from_excel(tmp_path)

        # Assertions
        assert success_count == 1
        assert len(errors) == 0
        assert mock_db_session.add.called
        assert mock_db_session.commit.called

        # Check the player data
        player_data = mock_db_session.add.call_args[0][0]
        assert player_data.name == "Test Rookie Excel"
        assert player_data.position == "WR"
        assert player_data.team == "SEA"
        assert player_data.height == 74  # 6'2" = 74 inches
        assert player_data.weight == 195
        assert player_data.date_of_birth == date(2000, 3, 15)
        assert player_data.status == "Rookie"
    finally:
        # Clean up
        os.unlink(tmp_path)


@pytest.mark.asyncio
async def test_import_rookies_from_json(mock_db_session):
    """Test importing rookies from a JSON file."""
    # Create a temporary JSON file
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w+", delete=False) as tmp:
        tmp.write(
            """{
            "version": "1.0",
            "last_updated": "2025-03-30",
            "rookies": [
                {
                    "name": "Test Rookie JSON",
                    "position": "RB",
                    "team": "NYG",
                    "height": 71,
                    "weight": 215,
                    "date_of_birth": "2001-05-12",
                    "draft_position": 42,
                    "draft_team": "NYG",
                    "draft_round": 2,
                    "draft_pick": 10
                }
            ]
        }"""
        )
        tmp_path = tmp.name

    try:
        # Create service with mock db
        service = RookieImportService(mock_db_session)

        # Call the method
        success_count, errors = await service.import_rookies_from_json(tmp_path)

        # Assertions
        assert success_count == 1
        assert len(errors) == 0
        assert mock_db_session.add.called
        assert mock_db_session.commit.called

        # Check the player data
        player_data = mock_db_session.add.call_args[0][0]
        assert player_data.name == "Test Rookie JSON"
        assert player_data.position == "RB"
        assert player_data.team == "NYG"
        assert player_data.height == 71
        assert player_data.weight == 215
        assert player_data.date_of_birth == date(2001, 5, 12)
        assert player_data.draft_position == 42
        assert player_data.draft_team == "NYG"
        assert player_data.draft_round == 2
        assert player_data.draft_pick == 10
        assert player_data.status == "Rookie"
    finally:
        # Clean up
        os.unlink(tmp_path)


@pytest.mark.asyncio
async def test_import_rookies_auto_detect(mock_db_session):
    """Test auto-detecting file format when importing rookies."""
    # Create a temporary CSV file
    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w+", delete=False) as tmp:
        tmp.write("name,position,team\n")
        tmp.write("Test Auto Detect,TE,KC\n")
        tmp_path = tmp.name

    try:
        # Create service with mock db
        service = RookieImportService(mock_db_session)

        # Mock the import methods to verify which one is called
        service.import_rookies_from_csv = AsyncMock(return_value=(1, []))
        service.import_rookies_from_excel = AsyncMock(return_value=(0, []))
        service.import_rookies_from_json = AsyncMock(return_value=(0, []))

        # Call the method
        await service.import_rookies(tmp_path)

        # Assert that the correct import method was called
        service.import_rookies_from_csv.assert_called_once_with(tmp_path)
        service.import_rookies_from_excel.assert_not_called()
        service.import_rookies_from_json.assert_not_called()
    finally:
        # Clean up
        os.unlink(tmp_path)


def test_convert_to_json_excel_format():
    """Test converting an Excel file to JSON."""
    # Create a temporary Excel file
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_in:
        tmp_in_path = tmp_in.name

    # Create a temporary output JSON file
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp_out:
        tmp_out_path = tmp_out.name

    # Create Excel file with test data
    df = pd.DataFrame(
        {
            "Name": ["Test Convert"],
            "Pos": ["QB"],
            "Team": ["KC"],
            "Height": [76],
            "Weight": [220],
            "DOB": ["1998-09-17"],
            "Gm": [17],
            "ADP": [12],
        }
    )
    df.to_excel(tmp_in_path, index=False)

    try:
        # Call the convert function (with force=True to avoid prompting)
        result = convert_to_json(tmp_in_path, tmp_out_path, force=True)

        # Check if conversion was successful
        assert result is True

        # Read the generated JSON
        import json

        with open(tmp_out_path, "r") as f:
            data = json.load(f)

        # Validate the JSON structure
        assert "version" in data
        assert "rookies" in data
        assert len(data["rookies"]) == 1

        rookie = data["rookies"][0]
        assert rookie["name"] == "Test Convert"
        assert rookie["position"] == "QB"
        assert rookie["team"] == "KC"
        assert rookie["height"] == 76
        assert rookie["weight"] == 220
        assert rookie["date_of_birth"] == "1998-09-17"
        assert rookie["draft_position"] == 12
        assert rookie["projected_stats"]["games"] == 17
    finally:
        # Clean up
        os.unlink(tmp_in_path)
        os.unlink(tmp_out_path)


def test_seed_players_from_csv():
    """Test seeding the database from a CSV file."""
    # Create a mock db session
    mock_session = MagicMock()
    mock_session.query.return_value.filter.return_value.first.return_value = None

    # Create a temporary CSV file
    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w+", delete=False) as tmp:
        tmp.write(
            "name,team,position,height,weight,date_of_birth,status,depth_chart_position,draft_team,draft_round,draft_pick\n"
        )
        tmp.write("Active Player,DAL,QB,75,220,1995-04-15,Active,Starter,DAL,1,4\n")
        tmp.write("Practice Squad,NYJ,RB,71,205,1998-07-22,Active,Backup,NYJ,6,198\n")
        tmp_path = tmp.name

    try:
        # Call the seeding function
        with patch("backend.scripts.seed_database.SessionLocal", return_value=mock_session):
            result = seed_players_from_csv(tmp_path)

        # Assertions
        assert result is True
        assert mock_session.add.call_count == 2
        assert mock_session.commit.called

        # Verify player data
        player1 = mock_session.add.call_args_list[0][0][0]
        assert player1.name == "Active Player"
        assert player1.team == "DAL"
        assert player1.position == "QB"
        assert player1.height == 75
        assert player1.weight == 220
        assert player1.date_of_birth == date(1995, 4, 15)
        assert player1.status == "Active"
        assert player1.depth_chart_position == "Starter"
        assert player1.draft_team == "DAL"
        assert player1.draft_round == 1
        assert player1.draft_pick == 4

        player2 = mock_session.add.call_args_list[1][0][0]
        assert player2.name == "Practice Squad"
        assert player2.team == "NYJ"
        assert player2.position == "RB"
        assert player2.height == 71
        assert player2.weight == 205
        assert player2.date_of_birth == date(1998, 7, 22)
        assert player2.status == "Active"
        assert player2.depth_chart_position == "Backup"
        assert player2.draft_team == "NYJ"
        assert player2.draft_round == 6
        assert player2.draft_pick == 198
    finally:
        # Clean up
        os.unlink(tmp_path)
