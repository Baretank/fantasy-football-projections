import pytest
import pandas as pd
import uuid
from unittest.mock import patch, MagicMock
from backend.services.data_import_service import DataImportService
from backend.database.models import Player, BaseStat

class TestPositionImportAccuracy:
    @pytest.fixture(scope="function")
    def service(self, test_db):
        """Create DataImportService instance for testing."""
        return DataImportService(test_db)
    
    @pytest.fixture(scope="function")
    def sample_qb(self, test_db):
        """Create a sample QB for testing."""
        player = Player(
            player_id=str(uuid.uuid4()),
            name="Test QB",
            team="KC",
            position="QB"
        )
        test_db.add(player)
        test_db.commit()
        return player
    
    @pytest.fixture(scope="function")
    def sample_rb(self, test_db):
        """Create a sample RB for testing."""
        player = Player(
            player_id=str(uuid.uuid4()),
            name="Test RB",
            team="SF",
            position="RB"
        )
        test_db.add(player)
        test_db.commit()
        return player
    
    @pytest.fixture(scope="function")
    def sample_wr(self, test_db):
        """Create a sample WR for testing."""
        player = Player(
            player_id=str(uuid.uuid4()),
            name="Test WR",
            team="MIN",
            position="WR"
        )
        test_db.add(player)
        test_db.commit()
        return player
    
    @pytest.fixture(scope="function")
    def sample_te(self, test_db):
        """Create a sample TE for testing."""
        player = Player(
            player_id=str(uuid.uuid4()),
            name="Test TE",
            team="KC",
            position="TE"
        )
        test_db.add(player)
        test_db.commit()
        return player
    
    def _create_mock_qb_game_log(self):
        """Create mock QB game log data."""
        return pd.DataFrame({
            "Date": ["2023-09-10", "2023-09-17", "2023-09-24"],
            "Week": [1, 2, 3],
            "Tm": ["KC", "KC", "KC"],
            "Opp": ["JAX", "DET", "CHI"],
            "Result": ["W 17-9", "W 31-17", "W 41-10"],
            "Cmp": [25, 29, 24],
            "Att": [37, 44, 33],
            "Cmp%": [67.6, 65.9, 72.7],
            "Yds": [305, 316, 272],
            "TD": [2, 2, 3],
            "Int": [1, 0, 0],
            "Rate": [94.2, 97.3, 123.8],
            "Sk": [1, 2, 1],
            "YdsL": [8, 15, 9],
            "Y/A": [8.2, 7.2, 8.2],
            "AY/A": [8.4, 7.8, 10.1],
            "Att.1": [6, 4, 3],
            "Yds.1": [45, 27, 17],
            "Y/A.1": [7.5, 6.8, 5.7],
            "TD.1": [0, 0, 1],
        })
    
    def _create_mock_qb_season_totals(self):
        """Create mock QB season totals data."""
        return pd.DataFrame({
            "Rk": [1],
            "Player": ["Test QB"],
            "Tm": ["KC"],
            "Age": [28],
            "Pos": ["QB"],
            "G": [17],
            "GS": [17],
            "Cmp": [401],
            "Att": [599],
            "Cmp%": [67.0],
            "Yds": [4472],
            "TD": [27],
            "Int": [14],
            "Y/A": [7.5],
            "AY/A": [7.2],
            "Rate": [94.2],
            "Sk": [31],
            "YdsL": [224],
            "NY/A": [6.77],
            "ANY/A": [6.50],
            "Att.1": [73],
            "Yds.1": [389],
            "Y/A.1": [5.3],
            "TD.1": [4],
        })
    
    def _create_mock_rb_game_log(self):
        """Create mock RB game log data."""
        return pd.DataFrame({
            "Date": ["2023-09-10", "2023-09-17", "2023-09-24"],
            "Week": [1, 2, 3],
            "Tm": ["SF", "SF", "SF"],
            "Opp": ["PIT", "LAR", "NYG"],
            "Result": ["W 30-7", "W 27-20", "W 30-12"],
            "Att": [22, 20, 18],
            "Yds": [152, 116, 85],
            "Y/A": [6.9, 5.8, 4.7],
            "TD": [1, 1, 0],
            "Tgt": [7, 6, 8],
            "Rec": [5, 5, 7],
            "Yds.1": [17, 21, 34],
            "Y/R": [3.4, 4.2, 4.9],
            "TD.1": [0, 0, 1],
        })
    
    def _create_mock_rb_season_totals(self):
        """Create mock RB season totals data."""
        return pd.DataFrame({
            "Rk": [1],
            "Player": ["Test RB"],
            "Tm": ["SF"],
            "Age": [27],
            "Pos": ["RB"],
            "G": [16],
            "GS": [16],
            "Att": [272],
            "Yds": [1459],
            "Y/A": [5.4],
            "TD": [14],
            "Tgt": [83],
            "Rec": [67],
            "Yds.1": [564],
            "Y/R": [8.4],
            "TD.1": [7],
            "Ctch%": [80.7],
            "Y/Tgt": [6.8],
        })
    
    def _create_mock_wr_game_log(self):
        """Create mock WR game log data."""
        return pd.DataFrame({
            "Date": ["2023-09-10", "2023-09-17", "2023-09-24"],
            "Week": [1, 2, 3],
            "Tm": ["MIN", "MIN", "MIN"],
            "Opp": ["TB", "PHI", "LAC"],
            "Result": ["L 17-20", "W 28-13", "W 28-24"],
            "Tgt": [8, 9, 12],
            "Rec": [5, 6, 10],
            "Yds": [82, 93, 133],
            "Y/R": [16.4, 15.5, 13.3],
            "TD": [0, 1, 1],
            "Att": [1, 0, 0],
            "Yds.1": [5, 0, 0],
            "Y/A": [5.0, None, None],
            "TD.1": [0, 0, 0],
        })
    
    def _create_mock_wr_season_totals(self):
        """Create mock WR season totals data."""
        return pd.DataFrame({
            "Rk": [1],
            "Player": ["Test WR"],
            "Tm": ["MIN"],
            "Age": [24],
            "Pos": ["WR"],
            "G": [17],
            "GS": [17],
            "Tgt": [184],
            "Rec": [128],
            "Yds": [1698],
            "Y/R": [13.3],
            "TD": [8],
            "Att": [2],
            "Yds.1": [17],
            "Y/A": [8.5],
            "TD.1": [0],
            "Ctch%": [69.6],
            "Y/Tgt": [9.2],
        })
    
    def _create_mock_te_game_log(self):
        """Create mock TE game log data."""
        return pd.DataFrame({
            "Date": ["2023-09-10", "2023-09-17", "2023-09-24"],
            "Week": [1, 2, 3],
            "Tm": ["KC", "KC", "KC"],
            "Opp": ["JAX", "DET", "CHI"],
            "Result": ["W 17-9", "W 31-17", "W 41-10"],
            "Tgt": [5, 8, 7],
            "Rec": [4, 7, 6],
            "Yds": [46, 69, 51],
            "Y/R": [11.5, 9.9, 8.5],
            "TD": [0, 1, 1],
            "Att": [0, 0, 0],
            "Yds.1": [0, 0, 0],
            "Y/A": [None, None, None],
            "TD.1": [0, 0, 0],
        })
    
    def _create_mock_te_season_totals(self):
        """Create mock TE season totals data."""
        return pd.DataFrame({
            "Rk": [1],
            "Player": ["Test TE"],
            "Tm": ["KC"],
            "Age": [34],
            "Pos": ["TE"],
            "G": [15],
            "GS": [15],
            "Tgt": [121],
            "Rec": [93],
            "Yds": [984],
            "Y/R": [10.6],
            "TD": [5],
            "Att": [0],
            "Yds.1": [0],
            "Y/A": [None],
            "TD.1": [0],
            "Ctch%": [76.9],
            "Y/Tgt": [8.1],
        })
    
    @pytest.mark.asyncio
    @patch.object(DataImportService, '_fetch_game_log_data')
    @patch.object(DataImportService, '_fetch_season_totals')
    async def test_qb_stats_import_accuracy(self, mock_season_totals, mock_game_log, service, sample_qb):
        """Test accuracy of QB stats import."""
        # Set up mocks
        mock_game_log.return_value = self._create_mock_qb_game_log()
        mock_season_totals.return_value = self._create_mock_qb_season_totals()
        
        # Run the import
        success = await service._import_player_data(sample_qb.player_id, 2023)
        
        # Verify import succeeded
        assert success is True
        
        # Get the imported base stats
        stats = service.db.query(BaseStat).filter(
            BaseStat.player_id == sample_qb.player_id,
            BaseStat.season == 2023,
            BaseStat.week.is_(None)  # Get season totals
        ).first()
        
        # Verify accuracy of key QB metrics
        assert stats is not None
        assert stats.games == 17
        assert stats.pass_attempts == 599
        assert stats.completions == 401
        assert stats.comp_pct == pytest.approx(401 / 599, rel=0.01)  # ~67%
        assert stats.pass_yards == 4472
        assert stats.pass_td == 27
        assert stats.interceptions == 14
        assert stats.yards_per_att == pytest.approx(4472 / 599, rel=0.01)
        
        # Verify rushing stats
        assert stats.carries == 73
        assert stats.rush_yards == 389
        assert stats.rush_td == 4
        assert stats.yards_per_carry == pytest.approx(389 / 73, rel=0.01)
        
        # Verify game-level stats
        game_stats = service.db.query(BaseStat).filter(
            BaseStat.player_id == sample_qb.player_id,
            BaseStat.season == 2023,
            BaseStat.week.is_not(None)
        ).order_by(BaseStat.week).all()
        
        assert len(game_stats) == 3  # Three games in our mock data
        
        # Check first game
        game1 = game_stats[0]
        assert game1.week == 1
        assert game1.opponent == "JAX"
        assert game1.pass_attempts == 37
        assert game1.completions == 25
        assert game1.pass_yards == 305
        assert game1.pass_td == 2
        assert game1.interceptions == 1
    
    @pytest.mark.asyncio
    @patch.object(DataImportService, '_fetch_game_log_data')
    @patch.object(DataImportService, '_fetch_season_totals')
    async def test_rb_stats_import_accuracy(self, mock_season_totals, mock_game_log, service, sample_rb):
        """Test accuracy of RB stats import."""
        # Set up mocks
        mock_game_log.return_value = self._create_mock_rb_game_log()
        mock_season_totals.return_value = self._create_mock_rb_season_totals()
        
        # Run the import
        success = await service._import_player_data(sample_rb.player_id, 2023)
        
        # Verify import succeeded
        assert success is True
        
        # Get the imported base stats
        stats = service.db.query(BaseStat).filter(
            BaseStat.player_id == sample_rb.player_id,
            BaseStat.season == 2023,
            BaseStat.week.is_(None)  # Get season totals
        ).first()
        
        # Verify accuracy of key RB metrics
        assert stats is not None
        assert stats.games == 16
        assert stats.carries == 272
        assert stats.rush_yards == 1459
        assert stats.rush_td == 14
        assert stats.yards_per_carry == pytest.approx(1459 / 272, rel=0.01)
        
        # Verify receiving stats
        assert stats.targets == 83
        assert stats.receptions == 67
        assert stats.rec_yards == 564
        assert stats.rec_td == 7
        assert stats.catch_pct == pytest.approx(67 / 83, rel=0.01)  # ~80.7%
        assert stats.yards_per_target == pytest.approx(564 / 83, rel=0.01)
        
        # Verify game-level stats
        game_stats = service.db.query(BaseStat).filter(
            BaseStat.player_id == sample_rb.player_id,
            BaseStat.season == 2023,
            BaseStat.week.is_not(None)
        ).order_by(BaseStat.week).all()
        
        assert len(game_stats) == 3  # Three games in our mock data
        
        # Check first game
        game1 = game_stats[0]
        assert game1.week == 1
        assert game1.opponent == "PIT"
        assert game1.carries == 22
        assert game1.rush_yards == 152
        assert game1.rush_td == 1
        assert game1.targets == 7
        assert game1.receptions == 5
        assert game1.rec_yards == 17
        assert game1.rec_td == 0
    
    @pytest.mark.asyncio
    @patch.object(DataImportService, '_fetch_game_log_data')
    @patch.object(DataImportService, '_fetch_season_totals')
    async def test_wr_stats_import_accuracy(self, mock_season_totals, mock_game_log, service, sample_wr):
        """Test accuracy of WR stats import."""
        # Set up mocks
        mock_game_log.return_value = self._create_mock_wr_game_log()
        mock_season_totals.return_value = self._create_mock_wr_season_totals()
        
        # Run the import
        success = await service._import_player_data(sample_wr.player_id, 2023)
        
        # Verify import succeeded
        assert success is True
        
        # Get the imported base stats
        stats = service.db.query(BaseStat).filter(
            BaseStat.player_id == sample_wr.player_id,
            BaseStat.season == 2023,
            BaseStat.week.is_(None)  # Get season totals
        ).first()
        
        # Verify accuracy of key WR metrics
        assert stats is not None
        assert stats.games == 17
        assert stats.targets == 184
        assert stats.receptions == 128
        assert stats.rec_yards == 1698
        assert stats.rec_td == 8
        assert stats.catch_pct == pytest.approx(128 / 184, rel=0.01)  # ~69.6%
        assert stats.yards_per_target == pytest.approx(1698 / 184, rel=0.01)
        
        # Verify rushing stats
        assert stats.carries == 2
        assert stats.rush_yards == 17
        assert stats.rush_td == 0
        
        # Verify game-level stats
        game_stats = service.db.query(BaseStat).filter(
            BaseStat.player_id == sample_wr.player_id,
            BaseStat.season == 2023,
            BaseStat.week.is_not(None)
        ).order_by(BaseStat.week).all()
        
        assert len(game_stats) == 3  # Three games in our mock data
        
        # Check third game
        game3 = game_stats[2]
        assert game3.week == 3
        assert game3.opponent == "LAC"
        assert game3.targets == 12
        assert game3.receptions == 10
        assert game3.rec_yards == 133
        assert game3.rec_td == 1
    
    @pytest.mark.asyncio
    @patch.object(DataImportService, '_fetch_game_log_data')
    @patch.object(DataImportService, '_fetch_season_totals')
    async def test_te_stats_import_accuracy(self, mock_season_totals, mock_game_log, service, sample_te):
        """Test accuracy of TE stats import."""
        # Set up mocks
        mock_game_log.return_value = self._create_mock_te_game_log()
        mock_season_totals.return_value = self._create_mock_te_season_totals()
        
        # Run the import
        success = await service._import_player_data(sample_te.player_id, 2023)
        
        # Verify import succeeded
        assert success is True
        
        # Get the imported base stats
        stats = service.db.query(BaseStat).filter(
            BaseStat.player_id == sample_te.player_id,
            BaseStat.season == 2023,
            BaseStat.week.is_(None)  # Get season totals
        ).first()
        
        # Verify accuracy of key TE metrics
        assert stats is not None
        assert stats.games == 15
        assert stats.targets == 121
        assert stats.receptions == 93
        assert stats.rec_yards == 984
        assert stats.rec_td == 5
        assert stats.catch_pct == pytest.approx(93 / 121, rel=0.01)  # ~76.9%
        assert stats.yards_per_target == pytest.approx(984 / 121, rel=0.01)
        
        # Verify game-level stats
        game_stats = service.db.query(BaseStat).filter(
            BaseStat.player_id == sample_te.player_id,
            BaseStat.season == 2023,
            BaseStat.week.is_not(None)
        ).order_by(BaseStat.week).all()
        
        assert len(game_stats) == 3  # Three games in our mock data
        
        # Check second game
        game2 = game_stats[1]
        assert game2.week == 2
        assert game2.opponent == "DET"
        assert game2.targets == 8
        assert game2.receptions == 7
        assert game2.rec_yards == 69
        assert game2.rec_td == 1
    
    @pytest.mark.asyncio
    @patch.object(DataImportService, '_fetch_game_log_data')
    @patch.object(DataImportService, '_fetch_season_totals')
    async def test_missing_critical_stats_handling(self, mock_season_totals, mock_game_log, service, sample_qb):
        """Test handling of missing critical stats during import."""
        # Create data with missing critical stats
        qb_data = self._create_mock_qb_season_totals()
        qb_data.loc[0, 'Att'] = None  # Missing pass attempts
        
        # Set up mocks
        mock_game_log.return_value = self._create_mock_qb_game_log()
        mock_season_totals.return_value = qb_data
        
        # Run the import
        success = await service._import_player_data(sample_qb.player_id, 2023)
        
        # Should still succeed but log a warning
        assert success is True
        
        # Get the imported base stats
        stats = service.db.query(BaseStat).filter(
            BaseStat.player_id == sample_qb.player_id,
            BaseStat.season == 2023,
            BaseStat.week.is_(None)  # Get season totals
        ).first()
        
        # Should have calculated attempts from game logs
        assert stats is not None
        assert stats.pass_attempts > 0
        
        # Should be sum of game log attempts
        game_log_attempts = 37 + 44 + 33
        assert stats.pass_attempts == game_log_attempts
    
    @pytest.mark.asyncio
    @patch.object(DataImportService, '_fetch_season_totals')
    @patch.object(DataImportService, '_fetch_game_log_data')
    async def test_discrepancy_handling(self, mock_game_log, mock_season_totals, service, sample_qb):
        """Test handling of discrepancies between game logs and season totals."""
        # Create game log with a subset of season games
        game_log = self._create_mock_qb_game_log()
        
        # Create season totals that don't match sum of game logs
        season_totals = self._create_mock_qb_season_totals()
        
        # Set up mocks
        mock_game_log.return_value = game_log
        mock_season_totals.return_value = season_totals
        
        # Run the import
        success = await service._import_player_data(sample_qb.player_id, 2023)
        
        # Should succeed despite discrepancy
        assert success is True
        
        # Get the imported base stats
        stats = service.db.query(BaseStat).filter(
            BaseStat.player_id == sample_qb.player_id,
            BaseStat.season == 2023,
            BaseStat.week.is_(None)  # Get season totals
        ).first()
        
        # Should use season totals for aggregate stats
        assert stats is not None
        assert stats.games == 17  # From season totals
        assert stats.pass_attempts == 599  # From season totals
        assert stats.pass_yards == 4472  # From season totals
        
        # Get game stats
        game_stats = service.db.query(BaseStat).filter(
            BaseStat.player_id == sample_qb.player_id,
            BaseStat.season == 2023,
            BaseStat.week.is_not(None)
        ).all()
        
        # Should have imported all available game logs
        assert len(game_stats) == 3
        
        # Check if there's a validation warning log about the discrepancy
        # This depends on how your service logs warnings