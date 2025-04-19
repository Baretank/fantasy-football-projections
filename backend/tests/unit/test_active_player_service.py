import os
import tempfile
import pytest
import pandas as pd
from pandas.testing import assert_frame_equal

from backend.services.active_player_service import ActivePlayerService


@pytest.fixture
def sample_csv_content():
    """Sample CSV content for testing."""
    return """name,team,position,player_id,status
Patrick Mahomes,KC,QB,mahomes_id,Active
Travis Kelce,KC,TE,kelce_id,Active
Christian McCaffrey,SF,RB,mccaffrey_id,Active
Retired Player,DEN,QB,retired_id,Inactive
"""


@pytest.fixture
def temp_csv_file(sample_csv_content):
    """Create a temporary CSV file with sample content."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(sample_csv_content)
        return f.name


@pytest.fixture
def sample_players_df():
    """Sample players DataFrame for testing."""
    return pd.DataFrame({
        'display_name': ['Patrick Mahomes', 'Travis Kelce', 'Justin Jefferson', 'Lamar Jackson'],
        'team_abbr': ['KC', 'KC', 'MIN', 'BAL'],
        'position': ['QB', 'TE', 'WR', 'QB'],
        'player_id': ['mahomes_id', 'kelce_id', 'jefferson_id', 'jackson_id'],
        'height': [75, 77, 73, 74],
        'weight': [230, 250, 195, 215],
        'status': ['Active', 'Active', 'Active', 'Active']
    })


def test_active_player_service_initialization(temp_csv_file):
    """Test initializing the ActivePlayerService with a CSV file."""
    service = ActivePlayerService(csv_path=temp_csv_file)
    
    # Check that the active sets were populated
    assert len(service._active_names) == 4  # All names including inactive
    assert len(service._active_teams) == 3
    
    # Check specific values
    assert 'patrick mahomes' in service._active_names
    assert 'travis kelce' in service._active_names
    assert 'christian mccaffrey' in service._active_names
    assert 'KC' in service._active_teams
    assert 'SF' in service._active_teams
    assert 'DEN' in service._active_teams


def test_active_player_service_empty_csv():
    """Test initializing with non-existent CSV creates empty sets."""
    service = ActivePlayerService(csv_path='non_existent_file.csv')
    
    assert len(service._active_names) == 0
    assert len(service._active_teams) == 0


def test_filter_active_players(temp_csv_file, sample_players_df):
    """Test filtering players based on active roster."""
    service = ActivePlayerService(csv_path=temp_csv_file)
    
    # Filter the sample DataFrame with default current season
    filtered_df = service.filter_active(sample_players_df)
    
    # Should only return Mahomes and Kelce (players on KC roster from our CSV)
    assert len(filtered_df) == 2
    assert 'Patrick Mahomes' in filtered_df['display_name'].values
    assert 'Travis Kelce' in filtered_df['display_name'].values
    assert 'Justin Jefferson' not in filtered_df['display_name'].values
    assert 'Lamar Jackson' not in filtered_df['display_name'].values


def test_filter_active_players_for_historical_season(temp_csv_file, sample_players_df):
    """Test filtering players for historical seasons."""
    service = ActivePlayerService(csv_path=temp_csv_file)
    
    # Add fantasy points to the sample DataFrame
    sample_players_df['fantasy_points'] = [300, 250, 280, 320]
    
    # Filter for historical season (2024)
    filtered_df = service.filter_active(sample_players_df, season=2024)
    
    # Should keep all players with fantasy points > 0 
    assert len(filtered_df) == 4
    assert 'Patrick Mahomes' in filtered_df['display_name'].values
    assert 'Travis Kelce' in filtered_df['display_name'].values
    assert 'Justin Jefferson' in filtered_df['display_name'].values
    assert 'Lamar Jackson' in filtered_df['display_name'].values


def test_filter_active_players_status(temp_csv_file):
    """Test filtering based on player status."""
    service = ActivePlayerService(csv_path=temp_csv_file)
    
    # Create DataFrame with both active and inactive players
    status_df = pd.DataFrame({
        'display_name': ['Patrick Mahomes', 'Retired Player'],
        'team_abbr': ['KC', 'DEN'],
        'position': ['QB', 'QB'],
        'player_id': ['mahomes_id', 'retired_id'],
        'status': ['Active', 'Inactive']
    })
    
    # Filter for current season, should filter out inactive players
    filtered_df = service.filter_active(status_df, season=2025)
    
    # Should only return active players (Mahomes)
    assert len(filtered_df) == 1
    assert 'Patrick Mahomes' in filtered_df['display_name'].values
    assert 'Retired Player' not in filtered_df['display_name'].values


def test_filter_active_players_include_all_positions(temp_csv_file):
    """Test including all positions in filtering."""
    service = ActivePlayerService(csv_path=temp_csv_file)
    
    # Create DataFrame with both fantasy and non-fantasy positions
    pos_df = pd.DataFrame({
        'display_name': ['Patrick Mahomes', 'Justin Tucker', 'San Francisco'],
        'team_abbr': ['KC', 'BAL', 'SF'],
        'position': ['QB', 'K', 'DEF'],
        'status': ['Active', 'Active', 'Active']
    })
    
    # Filter with default position filtering
    filtered_default = service.filter_active(pos_df, season=2024)
    
    # Should only include fantasy positions by default
    assert len(filtered_default) == 1
    assert 'Justin Tucker' not in filtered_default['display_name'].values
    assert 'San Francisco' not in filtered_default['display_name'].values
    
    # Filter with include_all_positions=True
    filtered_all = service.filter_active(pos_df, season=2024, include_all_positions=True)
    
    # Should include all positions with teams
    assert len(filtered_all) == 3
    assert 'Patrick Mahomes' in filtered_all['display_name'].values
    assert 'Justin Tucker' in filtered_all['display_name'].values
    assert 'San Francisco' in filtered_all['display_name'].values


def test_filter_active_players_empty_df():
    """Test filtering an empty DataFrame."""
    service = ActivePlayerService()
    empty_df = pd.DataFrame()
    
    filtered_df = service.filter_active(empty_df)
    
    # Should return the empty DataFrame as is
    assert filtered_df.empty


def test_filter_active_players_no_matches(temp_csv_file):
    """Test filtering when no players match the active roster."""
    service = ActivePlayerService(csv_path=temp_csv_file)
    
    # Create DataFrame with players not in our active list
    no_match_df = pd.DataFrame({
        'display_name': ['Justin Jefferson', 'Lamar Jackson'],
        'team_abbr': ['MIN', 'BAL'],
        'position': ['WR', 'QB']
    })
    
    filtered_df = service.filter_active(no_match_df)
    
    # Should return an empty DataFrame for current season filtering
    assert len(filtered_df) == 0


def test_different_column_names(temp_csv_file):
    """Test handling different column names in the players DataFrame."""
    service = ActivePlayerService(csv_path=temp_csv_file)
    
    # Create DataFrame with different column names
    diff_cols_df = pd.DataFrame({
        'player_name': ['Patrick Mahomes', 'Travis Kelce'],
        'nfl_team': ['KC', 'KC']
    })
    
    # This should not raise errors but return empty DataFrame due to missing expected columns
    filtered_df = service.filter_active(diff_cols_df)
    assert len(filtered_df) == 0


def test_integration_with_import_service(temp_csv_file, sample_players_df):
    """Test integration with import services."""
    # Create the active player service
    active_service = ActivePlayerService(csv_path=temp_csv_file)
    
    # Apply filtering
    filtered_df = active_service.filter_active(sample_players_df)
    
    # Verify filtering results
    assert len(filtered_df) == 2
    assert 'Patrick Mahomes' in filtered_df['display_name'].values
    assert 'Travis Kelce' in filtered_df['display_name'].values


def test_get_active_teams(temp_csv_file):
    """Test getting list of active teams."""
    service = ActivePlayerService(csv_path=temp_csv_file)
    
    teams = service.get_active_teams()
    
    # Should return sorted list of teams
    assert teams == ['DEN', 'KC', 'SF']


def test_is_active_player(temp_csv_file):
    """Test checking if individual player is active."""
    service = ActivePlayerService(csv_path=temp_csv_file)
    
    # Test active players
    assert service.is_active_player('Patrick Mahomes', 'KC') == True
    assert service.is_active_player('Travis Kelce', 'KC') == True
    
    # Test inactive or non-existent players
    assert service.is_active_player('Justin Jefferson', 'MIN') == False
    assert service.is_active_player('Patrick Mahomes', 'SF') == False  # Wrong team