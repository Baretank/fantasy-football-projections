import pytest
from sqlalchemy import and_
import uuid

from backend.services.data_validation import DataValidationService
from backend.database.models import Player, BaseStat, GameStats

class TestDataValidation:
    @pytest.fixture(scope="function")
    def validation_service(self, test_db):
        """Create DataValidationService instance for testing."""
        return DataValidationService(test_db)
    
    @pytest.fixture(scope="function")
    def test_player(self, test_db):
        """Create a test player with basic stats."""
        player_id = str(uuid.uuid4())
        player = Player(
            player_id=player_id,
            name="Test Player",
            team="TEST",
            position="QB"
        )
        test_db.add(player)
        test_db.commit()
        
        # Add some basic stats
        season = 2023
        stats = [
            BaseStat(player_id=player_id, season=season, stat_type="games", value=16.0),
            BaseStat(player_id=player_id, season=season, stat_type="completions", value=350.0),
            BaseStat(player_id=player_id, season=season, stat_type="pass_attempts", value=500.0),
            BaseStat(player_id=player_id, season=season, stat_type="pass_yards", value=4000.0),
            BaseStat(player_id=player_id, season=season, stat_type="pass_td", value=30.0),
            BaseStat(player_id=player_id, season=season, stat_type="interceptions", value=10.0),
            BaseStat(player_id=player_id, season=season, stat_type="rush_attempts", value=50.0),
            BaseStat(player_id=player_id, season=season, stat_type="rush_yards", value=200.0),
            BaseStat(player_id=player_id, season=season, stat_type="rush_td", value=2.0)
        ]
        
        for stat in stats:
            test_db.add(stat)
        test_db.commit()
        
        return {"player": player, "season": season}

    @pytest.fixture(scope="function")
    def test_game_logs(self, test_db, test_player):
        """Create test game logs for the player."""
        player = test_player["player"]
        season = test_player["season"]
        
        # Create 15 game logs (intentionally fewer than the games stat)
        games = []
        for week in range(1, 16):
            game = GameStats(
                game_stat_id=str(uuid.uuid4()),
                player_id=player.player_id,
                season=season,
                week=week,
                opponent="OPP",
                game_location="home",  # Required field
                result="W",            # Required field
                team_score=27,         # Required field
                opponent_score=17,     # Required field
                stats={
                    "cmp": "22",
                    "att": "33",
                    "pass_yds": "250",
                    "pass_td": "2",
                    "int": "0",
                    "rush_att": "3",
                    "rush_yds": "15",
                    "rush_td": "0",
                    "sacked": "1"
                }
            )
            test_db.add(game)
            games.append(game)
        
        test_db.commit()
        return games
    
    def test_check_game_counts(self, validation_service, test_player, test_game_logs):
        """Test validation of game counts against game logs."""
        player = test_player["player"]
        season = test_player["season"]
        
        # There's a discrepancy: 16 in BaseStat vs 15 game logs
        issues = validation_service._check_game_counts(player, season)
        
        # Should identify the issue
        assert len(issues) == 1
        assert "has 15 game logs but games stat is 16" in issues[0]
        
        # Should fix the game count stat
        games_stat = validation_service.db.query(BaseStat).filter(
            and_(
                BaseStat.player_id == player.player_id,
                BaseStat.season == season,
                BaseStat.stat_type == "games"
            )
        ).first()
        
        assert games_stat.value == 15.0

    def test_verify_season_totals(self, validation_service, test_player, test_game_logs):
        """Test validation of season totals against game logs."""
        player = test_player["player"]
        season = test_player["season"]
        
        # Intentionally update a stat to be inconsistent with game logs
        pass_yards_stat = validation_service.db.query(BaseStat).filter(
            and_(
                BaseStat.player_id == player.player_id,
                BaseStat.season == season,
                BaseStat.stat_type == "pass_yards"
            )
        ).first()
        pass_yards_stat.value = 3000.0  # Different from sum of game logs (15 * 250 = 3750)
        validation_service.db.commit()
        
        # Run validation
        issues = validation_service._verify_season_totals(player, season)
        
        # Should identify the inconsistency
        assert len(issues) >= 1
        assert any("inconsistent pass_yards" in issue for issue in issues)
        
        # Should fix the stat value
        fixed_stat = validation_service.db.query(BaseStat).filter(
            and_(
                BaseStat.player_id == player.player_id,
                BaseStat.season == season,
                BaseStat.stat_type == "pass_yards"
            )
        ).first()
        
        assert fixed_stat.value == 3750.0  # Should be fixed to match game logs

    def test_check_missing_stats(self, validation_service, test_player):
        """Test detection of missing required stats."""
        player = test_player["player"]
        season = test_player["season"]
        
        # Delete a required stat to simulate missing data
        sacks_stat = validation_service.db.query(BaseStat).filter(
            and_(
                BaseStat.player_id == player.player_id,
                BaseStat.season == season,
                BaseStat.stat_type == "interceptions"
            )
        ).first()
        validation_service.db.delete(sacks_stat)
        validation_service.db.commit()
        
        # Run validation
        issues = validation_service._check_missing_stats(player, season)
        
        # Should identify the missing stat
        assert len(issues) == 1
        assert "missing required stat: interceptions" in issues[0]

    def test_validate_player_data(self, validation_service, test_player, test_game_logs):
        """Test the full player data validation process."""
        player = test_player["player"]
        season = test_player["season"]
        
        # Create inconsistencies for testing
        # 1. Inconsistent game count
        games_stat = validation_service.db.query(BaseStat).filter(
            and_(
                BaseStat.player_id == player.player_id,
                BaseStat.season == season,
                BaseStat.stat_type == "games"
            )
        ).first()
        games_stat.value = 17.0  # Different from actual game logs
        
        # 2. Inconsistent passing yards
        pass_yards_stat = validation_service.db.query(BaseStat).filter(
            and_(
                BaseStat.player_id == player.player_id,
                BaseStat.season == season,
                BaseStat.stat_type == "pass_yards"
            )
        ).first()
        pass_yards_stat.value = 4200.0  # Different from sum of game logs
        
        validation_service.db.commit()
        
        # Run full validation
        issues = validation_service.validate_player_data(player, season)
        
        # Should identify all issues
        assert len(issues) >= 2
        assert any("game logs but games stat is" in issue for issue in issues)
        assert any("inconsistent pass_yards" in issue for issue in issues)
        
        # Should fix all issues
        games_stat = validation_service.db.query(BaseStat).filter(
            and_(
                BaseStat.player_id == player.player_id,
                BaseStat.season == season,
                BaseStat.stat_type == "games"
            )
        ).first()
        assert games_stat.value == 15.0
        
        pass_yards_stat = validation_service.db.query(BaseStat).filter(
            and_(
                BaseStat.player_id == player.player_id,
                BaseStat.season == season,
                BaseStat.stat_type == "pass_yards"
            )
        ).first()
        assert pass_yards_stat.value == 3750.0

    def test_add_missing_stat(self, validation_service, test_player):
        """Test adding a missing stat."""
        player = test_player["player"]
        season = test_player["season"]
        
        # Add a missing stat
        validation_service._add_missing_stat(player, season, "sacks", 25.0)
        
        # Verify it was added
        sacks_stat = validation_service.db.query(BaseStat).filter(
            and_(
                BaseStat.player_id == player.player_id,
                BaseStat.season == season,
                BaseStat.stat_type == "sacks"
            )
        ).first()
        
        assert sacks_stat is not None
        assert sacks_stat.value == 25.0

    def test_invalid_position(self, validation_service, test_db):
        """Test validation for player with invalid position."""
        player_id = str(uuid.uuid4())
        player = Player(
            player_id=player_id,
            name="Invalid Player",
            team="TEST",
            position="K"  # Not in required_stats
        )
        test_db.add(player)
        test_db.commit()
        
        issues = validation_service.validate_player_data(player, 2023)
        
        assert len(issues) == 1
        assert "invalid position: K" in issues[0]