import pytest
from sqlalchemy import and_
import uuid
from unittest.mock import MagicMock, patch

from backend.services.data_validation import DataValidationService, ValidationResultDict
from backend.database.models import Player, BaseStat, GameStats, Projection, TeamStat


class TestDataValidation:
    @pytest.fixture(scope="function")
    def validation_service(self, test_db):
        """Create DataValidationService instance for testing."""
        return DataValidationService(test_db)

    @pytest.fixture(scope="function")
    def test_player(self, test_db):
        """Create a test player with basic stats."""
        player_id = str(uuid.uuid4())
        player = Player(player_id=player_id, name="Test Player", team="TEST", position="QB")
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
            BaseStat(player_id=player_id, season=season, stat_type="rush_td", value=2.0),
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
                result="W",  # Required field
                team_score=27,  # Required field
                opponent_score=17,  # Required field
                stats={
                    "cmp": "22",
                    "att": "33",
                    "pass_yds": "250",
                    "pass_td": "2",
                    "int": "0",
                    "rush_att": "3",
                    "rush_yds": "15",
                    "rush_td": "0",
                    "sacked": "1",
                },
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
        games_stat = (
            validation_service.db.query(BaseStat)
            .filter(
                and_(
                    BaseStat.player_id == player.player_id,
                    BaseStat.season == season,
                    BaseStat.stat_type == "games",
                )
            )
            .first()
        )

        assert games_stat.value == 15.0

    def test_verify_season_totals(self, validation_service, test_player, test_game_logs):
        """Test validation of season totals against game logs."""
        player = test_player["player"]
        season = test_player["season"]

        # Intentionally update a stat to be inconsistent with game logs
        pass_yards_stat = (
            validation_service.db.query(BaseStat)
            .filter(
                and_(
                    BaseStat.player_id == player.player_id,
                    BaseStat.season == season,
                    BaseStat.stat_type == "pass_yards",
                )
            )
            .first()
        )
        pass_yards_stat.value = 3000.0  # Different from sum of game logs (15 * 250 = 3750)
        validation_service.db.commit()

        # Run validation
        issues = validation_service._verify_season_totals(player, season)

        # Should identify the inconsistency
        assert len(issues) >= 1
        assert any("inconsistent pass_yards" in issue for issue in issues)

        # Should fix the stat value
        fixed_stat = (
            validation_service.db.query(BaseStat)
            .filter(
                and_(
                    BaseStat.player_id == player.player_id,
                    BaseStat.season == season,
                    BaseStat.stat_type == "pass_yards",
                )
            )
            .first()
        )

        assert fixed_stat.value == 3750.0  # Should be fixed to match game logs

    def test_check_missing_stats(self, validation_service, test_player):
        """Test detection of missing required stats."""
        player = test_player["player"]
        season = test_player["season"]

        # Delete a required stat to simulate missing data
        sacks_stat = (
            validation_service.db.query(BaseStat)
            .filter(
                and_(
                    BaseStat.player_id == player.player_id,
                    BaseStat.season == season,
                    BaseStat.stat_type == "interceptions",
                )
            )
            .first()
        )
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
        games_stat = (
            validation_service.db.query(BaseStat)
            .filter(
                and_(
                    BaseStat.player_id == player.player_id,
                    BaseStat.season == season,
                    BaseStat.stat_type == "games",
                )
            )
            .first()
        )
        games_stat.value = 17.0  # Different from actual game logs

        # 2. Inconsistent passing yards
        pass_yards_stat = (
            validation_service.db.query(BaseStat)
            .filter(
                and_(
                    BaseStat.player_id == player.player_id,
                    BaseStat.season == season,
                    BaseStat.stat_type == "pass_yards",
                )
            )
            .first()
        )
        pass_yards_stat.value = 4200.0  # Different from sum of game logs

        validation_service.db.commit()

        # Run full validation
        issues = validation_service.validate_player_data(player, season)

        # Should identify all issues
        assert len(issues) >= 2
        assert any("game logs but games stat is" in issue for issue in issues)
        assert any("inconsistent pass_yards" in issue for issue in issues)

        # Should fix all issues
        games_stat = (
            validation_service.db.query(BaseStat)
            .filter(
                and_(
                    BaseStat.player_id == player.player_id,
                    BaseStat.season == season,
                    BaseStat.stat_type == "games",
                )
            )
            .first()
        )
        assert games_stat.value == 15.0

        pass_yards_stat = (
            validation_service.db.query(BaseStat)
            .filter(
                and_(
                    BaseStat.player_id == player.player_id,
                    BaseStat.season == season,
                    BaseStat.stat_type == "pass_yards",
                )
            )
            .first()
        )
        assert pass_yards_stat.value == 3750.0

    def test_add_missing_stat(self, validation_service, test_player):
        """Test adding a missing stat."""
        player = test_player["player"]
        season = test_player["season"]

        # Add a missing stat
        validation_service._add_missing_stat(player, season, "sacks", 25.0)

        # Verify it was added
        sacks_stat = (
            validation_service.db.query(BaseStat)
            .filter(
                and_(
                    BaseStat.player_id == player.player_id,
                    BaseStat.season == season,
                    BaseStat.stat_type == "sacks",
                )
            )
            .first()
        )

        assert sacks_stat is not None
        assert sacks_stat.value == 25.0

    def test_invalid_position(self, validation_service, test_db):
        """Test validation for player with invalid position."""
        player_id = str(uuid.uuid4())
        player = Player(
            player_id=player_id,
            name="Invalid Player",
            team="TEST",
            position="K",  # Not in required_stats
        )
        test_db.add(player)
        test_db.commit()

        issues = validation_service.validate_player_data(player, 2023)

        assert len(issues) == 1
        assert "invalid position: K" in issues[0]
        
    @pytest.fixture(scope="function")
    def mock_projection(self):
        """Create a sample projection for testing mathematical consistency."""
        # Create a mock projection that won't be saved to the database
        projection = MagicMock(spec=Projection)
        
        # Set up all the attributes we need for testing
        projection.projection_id = str(uuid.uuid4())
        projection.player_id = str(uuid.uuid4())
        projection.season = 2025
        projection.games = 17
        
        # QB stats
        projection.pass_attempts = 500
        projection.completions = 325
        projection.pass_yards = 4000
        projection.pass_td = 30
        projection.interceptions = 10
        
        # Rushing stats
        projection.rush_attempts = 40
        projection.rush_yards = 200
        projection.rush_td = 2
        
        # Efficiency metrics (using attribute names that match our validation code)
        projection.comp_pct = 65.0  # Correct: 325/500*100 = 65.0
        projection.yards_per_att = 8.0  # Correct: 4000/500 = 8.0
        projection.yards_per_completion = 12.31  # Correct: 4000/325 ≈ 12.31
        projection.pass_td_rate = 6.0  # Correct: 30/500*100 = 6.0
        projection.int_rate = 2.0  # Correct: 10/500*100 = 2.0
        projection.rush_yards_per_att = 5.0  # Correct: 200/40 = 5.0
        
        # Additional stats
        projection.fumbles_lost = 0  # No fumbles
        projection.targets = 5  # Some targets for receiving
        projection.receptions = 3  # Some receptions
        projection.rec_yards = 40  # Some receiving yards
        projection.rec_td = 0  # No receiving TDs
        
        # Fantasy points
        projection.ppr = 262.0  # Correctly calculated
        projection.half_ppr = 262.0  # Correctly calculated
        projection.standard = 262.0  # Correctly calculated
        
        return projection
        
    @pytest.mark.asyncio
    async def test_validate_qb_math(self, validation_service, mock_projection):
        """Test QB mathematical validation when values are correct."""
        # Test the helper method directly
        issues = validation_service._validate_qb_math(mock_projection)
        
        # Should have no issues since the values are consistent
        assert len(issues) == 0
        
    @pytest.mark.asyncio
    async def test_validate_qb_math_with_errors(self, validation_service, mock_projection):
        """Test QB mathematical validation when values are incorrect."""
        # Introduce inconsistencies
        mock_projection.comp_pct = 70.0  # Should be 65.0
        mock_projection.yards_per_att = 7.0      # Should be 8.0
        
        # Test the helper method directly
        issues = validation_service._validate_qb_math(mock_projection)
        
        # Should have 2 issues
        assert len(issues) == 2
        assert "Completion percentage mismatch" in issues[0]
        assert "Yards per attempt mismatch" in issues[1]
        
    @pytest.mark.asyncio
    async def test_validate_fantasy_points(self, validation_service, mock_projection):
        """Test validation of fantasy point calculations."""
        # Set fantasy points to incorrect values
        mock_projection.ppr = 300.0       # Should be 262.0
        mock_projection.half_ppr = 280.0  # Should be 262.0
        mock_projection.standard = 240.0  # Should be 262.0
        
        # Test the helper method directly
        issues = validation_service._validate_fantasy_points(mock_projection)
        
        # Should have 3 issues
        assert len(issues) == 3
        assert "PPR points mismatch" in issues[0]
        assert "Half PPR points mismatch" in issues[1]
        assert "Standard points mismatch" in issues[2]
        
    @pytest.mark.asyncio
    async def test_validate_team_consistency(self, validation_service, test_db):
        """Test validation of team-level statistical consistency."""
        # Create team stats
        team = "KC"
        season = 2025
        team_stat = TeamStat(
            team=team,
            season=season,
            plays=1000,
            pass_attempts=600,
            completions=390,
            pass_yards=4500,
            pass_td=35,
            interceptions=12,
            rush_attempts=400,
            rush_yards=1800,
            rush_td=18,
            targets=600,
            receptions=390,
            rec_yards=4500,
            rec_td=35,
            pass_percentage=60.0,
            pass_td_rate=5.83,
            rush_yards_per_carry=4.5,
        )
        test_db.add(team_stat)
        
        # Create two KC players with stats that add up to team totals
        player1_id = str(uuid.uuid4())
        player1 = Player(player_id=player1_id, name="QB One", team=team, position="QB")
        test_db.add(player1)
        
        player2_id = str(uuid.uuid4())
        player2 = Player(player_id=player2_id, name="RB One", team=team, position="RB")
        test_db.add(player2)
        
        # Add stats that match team totals
        stats1 = [
            BaseStat(player_id=player1_id, season=season, stat_type="pass_attempts", value=600.0),
            BaseStat(player_id=player1_id, season=season, stat_type="completions", value=390.0),
            BaseStat(player_id=player1_id, season=season, stat_type="pass_yards", value=4500.0),
            BaseStat(player_id=player1_id, season=season, stat_type="pass_td", value=35.0),
            BaseStat(player_id=player1_id, season=season, stat_type="interceptions", value=12.0),
            BaseStat(player_id=player1_id, season=season, stat_type="rush_attempts", value=50.0),
            BaseStat(player_id=player1_id, season=season, stat_type="rush_yards", value=200.0),
            BaseStat(player_id=player1_id, season=season, stat_type="rush_td", value=3.0),
        ]
        
        stats2 = [
            BaseStat(player_id=player2_id, season=season, stat_type="rush_attempts", value=350.0),
            BaseStat(player_id=player2_id, season=season, stat_type="rush_yards", value=1600.0),
            BaseStat(player_id=player2_id, season=season, stat_type="rush_td", value=15.0),
            BaseStat(player_id=player2_id, season=season, stat_type="targets", value=80.0),
            BaseStat(player_id=player2_id, season=season, stat_type="receptions", value=60.0),
            BaseStat(player_id=player2_id, season=season, stat_type="rec_yards", value=500.0),
            BaseStat(player_id=player2_id, season=season, stat_type="rec_td", value=3.0),
        ]
        
        for stat in stats1 + stats2:
            test_db.add(stat)
        
        test_db.commit()
        
        # Run the team consistency validation
        issues = validation_service.validate_team_consistency(team, season)
        
        # There should be at least one issue (RB receptions and yards don't match team totals)
        assert len(issues) > 0
        assert any("rec_yards mismatch" in issue for issue in issues)
        assert any("rec_td mismatch" in issue for issue in issues)
