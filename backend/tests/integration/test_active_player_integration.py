import os
import tempfile
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

from backend.services.active_player_service import ActivePlayerService
from backend.services.nfl_data_import_service import NFLDataImportService
from backend.database.models import Player


@pytest.fixture
def sample_csv_content():
    """Sample CSV content for testing."""
    return """name,team,position,player_id
Patrick Mahomes,KC,QB,mahomes_id
Travis Kelce,KC,TE,kelce_id
Cooper Kupp,LAR,WR,kupp_id
Justin Jefferson,MIN,WR,jefferson_id
"""


@pytest.fixture
def active_players_csv(sample_csv_content):
    """Create a temporary CSV file with sample content."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(sample_csv_content)
        csv_path = f.name
    
    yield csv_path
    
    # Cleanup
    if os.path.exists(csv_path):
        os.unlink(csv_path)


@pytest.fixture
def mock_nfl_data_adapter():
    """Mock NFL data adapter with sample player data."""
    adapter = MagicMock()
    
    # Sample player data that would be returned from the NFL data adapter
    players_df = pd.DataFrame({
        'player_id': ['mahomes_id', 'kelce_id', 'kupp_id', 'jefferson_id', 'inactive_id'],
        'display_name': ['Patrick Mahomes', 'Travis Kelce', 'Cooper Kupp', 'Justin Jefferson', 'Inactive Player'],
        'team_abbr': ['KC', 'KC', 'LAR', 'MIN', 'UNK'],
        'position': ['QB', 'TE', 'WR', 'WR', 'QB'],
        'status': ['Active', 'Active', 'Active', 'Active', 'Inactive']
    })
    
    adapter.get_players.return_value = players_df
    return adapter


@pytest.mark.asyncio
async def test_import_players_with_active_filtering(test_db, active_players_csv, mock_nfl_data_adapter):
    """Test that player import correctly filters active players."""
    # Setup the NFLDataImportService with the mock adapter
    service = NFLDataImportService(test_db)
    service.nfl_data_adapter = mock_nfl_data_adapter
    
    # Create a real ActivePlayerService with our test CSV
    active_service = ActivePlayerService(csv_path=active_players_csv)
    
    # Patch the import_players method to use our active_service
    with patch('backend.services.nfl_data_import_service.ActivePlayerService', return_value=active_service):
        # Run the import_players method
        result = await service.import_players(season=2025)
        
        # Check that only players from our active CSV were imported
        assert result['total_processed'] == 4  # The active players from our CSV
        
        # Verify the players in the database match our active players
        players = test_db.query(Player).all()
        player_names = [p.name for p in players]
        
        # These should be in the database
        assert 'Patrick Mahomes' in player_names
        assert 'Travis Kelce' in player_names
        assert 'Cooper Kupp' in player_names
        assert 'Justin Jefferson' in player_names
        
        # This should not be in the database due to active filtering
        assert 'Inactive Player' not in player_names


@pytest.mark.asyncio
async def test_integration_with_nfl_data_import_empty_active_list(test_db, mock_nfl_data_adapter):
    """Test behavior when active players list is empty."""
    # Setup the NFLDataImportService with the mock adapter
    service = NFLDataImportService(test_db)
    service.nfl_data_adapter = mock_nfl_data_adapter
    
    # Create an ActivePlayerService with a non-existent CSV (will result in empty active lists)
    active_service = ActivePlayerService(csv_path='non_existent_file.csv')
    
    # Patch the import_players method to use our empty active_service
    with patch('backend.services.nfl_data_import_service.ActivePlayerService', return_value=active_service):
        # Run the import_players method
        # Since active filtering will result in no players, the import should fall back
        # to using all players from the adapter
        result = await service.import_players(season=2025)
        
        # Check that all players were processed (since active filtering would fail)
        assert result['total_processed'] == 5  # All players from the mock data
        
        # Verify players in database
        players = test_db.query(Player).all()
        assert len(players) == 5


@pytest.mark.asyncio
async def test_full_import_season_with_active_filtering(test_db, active_players_csv, mocker):
    """Test the full import_season process with active player filtering."""
    # Setup mock data adapter
    mock_adapter = MagicMock()
    
    # Sample player data
    players_df = pd.DataFrame({
        'player_id': ['mahomes_id', 'kelce_id', 'inactive_id'],
        'display_name': ['Patrick Mahomes', 'Travis Kelce', 'Inactive Player'],
        'team_abbr': ['KC', 'KC', 'UNK'],
        'position': ['QB', 'TE', 'QB'],
        'status': ['Active', 'Active', 'Inactive']
    })
    
    # Mock additional data needed for import_season
    mock_adapter.get_players.return_value = players_df
    mock_adapter.get_weekly_stats.return_value = pd.DataFrame()
    mock_adapter.get_schedules.return_value = pd.DataFrame()
    mock_adapter.get_team_stats.return_value = pd.DataFrame()
    
    # Mock the various steps to speed up testing and focus on active player filtering
    mocker.patch.object(NFLDataImportService, 'import_weekly_stats', return_value={'weekly_stats_added': 0})
    mocker.patch.object(NFLDataImportService, 'import_team_stats', return_value={'teams_processed': 0})
    mocker.patch.object(NFLDataImportService, 'calculate_season_totals', return_value={'totals_created': 0})
    mocker.patch.object(NFLDataImportService, 'validate_data', return_value={'issues_fixed': 0})
    
    # Create NFLDataImportService with mocked adapter
    service = NFLDataImportService(test_db)
    service.nfl_data_adapter = mock_adapter
    
    # Create a real ActivePlayerService with our test CSV
    active_service = ActivePlayerService(csv_path=active_players_csv)
    
    # Patch the ActivePlayerService constructor
    with patch('backend.services.nfl_data_import_service.ActivePlayerService', return_value=active_service):
        # Run the import_season method
        await service.import_season(season=2025)
        
        # Verify players in database - only active players should be present
        players = test_db.query(Player).all()
        player_names = [p.name for p in players]
        
        # These should be in the database (they're in our active CSV)
        assert 'Patrick Mahomes' in player_names
        assert 'Travis Kelce' in player_names
        
        # This should not be in the database (not in active CSV)
        assert 'Inactive Player' not in player_names