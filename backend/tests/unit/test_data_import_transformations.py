import pytest
import pandas as pd
from sqlalchemy.orm import Session
from backend.services.data_import_service import DataImportService
from backend.database.models import Player, BaseStat
import uuid

class TestDataImportTransformations:
    @pytest.fixture(scope="function")
    def service(self, test_db):
        """Create DataImportService instance for testing."""
        return DataImportService(test_db)
    
    @pytest.fixture(scope="function")
    def mock_qb_data(self):
        """Mock QB game log data from external source."""
        data = {
            "Date": ["2023-09-10", "2023-09-17", "2023-09-24", "2023-10-01", "2023-10-08"],
            "Week": [1, 2, 3, 4, 5],
            "Tm": ["KC", "KC", "KC", "KC", "KC"],
            "Opp": ["JAX", "DET", "CHI", "NYJ", "MIN"],
            "Result": ["W 17-9", "W 31-17", "W 41-10", "W 23-20", "W 27-20"],
            "Cmp": [25, 29, 24, 30, 31],
            "Att": [37, 44, 33, 40, 45],
            "Cmp%": [67.6, 65.9, 72.7, 75.0, 68.9],
            "Yds": [305, 316, 272, 298, 348],
            "TD": [2, 2, 3, 1, 3],
            "Int": [1, 0, 0, 1, 0],
            "Rate": [94.2, 97.3, 123.8, 89.5, 108.7],
            "Sk": [1, 2, 1, 3, 2],
            "YdsL": [8, 15, 9, 23, 16],
            "Y/A": [8.2, 7.2, 8.2, 7.5, 7.7],
            "AY/A": [8.4, 7.8, 10.1, 6.9, 9.0],
            "Att.1": [6, 4, 3, 7, 5],
            "Yds.1": [45, 27, 17, 53, 38],
            "Y/A.1": [7.5, 6.8, 5.7, 7.6, 7.6],
            "TD.1": [0, 0, 1, 0, 0],
            "Snaps": [68, 72, 70, 75, 71],
            "Snap%": [100, 100, 98, 100, 100]
        }
        return pd.DataFrame(data)
    
    @pytest.fixture(scope="function")
    def mock_rb_data(self):
        """Mock RB game log data from external source."""
        data = {
            "Date": ["2023-09-10", "2023-09-17", "2023-09-24", "2023-10-01", "2023-10-08"],
            "Week": [1, 2, 3, 4, 5],
            "Tm": ["SF", "SF", "SF", "SF", "SF"],
            "Opp": ["PIT", "LAR", "NYG", "ARI", "DAL"],
            "Result": ["W 30-7", "W 27-20", "W 30-12", "L 17-18", "W 42-10"],
            "Att": [22, 20, 18, 16, 17],
            "Yds": [152, 116, 85, 106, 118],
            "Y/A": [6.9, 5.8, 4.7, 6.6, 6.9],
            "TD": [1, 1, 0, 1, 2],
            "Tgt": [7, 6, 8, 5, 4],
            "Rec": [5, 5, 7, 3, 3],
            "Yds.1": [17, 21, 34, 18, 15],
            "Y/R": [3.4, 4.2, 4.9, 6.0, 5.0],
            "TD.1": [0, 0, 1, 0, 0],
            "Snaps": [45, 47, 46, 44, 42],
            "Snap%": [65, 67, 64, 62, 60]
        }
        return pd.DataFrame(data)
    
    @pytest.fixture(scope="function")
    def mock_wr_data(self):
        """Mock WR game log data from external source."""
        data = {
            "Date": ["2023-09-10", "2023-09-17", "2023-09-24", "2023-10-01", "2023-10-08"],
            "Week": [1, 2, 3, 4, 5],
            "Tm": ["KC", "KC", "KC", "KC", "KC"],
            "Opp": ["JAX", "DET", "CHI", "NYJ", "MIN"],
            "Result": ["W 17-9", "W 31-17", "W 41-10", "W 23-20", "W 27-20"],
            "Tgt": [9, 10, 8, 12, 11],
            "Rec": [7, 8, 6, 9, 8],
            "Yds": [95, 103, 69, 124, 112],
            "Y/R": [13.6, 12.9, 11.5, 13.8, 14.0],
            "TD": [1, 1, 0, 1, 2],
            "Att": [0, 1, 0, 0, 0],
            "Yds.1": [0, 8, 0, 0, 0],
            "Y/A": [0, 8.0, 0, 0, 0],
            "TD.1": [0, 0, 0, 0, 0],
            "Snaps": [55, 59, 50, 62, 58],
            "Snap%": [80, 82, 70, 83, 82]
        }
        return pd.DataFrame(data)
    
    @pytest.fixture(scope="function")
    def sample_player(self, test_db):
        """Create a sample player for testing."""
        player = Player(
            player_id=str(uuid.uuid4()),
            name="Test Player",
            team="KC",
            position="QB"
        )
        test_db.add(player)
        test_db.commit()
        return player
    
    def test_transform_qb_data(self, service, mock_qb_data, sample_player):
        """Test transformation of QB data from external format to internal model."""
        # Test the transformation of game log data
        game_stats = service._transform_qb_game_data(mock_qb_data, sample_player.player_id, 2023)
        
        assert len(game_stats) == 5  # 5 games in our mock data
        
        # Verify the first game's stats
        first_game = game_stats[0]
        assert first_game.player_id == sample_player.player_id
        assert first_game.season == 2023
        assert first_game.week == 1
        assert first_game.opponent == "JAX"
        
        # Check specific QB stats
        assert first_game.pass_attempts == 37
        assert first_game.completions == 25
        assert first_game.pass_yards == 305
        assert first_game.pass_td == 2
        assert first_game.interceptions == 1
        
        # Check rushing stats
        assert first_game.carries == 6
        assert first_game.rush_yards == 45
        assert first_game.rush_td == 0
        
        # Test calculation of season totals
        season_totals = service._calculate_season_totals(game_stats)
        
        assert season_totals.games == 5
        assert season_totals.pass_attempts == sum([g.pass_attempts for g in game_stats])
        assert season_totals.completions == sum([g.completions for g in game_stats])
        assert season_totals.pass_yards == sum([g.pass_yards for g in game_stats])
        assert season_totals.pass_td == sum([g.pass_td for g in game_stats])
        assert season_totals.interceptions == sum([g.interceptions for g in game_stats])
        assert season_totals.carries == sum([g.carries for g in game_stats])
        assert season_totals.rush_yards == sum([g.rush_yards for g in game_stats])
        assert season_totals.rush_td == sum([g.rush_td for g in game_stats])
    
    def test_transform_rb_data(self, service, mock_rb_data, sample_player):
        """Test transformation of RB data from external format to internal model."""
        # Update sample player to be an RB
        service.db.query(Player).filter(
            Player.player_id == sample_player.player_id
        ).update({"position": "RB", "team": "SF"})
        service.db.commit()
        
        # Test the transformation of game log data
        game_stats = service._transform_rb_game_data(mock_rb_data, sample_player.player_id, 2023)
        
        assert len(game_stats) == 5  # 5 games in our mock data
        
        # Verify the first game's stats
        first_game = game_stats[0]
        assert first_game.player_id == sample_player.player_id
        assert first_game.season == 2023
        assert first_game.week == 1
        assert first_game.opponent == "PIT"
        
        # Check specific RB stats
        assert first_game.carries == 22
        assert first_game.rush_yards == 152
        assert first_game.rush_td == 1
        
        # Check receiving stats
        assert first_game.targets == 7
        assert first_game.receptions == 5
        assert first_game.rec_yards == 17
        assert first_game.rec_td == 0
        
        # Test calculation of season totals
        season_totals = service._calculate_season_totals(game_stats)
        
        assert season_totals.games == 5
        assert season_totals.carries == sum([g.carries for g in game_stats])
        assert season_totals.rush_yards == sum([g.rush_yards for g in game_stats])
        assert season_totals.rush_td == sum([g.rush_td for g in game_stats])
        assert season_totals.targets == sum([g.targets for g in game_stats])
        assert season_totals.receptions == sum([g.receptions for g in game_stats])
        assert season_totals.rec_yards == sum([g.rec_yards for g in game_stats])
        assert season_totals.rec_td == sum([g.rec_td for g in game_stats])
    
    def test_transform_wr_data(self, service, mock_wr_data, sample_player):
        """Test transformation of WR data from external format to internal model."""
        # Update sample player to be a WR
        service.db.query(Player).filter(
            Player.player_id == sample_player.player_id
        ).update({"position": "WR", "team": "KC"})
        service.db.commit()
        
        # Test the transformation of game log data
        game_stats = service._transform_wr_game_data(mock_wr_data, sample_player.player_id, 2023)
        
        assert len(game_stats) == 5  # 5 games in our mock data
        
        # Verify the first game's stats
        first_game = game_stats[0]
        assert first_game.player_id == sample_player.player_id
        assert first_game.season == 2023
        assert first_game.week == 1
        assert first_game.opponent == "JAX"
        
        # Check specific WR stats
        assert first_game.targets == 9
        assert first_game.receptions == 7
        assert first_game.rec_yards == 95
        assert first_game.rec_td == 1
        
        # Check rushing stats (if any)
        assert first_game.carries == 0
        assert first_game.rush_yards == 0
        assert first_game.rush_td == 0
        
        # Test calculation of season totals
        season_totals = service._calculate_season_totals(game_stats)
        
        assert season_totals.games == 5
        assert season_totals.targets == sum([g.targets for g in game_stats])
        assert season_totals.receptions == sum([g.receptions for g in game_stats])
        assert season_totals.rec_yards == sum([g.rec_yards for g in game_stats])
        assert season_totals.rec_td == sum([g.rec_td for g in game_stats])
        
        # Should have 1 carry from game 2
        assert season_totals.carries == 1
        assert season_totals.rush_yards == 8
        assert season_totals.rush_td == 0
    
    def test_derived_metrics_calculation(self, service, mock_qb_data, sample_player):
        """Test calculation of derived metrics from raw stats."""
        # Transform game data first
        game_stats = service._transform_qb_game_data(mock_qb_data, sample_player.player_id, 2023)
        season_totals = service._calculate_season_totals(game_stats)
        
        # Calculate derived metrics
        derived_metrics = service._calculate_derived_metrics(season_totals)
        
        # Check derived efficiency metrics
        assert derived_metrics.comp_pct == pytest.approx(
            season_totals.completions / season_totals.pass_attempts, rel=0.01
        )
        
        assert derived_metrics.yards_per_att == pytest.approx(
            season_totals.pass_yards / season_totals.pass_attempts, rel=0.01
        )
        
        assert derived_metrics.pass_td_rate == pytest.approx(
            season_totals.pass_td / season_totals.pass_attempts, rel=0.01
        )
        
        assert derived_metrics.int_rate == pytest.approx(
            season_totals.interceptions / season_totals.pass_attempts, rel=0.01
        )
        
        assert derived_metrics.yards_per_carry == pytest.approx(
            season_totals.rush_yards / season_totals.carries, rel=0.01
        )
    
    def test_stat_mapping_consistency(self, service, mock_qb_data, mock_rb_data, mock_wr_data, sample_player):
        """Test the consistency of stat mapping across different positions."""
        # QB transformation
        qb_games = service._transform_qb_game_data(mock_qb_data, sample_player.player_id, 2023)
        qb_season = service._calculate_season_totals(qb_games)
        
        # Update player to be RB
        service.db.query(Player).filter(
            Player.player_id == sample_player.player_id
        ).update({"position": "RB", "team": "SF"})
        service.db.commit()
        
        # RB transformation
        rb_games = service._transform_rb_game_data(mock_rb_data, sample_player.player_id, 2023)
        rb_season = service._calculate_season_totals(rb_games)
        
        # Update player to be WR
        service.db.query(Player).filter(
            Player.player_id == sample_player.player_id
        ).update({"position": "WR", "team": "KC"})
        service.db.commit()
        
        # WR transformation
        wr_games = service._transform_wr_game_data(mock_wr_data, sample_player.player_id, 2023)
        wr_season = service._calculate_season_totals(wr_games)
        
        # Verify common stats are mapped consistently
        # All players should have rush_yards, but QBs usually less
        assert qb_season.rush_yards == sum([g.rush_yards for g in qb_games])
        assert rb_season.rush_yards == sum([g.rush_yards for g in rb_games])
        assert wr_season.rush_yards == sum([g.rush_yards for g in wr_games])
        
        # All players should have games count
        assert qb_season.games == 5
        assert rb_season.games == 5
        assert wr_season.games == 5
        
        # RBs and WRs should have receiving stats
        assert rb_season.targets == sum([g.targets for g in rb_games])
        assert wr_season.targets == sum([g.targets for g in wr_games])
        
        # QBs should have passing stats
        assert qb_season.pass_attempts == sum([g.pass_attempts for g in qb_games])
        assert qb_season.pass_yards == sum([g.pass_yards for g in qb_games])
    
    def test_handling_missing_data(self, service, mock_qb_data, sample_player):
        """Test handling of missing data in import transformations."""
        # Create a copy with some missing data
        missing_data = mock_qb_data.copy()
        missing_data.loc[2, "Cmp"] = None  # Missing completions in game 3
        missing_data.loc[3, "TD"] = None   # Missing TDs in game 4
        
        # Test the transformation with missing data
        game_stats = service._transform_qb_game_data(missing_data, sample_player.player_id, 2023)
        
        # Check that missing data is handled properly (should default to 0)
        assert game_stats[2].completions == 0  # Game 3
        assert game_stats[3].pass_td == 0      # Game 4
        
        # Calculate season totals
        season_totals = service._calculate_season_totals(game_stats)
        
        # Verify totals still calculated correctly
        assert season_totals.completions == sum([g.completions for g in game_stats])
        assert season_totals.pass_td == sum([g.pass_td for g in game_stats])
    
    def test_handling_percentage_fields(self, service, mock_qb_data, sample_player):
        """Test handling of percentage fields in import transformations."""
        # Test the transformation of percentage fields
        game_stats = service._transform_qb_game_data(mock_qb_data, sample_player.player_id, 2023)
        
        # Completion percentage should be transformed from string to float
        assert game_stats[0].comp_pct == pytest.approx(67.6 / 100, rel=0.01)
        assert game_stats[1].comp_pct == pytest.approx(65.9 / 100, rel=0.01)
        
        # Calculate season totals
        season_totals = service._calculate_season_totals(game_stats)
        
        # Verify percentage is calculated as aggregate
        expected_comp_pct = sum([g.completions for g in game_stats]) / sum([g.pass_attempts for g in game_stats])
        assert season_totals.comp_pct == pytest.approx(expected_comp_pct, rel=0.01)