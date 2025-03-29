import pytest
import uuid
from datetime import datetime
from unittest.mock import patch, MagicMock

from backend.database.models import Player, BaseStat, GameStats
from backend.services.data_validation import DataValidationService

@pytest.fixture
def mock_db():
    """Mock database session for unit testing."""
    return MagicMock()

@pytest.fixture
def validation_service(mock_db):
    """Create validation service with mock database."""
    return DataValidationService(mock_db)

def test_check_game_counts(validation_service, mock_db):
    """Test game count validation."""
    # Create a test player
    player = Player(
        player_id=str(uuid.uuid4()),
        name="Test Player",
        position="QB",
        team="TEST"
    )
    
    # Mock game stats query
    game_stats = [
        GameStats(
            game_stat_id=str(uuid.uuid4()),
            player_id=player.player_id,
            season=2023,
            week=1,
            opponent="OPP",
            game_location="home",
            result="W",
            team_score=21,
            opponent_score=10,
            stats={}
        ),
        GameStats(
            game_stat_id=str(uuid.uuid4()),
            player_id=player.player_id,
            season=2023,
            week=2,
            opponent="OPP",
            game_location="away",
            result="L",
            team_score=14,
            opponent_score=21,
            stats={}
        )
    ]
    
    # Mock BaseStat query when games stat exists but is incorrect
    base_stat = BaseStat(
        stat_id=str(uuid.uuid4()),
        player_id=player.player_id,
        season=2023,
        stat_type="games",
        value=1.0  # Incorrect value, should be 2
    )
    
    # Configure mocks
    mock_db.query.return_value.filter.return_value.all.side_effect = [
        game_stats,  # For GameStats query
        []  # For BaseStat query (empty for first test)
    ]
    
    mock_db.query.return_value.filter.return_value.first.return_value = base_stat
    
    # Test game count validation
    issues = validation_service._check_game_counts(player, 2023)
    
    # Should detect the inconsistency
    assert len(issues) == 1
    assert "has 2 game logs but games stat is 1" in issues[0]
    
    # Verify _fix_games_count was called
    assert mock_db.flush.called

def test_missing_required_stats(validation_service, mock_db):
    """Test detection of missing required stats."""
    # Create a test player
    player = Player(
        player_id=str(uuid.uuid4()),
        name="Test Player",
        position="RB",
        team="TEST"
    )
    
    # Set up base stats with some missing
    base_stats = [
        BaseStat(stat_id=str(uuid.uuid4()), player_id=player.player_id, season=2023, stat_type="games", value=16.0),
        BaseStat(stat_id=str(uuid.uuid4()), player_id=player.player_id, season=2023, stat_type="rush_attempts", value=200.0),
        BaseStat(stat_id=str(uuid.uuid4()), player_id=player.player_id, season=2023, stat_type="rush_yards", value=950.0),
        # Missing: rush_td, targets, receptions, rec_yards, rec_td
    ]
    
    # Configure mocks
    mock_db.query.return_value.filter.return_value.all.return_value = base_stats
    
    # Test missing stats validation
    issues = validation_service._check_missing_stats(player, 2023)
    
    # Should detect missing stats
    assert len(issues) == 5
    assert any("missing required stat: rush_td" in issue for issue in issues)
    assert any("missing required stat: targets" in issue for issue in issues)
    assert any("missing required stat: receptions" in issue for issue in issues)
    assert any("missing required stat: rec_yards" in issue for issue in issues)
    assert any("missing required stat: rec_td" in issue for issue in issues)

def test_verify_season_totals(validation_service, mock_db):
    """Test verification of season totals against game logs."""
    # Create a test player
    player = Player(
        player_id=str(uuid.uuid4()),
        name="Test Player",
        position="QB",
        team="TEST"
    )
    
    # Mock game stats with QB stats
    game_stats = [
        GameStats(
            game_stat_id=str(uuid.uuid4()),
            player_id=player.player_id,
            season=2023,
            week=1,
            opponent="OPP",
            game_location="home",
            result="W",
            team_score=21,
            opponent_score=10,
            stats={
                "cmp": 20,
                "att": 30,
                "pass_yds": 250,
                "pass_td": 2,
                "int": 1,
                "rush_att": 5,
                "rush_yds": 25,
                "rush_td": 0
            }
        ),
        GameStats(
            game_stat_id=str(uuid.uuid4()),
            player_id=player.player_id,
            season=2023,
            week=2,
            opponent="OPP",
            game_location="away",
            result="L",
            team_score=14,
            opponent_score=21,
            stats={
                "cmp": 18,
                "att": 28,
                "pass_yds": 230,
                "pass_td": 1,
                "int": 2,
                "rush_att": 4,
                "rush_yds": 15,
                "rush_td": 1
            }
        )
    ]
    
    # Set up base stats with some inconsistent values
    base_stats = [
        BaseStat(stat_id=str(uuid.uuid4()), player_id=player.player_id, season=2023, stat_type="completions", value=38.0),  # Correct
        BaseStat(stat_id=str(uuid.uuid4()), player_id=player.player_id, season=2023, stat_type="pass_attempts", value=58.0),  # Correct
        BaseStat(stat_id=str(uuid.uuid4()), player_id=player.player_id, season=2023, stat_type="pass_yards", value=500.0),  # Incorrect (should be 480)
        BaseStat(stat_id=str(uuid.uuid4()), player_id=player.player_id, season=2023, stat_type="pass_td", value=3.0),  # Correct
        BaseStat(stat_id=str(uuid.uuid4()), player_id=player.player_id, season=2023, stat_type="interceptions", value=2.0),  # Incorrect (should be 3)
        # Missing rush stats
    ]
    
    # Configure mocks
    mock_db.query.return_value.filter.return_value.all.side_effect = [
        game_stats,  # For GameStats query
        base_stats   # For BaseStat query
    ]
    
    # Test season total verification
    issues = validation_service._verify_season_totals(player, 2023)
    
    # Should detect inconsistencies and missing stats
    assert len(issues) >= 5
    assert any("inconsistent pass_yards" in issue for issue in issues)
    assert any("inconsistent interceptions" in issue for issue in issues)
    assert any("missing rush_attempts" in issue for issue in issues)
    assert any("missing rush_yards" in issue for issue in issues)
    assert any("missing rush_td" in issue for issue in issues)
    
    # Verify fix methods were called
    assert mock_db.flush.call_count >= 5  # At least 5 fixes

def test_validate_player_data_integration(validation_service, mock_db):
    """Integration test for player data validation."""
    # Create a test player
    player = Player(
        player_id=str(uuid.uuid4()),
        name="Test Player",
        position="WR",
        team="TEST"
    )
    
    # Mock database queries for all validation methods
    with patch.object(validation_service, '_check_game_counts', return_value=["Issue 1"]):
        with patch.object(validation_service, '_verify_season_totals', return_value=["Issue 2", "Issue 3"]):
            with patch.object(validation_service, '_check_missing_stats', return_value=["Issue 4"]):
                
                # Run the validation
                issues = validation_service.validate_player_data(player, 2023)
                
                # Verify all validation methods were called and issues combined
                assert len(issues) == 4
                assert "Issue 1" in issues
                assert "Issue 2" in issues
                assert "Issue 3" in issues
                assert "Issue 4" in issues