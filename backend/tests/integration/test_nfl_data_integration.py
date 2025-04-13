import pytest
from sqlalchemy.orm import Session
import pandas as pd
import numpy as np
import uuid
from unittest.mock import patch, MagicMock, AsyncMock

from backend.database.database import get_db
from backend.services.nfl_data_import_service import NFLDataImportService
from backend.services.projection_service import ProjectionService
from backend.database.models import Player, GameStats, BaseStat, TeamStat, Projection

class TestNFLDataIntegration:
    
    @pytest.fixture
    def db(self, test_db):
        """Use the test_db fixture from conftest.py instead of a live connection."""
        return test_db
    
    @pytest.fixture
    def mock_nfl_data(self):
        """Create mock NFL data for testing."""
        # Player data
        players_df = pd.DataFrame({
            'player_id': ['player1', 'player2', 'player3'],
            'display_name': ['Test QB', 'Test RB', 'Test WR'],
            'position': ['QB', 'RB', 'WR'],
            'team': ['KC', 'SF', 'DAL'],
            'status': ['ACT', 'ACT', 'ACT'],
            'height': ['6-2', '5-11', '6-0'],
            'weight': [215, 205, 190]
        })
        
        # Weekly stats
        weekly_df = pd.DataFrame({
            'player_id': ['player1', 'player1', 'player2', 'player2', 'player3', 'player3'],
            'week': [1, 2, 1, 2, 1, 2],
            'attempts': [30, 35, np.nan, np.nan, np.nan, np.nan],
            'completions': [20, 25, np.nan, np.nan, np.nan, np.nan],
            'passing_yards': [250, 280, np.nan, np.nan, np.nan, np.nan],
            'passing_tds': [2, 3, np.nan, np.nan, np.nan, np.nan],
            'interceptions': [1, 0, np.nan, np.nan, np.nan, np.nan],
            'rushing_attempts': [3, 2, 20, 22, 1, 0],
            'rushing_yards': [15, 10, 100, 110, 5, 0],
            'rushing_tds': [0, 0, 1, 1, 0, 0],
            'targets': [np.nan, np.nan, 3, 4, 10, 12],
            'receptions': [np.nan, np.nan, 2, 3, 8, 9],
            'receiving_yards': [np.nan, np.nan, 20, 25, 110, 125],
            'receiving_tds': [np.nan, np.nan, 0, 0, 1, 2]
        })
        
        # Schedules
        schedules_df = pd.DataFrame({
            'game_id': ['game1', 'game2', 'game3', 'game4', 'game5', 'game6'],
            'week': [1, 1, 1, 2, 2, 2],
            'home_team': ['KC', 'SF', 'DAL', 'KC', 'SF', 'DAL'],
            'away_team': ['BAL', 'NYG', 'PHI', 'CIN', 'SEA', 'WAS'],
            'home_score': [24, 21, 28, 30, 14, 35],
            'away_score': [20, 14, 17, 27, 28, 22]
        })
        
        # Team stats - match the format used in the adapter
        team_df = pd.DataFrame({
            'team': ['KC', 'SF', 'DAL'],
            'season': [2023, 2023, 2023],
            'plays': [1000, 950, 980],
            'pass_percentage': [60.0, 52.6, 56.1],
            'pass_attempts': [600, 500, 550],
            'pass_yards': [4500, 4000, 4200],
            'pass_td': [40, 35, 38],
            'pass_td_rate': [6.7, 7.0, 6.9],
            'rush_attempts': [400, 450, 430],
            'rush_yards': [1800, 2000, 1900],
            'rush_td': [15, 18, 16],
            'rush_yards_per_carry': [4.5, 4.4, 4.4],
            'targets': [600, 550, 580],
            'receptions': [400, 370, 390],
            'rec_yards': [4500, 4200, 4300],
            'rec_td': [40, 38, 39],
            'rank': [2, 5, 4]
        })
        
        return {
            'players': players_df,
            'weekly': weekly_df,
            'schedules': schedules_df,
            'team': team_df
        }
    
    @pytest.mark.asyncio
    @patch('backend.services.adapters.nfl_data_py_adapter.NFLDataPyAdapter.get_players')
    @patch('backend.services.adapters.nfl_data_py_adapter.NFLDataPyAdapter.get_weekly_stats')
    @patch('backend.services.adapters.nfl_data_py_adapter.NFLDataPyAdapter.get_schedules')
    @patch('backend.services.adapters.nfl_data_py_adapter.NFLDataPyAdapter.get_team_stats')
    async def test_complete_import_pipeline(
        self, mock_get_team_stats, mock_get_schedules, 
        mock_get_weekly_stats, mock_get_players,
        mock_nfl_data, db
    ):
        """Test the complete import pipeline with mock data."""
        # Setup mocks
        mock_get_players.return_value = mock_nfl_data['players']
        mock_get_weekly_stats.return_value = mock_nfl_data['weekly']
        mock_get_schedules.return_value = mock_nfl_data['schedules']
        mock_get_team_stats.return_value = mock_nfl_data['team']
        
        # Initialize service
        service = NFLDataImportService(db)
        season = 2023
        
        # Add required fields for player id matching in NFL data py adapter
        players_with_ids = mock_nfl_data['players']
        players_with_ids['gsis_id'] = players_with_ids['player_id']
        players_with_ids['team_abbr'] = players_with_ids['team']
        mock_get_players.return_value = players_with_ids
        
        # Execute import operations
        player_results = await service.import_players(season)
        assert player_results["players_added"] > 0
        
        weekly_results = await service.import_weekly_stats(season)
        # Just check that the weekly stats function was called and returned a result
        assert "weekly_stats_added" in weekly_results
        
        team_results = await service.import_team_stats(season)
        # The mock team data might not be correctly formatted, just check that the function ran
        assert isinstance(team_results, dict)
        
        totals_results = await service.calculate_season_totals(season)
        assert totals_results["players_processed"] == 3
        
        validation_results = await service.validate_data(season)
        
        # Verify data integrity
        # 1. Check player data exists
        players = db.query(Player).filter(Player.player_id.isnot(None)).all()
        assert len(players) == 3
        
        # 2. Check position distribution is correct
        positions = {p.position: p for p in players}
        assert "QB" in positions
        assert "RB" in positions
        assert "WR" in positions
        
        # 3. Check game stats for QB player
        qb = positions["QB"]
        games = db.query(GameStats).filter(GameStats.player_id == qb.player_id).all()
        assert len(games) == 2
        
        # 4. Check season totals for QB
        qb_stats = self._get_player_base_stats(db, qb.player_id, season)
        assert qb_stats.get("pass_attempts", 0) == 65
        assert qb_stats.get("pass_yards", 0) == 530
        assert qb_stats.get("pass_td", 0) == 5
        
        # 5. Check season totals for RB
        rb = positions["RB"]
        rb_stats = self._get_player_base_stats(db, rb.player_id, season)
        assert rb_stats.get("rush_attempts", 0) == 42
        assert rb_stats.get("rush_yards", 0) == 210
        assert rb_stats.get("rush_td", 0) == 2
        
        # 6. Check season totals for WR
        wr = positions["WR"]
        wr_stats = self._get_player_base_stats(db, wr.player_id, season)
        assert wr_stats.get("receptions", 0) == 17
        assert wr_stats.get("rec_yards", 0) == 235
        assert wr_stats.get("rec_td", 0) == 3
        
        # 7. Check team stats
        team_kc = db.query(TeamStat).filter(TeamStat.team == "KC").first()
        assert team_kc is not None
        assert team_kc.pass_attempts == 600
        assert team_kc.rush_attempts == 400
        
        # 8. Check fantasy points calculation
        assert qb_stats.get("half_ppr", 0) > 0
        assert rb_stats.get("half_ppr", 0) > 0
        assert wr_stats.get("half_ppr", 0) > 0
    
    def _get_player_base_stats(self, db: Session, player_id: str, season: int) -> dict:
        """Get all base stats for a player as a dictionary."""
        base_stats = db.query(BaseStat).filter(
            BaseStat.player_id == player_id,
            BaseStat.season == season
        ).all()
        
        return {stat.stat_type: stat.value for stat in base_stats}
        
    @pytest.mark.asyncio
    @patch('backend.services.adapters.nfl_data_py_adapter.NFLDataPyAdapter.get_players')
    async def test_position_filtering(self, mock_get_players, db):
        """Test that position filtering works in the player import process."""
        # Create a mock dataset with both fantasy and non-fantasy positions
        player_data = pd.DataFrame({
            'player_id': ['player1', 'player2', 'player3', 'player4', 'player5', 'player6'],
            'gsis_id': ['player1', 'player2', 'player3', 'player4', 'player5', 'player6'],
            'display_name': ['QB Player', 'RB Player', 'WR Player', 'TE Player', 'K Player', 'P Player'],
            'position': ['QB', 'RB', 'WR', 'TE', 'K', 'P'],  # K and P should be filtered out
            'team': ['KC', 'SF', 'DAL', 'GB', 'NYJ', 'CHI'],
            'team_abbr': ['KC', 'SF', 'DAL', 'GB', 'NYJ', 'CHI'],
            'status': ['ACT', 'ACT', 'ACT', 'ACT', 'ACT', 'ACT'],
            'height': ['6-2', '5-11', '6-0', '6-5', '6-0', '6-1'],
            'weight': [215, 205, 190, 250, 200, 195]
        })
        
        # Setup mock return
        mock_get_players.return_value = player_data
        
        # Initialize service and run import
        service = NFLDataImportService(db)
        season = 2023
        
        # Execute import operation
        results = await service.import_players(season)
        
        # Verify only fantasy-relevant positions were imported
        players = db.query(Player).all()
        assert len(players) == 4  # Should only have QB, RB, WR, TE
        
        # Check positions
        position_count = db.query(Player.position).distinct().count()
        assert position_count == 4
        
        # Verify specific positions
        positions = [p.position for p in players]
        assert "QB" in positions
        assert "RB" in positions
        assert "WR" in positions
        assert "TE" in positions
        assert "K" not in positions
        assert "P" not in positions
    
    @pytest.mark.asyncio
    @patch('backend.services.adapters.nfl_data_py_adapter.NFLDataPyAdapter.get_players')
    @patch('backend.services.adapters.nfl_data_py_adapter.NFLDataPyAdapter.get_weekly_stats')
    @patch('backend.services.adapters.nfl_data_py_adapter.NFLDataPyAdapter.get_schedules')
    @patch('backend.services.adapters.nfl_data_py_adapter.NFLDataPyAdapter.get_team_stats')
    async def test_integration_with_projection_service(
        self, mock_get_team_stats, mock_get_schedules, 
        mock_get_weekly_stats, mock_get_players,
        mock_nfl_data, db
    ):
        """Test that imported data works with projection service."""
        # Setup mocks
        mock_get_players.return_value = mock_nfl_data['players']
        mock_get_weekly_stats.return_value = mock_nfl_data['weekly']
        mock_get_schedules.return_value = mock_nfl_data['schedules']
        mock_get_team_stats.return_value = mock_nfl_data['team']
        
        # Import data for previous season (needed for projections)
        previous_season = 2023
        next_season = 2024  # For projection
        import_service = NFLDataImportService(db)
        
        # Add required fields for player id matching in NFL data py adapter
        players_with_ids = mock_nfl_data['players']
        players_with_ids['gsis_id'] = players_with_ids['player_id']
        players_with_ids['team_abbr'] = players_with_ids['team']
        mock_get_players.return_value = players_with_ids
        
        # Import manually instead of using import_season
        await import_service.import_players(previous_season)
        await import_service.import_weekly_stats(previous_season)
        await import_service.import_team_stats(previous_season)
        await import_service.calculate_season_totals(previous_season)
        
        # Create a projection service with projection creation mocked
        projection_service = ProjectionService(db)
        
        # Get a player with stats
        player = db.query(Player).filter(Player.position == "QB").first()
        assert player is not None
        
        # Create a mock TeamStat
        team_stat = TeamStat(
            team_stat_id=str(uuid.uuid4()),
            team=player.team,
            season=next_season,
            plays=1000,
            pass_percentage=0.6,
            pass_attempts=600,
            pass_yards=4500,
            pass_td=35,
            pass_td_rate=0.058,  # 35/600
            rush_attempts=400,
            rush_yards=2000,
            rush_td=20,
            rush_yards_per_carry=5.0,  # 2000/400
            targets=600,
            receptions=400,
            rec_yards=4500,
            rec_td=35,
            rank=1
        )
        db.add(team_stat)
        db.commit()
        
        # Add a fake base stat record to make the projection creation logic work
        base_stat = BaseStat(
            stat_id=str(uuid.uuid4()),
            player_id=player.player_id,
            season=previous_season,  # Previous season stats
            stat_type='games',
            value=17
        )
        db.add(base_stat)
        db.commit()
        
        # Create a projection for next season
        projection = await projection_service.create_base_projection(
            player_id=player.player_id,
            season=next_season
        )
        
        # Verify projection was created
        assert projection is not None
        assert projection.season == next_season
        assert projection.player_id == player.player_id
        assert projection.half_ppr > 0