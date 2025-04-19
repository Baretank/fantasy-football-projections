import os
import sys
import tempfile
import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import patch

# Add project root to path for imports
project_root = str(Path(__file__).parent.parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.database.database import SessionLocal
from backend.database.models import Player, BaseStat
from backend.services.active_player_service import ActivePlayerService
from backend.services.nfl_data_import_service import NFLDataImportService
from backend.services.query_service import QueryService
from backend.services.projection_service import ProjectionService


@pytest.fixture
def sample_csv_content():
    """Sample active players CSV content for testing."""
    return """name,team,position,player_id,status
Patrick Mahomes,KC,QB,mahomes_id,Active
Travis Kelce,KC,TE,kelce_id,Active
Cooper Kupp,LAR,WR,kupp_id,Active
Justin Jefferson,MIN,WR,jefferson_id,Active
Ja'Marr Chase,CIN,WR,chase_id,Active
Christian McCaffrey,SF,RB,mccaffrey_id,Active
"""


@pytest.fixture
def temp_active_players_csv(sample_csv_content):
    """Create a temporary active_players.csv file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(sample_csv_content)
        csv_path = f.name
    
    yield csv_path
    
    # Cleanup
    if os.path.exists(csv_path):
        os.unlink(csv_path)


@pytest.fixture
def db_session():
    """Create a database session for testing."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.mark.asyncio
async def test_end_to_end_active_players_filtering(db_session, temp_active_players_csv, mocker):
    """
    Test the complete end-to-end flow of importing data with active player filtering:
    1. Import player data through NFLDataImportService
    2. Verify active players are properly filtered
    3. Check that projections only include active players
    """
    # Mock NFL data adapter responses
    mock_adapter = mocker.MagicMock()
    
    # Sample player data including both active and inactive players
    players_df = pd.DataFrame({
        'player_id': [
            'mahomes_id', 'kelce_id', 'kupp_id', 'jefferson_id', 
            'chase_id', 'mccaffrey_id', 'inactive_id1', 'inactive_id2'
        ],
        'display_name': [
            'Patrick Mahomes', 'Travis Kelce', 'Cooper Kupp', 'Justin Jefferson', 
            'Ja\'Marr Chase', 'Christian McCaffrey', 'Inactive Player 1', 'Inactive Player 2'
        ],
        'team_abbr': ['KC', 'KC', 'LAR', 'MIN', 'CIN', 'SF', 'UNK', 'UNK'],
        'position': ['QB', 'TE', 'WR', 'WR', 'WR', 'RB', 'QB', 'RB'],
        'status': ['Active', 'Active', 'Active', 'Active', 'Active', 'Active', 'Inactive', 'Inactive']
    })
    
    # Set up mock responses
    mock_adapter.get_players.return_value = players_df
    mock_adapter.get_weekly_stats.return_value = pd.DataFrame()
    mock_adapter.get_schedules.return_value = pd.DataFrame()
    mock_adapter.get_team_stats.return_value = pd.DataFrame()
    
    # Patch certain methods to speed up testing
    mocker.patch.object(NFLDataImportService, 'import_weekly_stats', return_value={'weekly_stats_added': 0})
    mocker.patch.object(NFLDataImportService, 'import_team_stats', return_value={'teams_processed': 0})
    mocker.patch.object(NFLDataImportService, 'calculate_season_totals', return_value={'totals_created': 0})
    mocker.patch.object(NFLDataImportService, 'validate_data', return_value={'issues_fixed': 0})
    
    # Create service instances
    nfl_import_service = NFLDataImportService(db_session)
    nfl_import_service.nfl_data_adapter = mock_adapter
    
    # Create a real ActivePlayerService with our test CSV
    active_service = ActivePlayerService(csv_path=temp_active_players_csv)
    
    # STEP 1: Run the import with active player filtering
    with patch('backend.services.nfl_data_import_service.ActivePlayerService', return_value=active_service):
        # Run the import
        await nfl_import_service.import_season(season=2025)
        
        # Verify players in database - only active players should be present
        players = db_session.query(Player).all()
        player_names = [p.name for p in players]
        
        # These should be in the database (in our active CSV)
        for name in ['Patrick Mahomes', 'Travis Kelce', 'Cooper Kupp', 'Justin Jefferson', 
                     'Ja\'Marr Chase', 'Christian McCaffrey']:
            assert name in player_names
        
        # These should NOT be in the database (not in active CSV)
        assert 'Inactive Player 1' not in player_names
        assert 'Inactive Player 2' not in player_names
    
    # STEP 2: Create some base stats for these players to test query service
    # Add some mock stats to players for testing
    for player in db_session.query(Player).all():
        # Add a base stat for half_ppr and games for each active player
        half_ppr_stat = BaseStat(
            stat_id=str(player.player_id) + "_half_ppr",
            player_id=player.player_id,
            season=2025,
            stat_type="half_ppr",
            value=15.0  # Some arbitrary value
        )
        games_stat = BaseStat(
            stat_id=str(player.player_id) + "_games",
            player_id=player.player_id,
            season=2025,
            stat_type="games",
            value=17.0
        )
        db_session.add(half_ppr_stat)
        db_session.add(games_stat)
    
    db_session.commit()
    
    # STEP 3: Query the players to verify only active players are returned
    query_service = QueryService(db_session)
    players_result = await query_service.get_players_with_projections(season=2025)
    
    # Check that we only get the active players
    player_ids = [p.player_id for p in players_result]
    assert len(player_ids) == 6  # 6 active players from our CSV
    
    # Check specific active players
    for player_id in ['mahomes_id', 'kelce_id', 'kupp_id', 'jefferson_id', 'chase_id', 'mccaffrey_id']:
        assert player_id in player_ids
    
    # Check inactive players are excluded
    assert 'inactive_id1' not in player_ids
    assert 'inactive_id2' not in player_ids
    
    # STEP 4: Test integration with projection service
    projection_service = ProjectionService(db_session)
    
    # Create a mock projection
    projections = await projection_service.generate_projections(season=2025)
    
    # Verify only active players have projections
    projection_player_ids = [p.player_id for p in projections]
    
    # Check active players have projections
    for player_id in ['mahomes_id', 'kelce_id', 'kupp_id', 'jefferson_id', 'chase_id', 'mccaffrey_id']:
        assert player_id in projection_player_ids
    
    # Check inactive players don't have projections
    assert 'inactive_id1' not in projection_player_ids
    assert 'inactive_id2' not in projection_player_ids