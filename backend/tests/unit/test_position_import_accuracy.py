import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from backend.services.nfl_data_import_service import NFLDataImportService
from backend.database.models import Player, BaseStat, GameStats

class TestPositionImportAccuracy:
    """
    Tests for position-specific data import accuracy using the NFL data import service.
    """
    
    @pytest.fixture(scope="function")
    def service(self, test_db):
        """Create NFLDataImportService instance for testing."""
        return NFLDataImportService(test_db)
    
    @pytest.fixture
    def mock_qb_weekly_data(self):
        """Create mock QB weekly stats data."""
        return pd.DataFrame({
            'player_id': ['qb1', 'qb1', 'qb1'],
            'week': [1, 2, 3],
            'recent_team': ['KC', 'KC', 'KC'],
            'attempts': [30, 32, 35],
            'completions': [22, 25, 28],
            'passing_yards': [250, 280, 310],
            'passing_tds': [2, 3, 2],
            'interceptions': [1, 0, 1],
            'rushing_attempts': [4, 5, 3],
            'rushing_yards': [20, 25, 15],
            'rushing_tds': [0, 1, 0]
        })
    
    @pytest.fixture
    def mock_rb_weekly_data(self):
        """Create mock RB weekly stats data."""
        return pd.DataFrame({
            'player_id': ['rb1', 'rb1', 'rb1'],
            'week': [1, 2, 3],
            'recent_team': ['SF', 'SF', 'SF'],
            'rushing_attempts': [18, 20, 22],
            'rushing_yards': [85, 95, 110],
            'rushing_tds': [1, 0, 1],
            'targets': [4, 5, 3],
            'receptions': [3, 4, 2],
            'receiving_yards': [25, 35, 15],
            'receiving_tds': [0, 1, 0]
        })
    
    @pytest.fixture
    def mock_wr_weekly_data(self):
        """Create mock WR weekly stats data."""
        return pd.DataFrame({
            'player_id': ['wr1', 'wr1', 'wr1'],
            'week': [1, 2, 3],
            'recent_team': ['DAL', 'DAL', 'DAL'],
            'targets': [10, 12, 8],
            'receptions': [7, 9, 5],
            'receiving_yards': [95, 120, 75],
            'receiving_tds': [1, 1, 0],
            'rushing_attempts': [1, 0, 1],
            'rushing_yards': [8, 0, 5],
            'rushing_tds': [0, 0, 0]
        })
    
    @pytest.fixture
    def mock_schedules_data(self):
        """Create mock game schedules data."""
        return pd.DataFrame({
            'game_id': ['game1', 'game2', 'game3', 'game4', 'game5', 'game6', 'game7', 'game8', 'game9'],
            'week': [1, 1, 1, 2, 2, 2, 3, 3, 3],
            'home_team': ['KC', 'SF', 'DAL', 'KC', 'SF', 'DAL', 'KC', 'SF', 'DAL'],
            'away_team': ['BAL', 'NYG', 'NYJ', 'CIN', 'SEA', 'PHI', 'LV', 'LAR', 'WAS'],
            'home_score': [24, 21, 28, 31, 17, 24, 27, 14, 35],
            'away_score': [20, 14, 14, 21, 10, 17, 20, 10, 20]
        })
    
    @pytest.fixture
    def sample_players(self, test_db):
        """Create sample players for different positions."""
        players = [
            Player(player_id='qb1', name='Test QB', team='KC', position='QB'),
            Player(player_id='rb1', name='Test RB', team='SF', position='RB'),
            Player(player_id='wr1', name='Test WR', team='DAL', position='WR')
        ]
        
        for player in players:
            test_db.add(player)
        
        test_db.commit()
        return players
    
    @pytest.mark.asyncio
    @patch('backend.services.adapters.nfl_data_py_adapter.NFLDataPyAdapter.get_weekly_stats')
    @patch('backend.services.adapters.nfl_data_py_adapter.NFLDataPyAdapter.get_schedules')
    async def test_qb_import_accuracy(self, mock_get_schedules, mock_get_weekly_stats, service, sample_players, mock_qb_weekly_data, mock_schedules_data):
        """Test accuracy of QB data import."""
        # Setup mocks
        mock_get_weekly_stats.return_value = mock_qb_weekly_data
        mock_get_schedules.return_value = mock_schedules_data
        
        # Import weekly stats
        await service.import_weekly_stats(2023)
        
        # Verify game stats were created
        game_stats = service.db.query(GameStats).filter(
            GameStats.player_id == 'qb1',
            GameStats.season == 2023
        ).all()
        
        assert len(game_stats) == 3
        
        # Check first game stats
        first_game = game_stats[0]
        assert first_game.week == 1
        assert first_game.opponent == 'BAL'
        assert first_game.stats['pass_attempts'] == 30
        assert first_game.stats['completions'] == 22
        assert first_game.stats['pass_yards'] == 250
        assert first_game.stats['pass_td'] == 2
        assert first_game.stats['interceptions'] == 1
        assert first_game.stats['rush_attempts'] == 4
        assert first_game.stats['rush_yards'] == 20
        assert first_game.stats['rush_td'] == 0
        
        # Calculate season totals
        await service.calculate_season_totals(2023)
        
        # Verify base stats were created
        base_stats = service.db.query(BaseStat).filter(
            BaseStat.player_id == 'qb1',
            BaseStat.season == 2023
        ).all()
        
        # Convert to dict for easier assertion
        stat_dict = {stat.stat_type: stat.value for stat in base_stats}
        
        # Verify season totals
        assert stat_dict['games'] == 3
        assert stat_dict['pass_attempts'] == 97  # 30+32+35
        assert stat_dict['completions'] == 75  # 22+25+28
        assert stat_dict['pass_yards'] == 840  # 250+280+310
        assert stat_dict['pass_td'] == 7  # 2+3+2
        assert stat_dict['interceptions'] == 2  # 1+0+1
        assert stat_dict['rush_attempts'] == 12  # 4+5+3
        assert stat_dict['rush_yards'] == 60  # 20+25+15
        assert stat_dict['rush_td'] == 1  # 0+1+0
        
        # Verify fantasy points calculation
        # (840 * 0.04) + (7 * 4) - (2 * 1) + (60 * 0.1) + (1 * 6) = 33.6 + 28 - 2 + 6 + 6 = 71.6
        expected_points = 71.6
        assert abs(stat_dict['half_ppr'] - expected_points) < 0.1
    
    @pytest.mark.asyncio
    @patch('backend.services.adapters.nfl_data_py_adapter.NFLDataPyAdapter.get_weekly_stats')
    @patch('backend.services.adapters.nfl_data_py_adapter.NFLDataPyAdapter.get_schedules')
    async def test_rb_import_accuracy(self, mock_get_schedules, mock_get_weekly_stats, service, sample_players, mock_rb_weekly_data, mock_schedules_data):
        """Test accuracy of RB data import."""
        # Setup mocks
        mock_get_weekly_stats.return_value = mock_rb_weekly_data
        mock_get_schedules.return_value = mock_schedules_data
        
        # Import weekly stats
        await service.import_weekly_stats(2023)
        
        # Verify game stats were created
        game_stats = service.db.query(GameStats).filter(
            GameStats.player_id == 'rb1',
            GameStats.season == 2023
        ).all()
        
        assert len(game_stats) == 3
        
        # Check first game stats
        first_game = game_stats[0]
        assert first_game.week == 1
        assert first_game.opponent == 'NYG'
        assert first_game.stats['rush_attempts'] == 18
        assert first_game.stats['rush_yards'] == 85
        assert first_game.stats['rush_td'] == 1
        assert first_game.stats['targets'] == 4
        assert first_game.stats['receptions'] == 3
        assert first_game.stats['rec_yards'] == 25
        assert first_game.stats['rec_td'] == 0
        
        # Calculate season totals
        await service.calculate_season_totals(2023)
        
        # Verify base stats were created
        base_stats = service.db.query(BaseStat).filter(
            BaseStat.player_id == 'rb1',
            BaseStat.season == 2023
        ).all()
        
        # Convert to dict for easier assertion
        stat_dict = {stat.stat_type: stat.value for stat in base_stats}
        
        # Verify season totals
        assert stat_dict['games'] == 3
        assert stat_dict['rush_attempts'] == 60  # 18+20+22
        assert stat_dict['rush_yards'] == 290  # 85+95+110
        assert stat_dict['rush_td'] == 2  # 1+0+1
        assert stat_dict['targets'] == 12  # 4+5+3
        assert stat_dict['receptions'] == 9  # 3+4+2
        assert stat_dict['rec_yards'] == 75  # 25+35+15
        assert stat_dict['rec_td'] == 1  # 0+1+0
        
        # Verify fantasy points calculation
        # (290 * 0.1) + (2 * 6) + (9 * 0.5) + (75 * 0.1) + (1 * 6) = 29 + 12 + 4.5 + 7.5 + 6 = 59
        expected_points = 59.0
        assert abs(stat_dict['half_ppr'] - expected_points) < 0.1
    
    @pytest.mark.asyncio
    @patch('backend.services.adapters.nfl_data_py_adapter.NFLDataPyAdapter.get_weekly_stats')
    @patch('backend.services.adapters.nfl_data_py_adapter.NFLDataPyAdapter.get_schedules')
    async def test_wr_import_accuracy(self, mock_get_schedules, mock_get_weekly_stats, service, sample_players, mock_wr_weekly_data, mock_schedules_data):
        """Test accuracy of WR data import."""
        # Setup mocks
        mock_get_weekly_stats.return_value = mock_wr_weekly_data
        mock_get_schedules.return_value = mock_schedules_data
        
        # Import weekly stats
        await service.import_weekly_stats(2023)
        
        # Verify game stats were created
        game_stats = service.db.query(GameStats).filter(
            GameStats.player_id == 'wr1',
            GameStats.season == 2023
        ).all()
        
        assert len(game_stats) == 3
        
        # Check first game stats
        first_game = game_stats[0]
        assert first_game.week == 1
        assert first_game.opponent == 'NYJ'
        assert first_game.stats['targets'] == 10
        assert first_game.stats['receptions'] == 7
        assert first_game.stats['rec_yards'] == 95
        assert first_game.stats['rec_td'] == 1
        assert first_game.stats['rush_attempts'] == 1
        assert first_game.stats['rush_yards'] == 8
        assert first_game.stats['rush_td'] == 0
        
        # Calculate season totals
        await service.calculate_season_totals(2023)
        
        # Verify base stats were created
        base_stats = service.db.query(BaseStat).filter(
            BaseStat.player_id == 'wr1',
            BaseStat.season == 2023
        ).all()
        
        # Convert to dict for easier assertion
        stat_dict = {stat.stat_type: stat.value for stat in base_stats}
        
        # Verify season totals
        assert stat_dict['games'] == 3
        assert stat_dict['targets'] == 30  # 10+12+8
        assert stat_dict['receptions'] == 21  # 7+9+5
        assert stat_dict['rec_yards'] == 290  # 95+120+75
        assert stat_dict['rec_td'] == 2  # 1+1+0
        assert stat_dict['rush_attempts'] == 2  # 1+0+1
        assert stat_dict['rush_yards'] == 13  # 8+0+5
        assert stat_dict['rush_td'] == 0  # 0+0+0
        
        # Verify fantasy points calculation
        # (21 * 0.5) + (290 * 0.1) + (2 * 6) + (13 * 0.1) = 10.5 + 29 + 12 + 1.3 = 52.8
        expected_points = 52.8
        assert abs(stat_dict['half_ppr'] - expected_points) < 0.1
    
    @pytest.mark.asyncio
    async def test_fantasy_point_calculation_accuracy(self, service):
        """Test fantasy point calculation accuracy for different positions."""
        # Test QB fantasy points
        qb_stats = {
            "pass_yards": 300,
            "pass_td": 3,
            "interceptions": 1,
            "rush_yards": 25,
            "rush_td": 0
        }
        qb_points = service._calculate_fantasy_points(qb_stats, "QB")
        # (300 * 0.04) + (3 * 4) - (1 * 1) + (25 * 0.1) = 12 + 12 - 1 + 2.5 = 25.5
        assert abs(qb_points - 25.5) < 0.1
        
        # Test RB fantasy points
        rb_stats = {
            "rush_yards": 120,
            "rush_td": 2,
            "receptions": 3,
            "rec_yards": 25,
            "rec_td": 0
        }
        rb_points = service._calculate_fantasy_points(rb_stats, "RB")
        # (120 * 0.1) + (2 * 6) + (3 * 0.5) + (25 * 0.1) = 12 + 12 + 1.5 + 2.5 = 28
        assert abs(rb_points - 28.0) < 0.1
        
        # Test WR fantasy points
        wr_stats = {
            "receptions": 8,
            "rec_yards": 120,
            "rec_td": 1,
            "rush_yards": 15,
            "rush_td": 0
        }
        wr_points = service._calculate_fantasy_points(wr_stats, "WR")
        # (8 * 0.5) + (120 * 0.1) + (1 * 6) + (15 * 0.1) = 4 + 12 + 6 + 1.5 = 23.5
        assert abs(wr_points - 23.5) < 0.1
        
        # Test TE fantasy points
        te_stats = {
            "receptions": 6,
            "rec_yards": 85,
            "rec_td": 1,
            "rush_yards": 0,
            "rush_td": 0
        }
        te_points = service._calculate_fantasy_points(te_stats, "TE")
        # (6 * 0.5) + (85 * 0.1) + (1 * 6) = 3 + 8.5 + 6 = 17.5
        assert abs(te_points - 17.5) < 0.1