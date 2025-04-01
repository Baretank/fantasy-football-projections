import pytest
import pandas as pd
from sqlalchemy.orm import Session
from backend.services.nfl_data_import_service import NFLDataImportService
from backend.database.models import Player, BaseStat, GameStats
import uuid

class TestDataImportTransformations:
    @pytest.fixture(scope="function")
    def service(self, test_db):
        """Create NFLDataImportService instance for testing."""
        return NFLDataImportService(test_db)
    
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
    
    @pytest.fixture(scope="function")
    def sample_game_stats(self, test_db, sample_player):
        """Create sample game stats for testing."""
        game_stats = []
        
        # Create QB game stats
        qb_stats = [
            {
                "pass_attempts": 37, "completions": 25, "pass_yards": 305, "pass_td": 2, "interceptions": 1,
                "rush_attempts": 6, "rush_yards": 45, "rush_td": 0
            },
            {
                "pass_attempts": 44, "completions": 29, "pass_yards": 316, "pass_td": 2, "interceptions": 0,
                "rush_attempts": 4, "rush_yards": 27, "rush_td": 0
            },
            {
                "pass_attempts": 33, "completions": 24, "pass_yards": 272, "pass_td": 3, "interceptions": 0,
                "rush_attempts": 3, "rush_yards": 17, "rush_td": 1
            },
            {
                "pass_attempts": 40, "completions": 30, "pass_yards": 298, "pass_td": 1, "interceptions": 1,
                "rush_attempts": 7, "rush_yards": 53, "rush_td": 0
            },
            {
                "pass_attempts": 45, "completions": 31, "pass_yards": 348, "pass_td": 3, "interceptions": 0,
                "rush_attempts": 5, "rush_yards": 38, "rush_td": 0
            }
        ]
        
        for i, stats in enumerate(qb_stats, 1):
            game_stat = GameStats(
                game_stat_id=str(uuid.uuid4()),
                player_id=sample_player.player_id,
                season=2023,
                week=i,
                opponent=["JAX", "DET", "CHI", "NYJ", "MIN"][i-1],
                game_location="home",
                result="W",
                team_score=["17", "31", "41", "23", "27"][i-1],
                opponent_score=["9", "17", "10", "20", "20"][i-1],
                stats=stats
            )
            test_db.add(game_stat)
            game_stats.append(game_stat)
        
        test_db.commit()
        return game_stats
    
    @pytest.mark.asyncio
    async def test_calculate_season_totals(self, service, sample_player, sample_game_stats):
        """Test calculating season totals from game stats."""
        # Calculate season totals
        result = await service.calculate_season_totals(2023)
        
        # Verify result structure
        assert isinstance(result, dict)
        assert "totals_created" in result
        assert "players_processed" in result
        
        # Query the base stats to verify calculations
        base_stats = service.db.query(BaseStat).filter(
            BaseStat.player_id == sample_player.player_id,
            BaseStat.season == 2023
        ).all()
        
        # Convert to dict for easier assertion
        stat_dict = {stat.stat_type: stat.value for stat in base_stats}
        
        # Verify pass stats
        assert stat_dict["pass_attempts"] == 199  # 37+44+33+40+45
        assert stat_dict["completions"] == 139  # 25+29+24+30+31
        assert stat_dict["pass_yards"] == 1539  # 305+316+272+298+348
        assert stat_dict["pass_td"] == 11  # 2+2+3+1+3
        assert stat_dict["interceptions"] == 2  # 1+0+0+1+0
        
        # Verify rush stats
        assert stat_dict["rush_attempts"] == 25  # 6+4+3+7+5
        assert stat_dict["rush_yards"] == 180  # 45+27+17+53+38
        assert stat_dict["rush_td"] == 1  # 0+0+1+0+0
        
        # Verify games count
        assert stat_dict["games"] == 5
        
        # Verify fantasy points calculation
        # (pass_yards * 0.04) + (pass_td * 4) - (interceptions * 1) + (rush_yards * 0.1) + (rush_td * 6)
        expected_points = (1539 * 0.04) + (11 * 4) - (2 * 1) + (180 * 0.1) + (1 * 6)
        assert stat_dict["half_ppr"] == pytest.approx(expected_points, rel=0.01)
    
    @pytest.mark.asyncio
    async def test_validate_data(self, service, sample_player, sample_game_stats):
        """Test data validation functionality."""
        # Delete one base stat to simulate an inconsistency
        service.db.query(BaseStat).filter(
            BaseStat.player_id == sample_player.player_id,
            BaseStat.season == 2023,
            BaseStat.stat_type == "pass_td"
        ).delete()
        
        # Add a wrong value to test correction
        wrong_stat = BaseStat(
            stat_id=str(uuid.uuid4()),
            player_id=sample_player.player_id,
            season=2023,
            stat_type="games",
            value=10  # Wrong value, should be 5
        )
        service.db.add(wrong_stat)
        service.db.commit()
        
        # Run validation
        result = await service.validate_data(2023)
        
        # Verify issues were found and fixed
        assert result["issues_found"] > 0
        assert result["issues_fixed"] > 0
        
        # Check the corrected values
        base_stats = service.db.query(BaseStat).filter(
            BaseStat.player_id == sample_player.player_id,
            BaseStat.season == 2023
        ).all()
        
        # Convert to dict for easier assertion
        stat_dict = {stat.stat_type: stat.value for stat in base_stats}
        
        # Verify the missing stat was recreated
        assert "pass_td" in stat_dict
        assert stat_dict["pass_td"] == 11
        
        # Verify the wrong value was corrected
        assert stat_dict["games"] == 5
    
    @pytest.mark.asyncio
    async def test_stat_consistency_across_positions(self, service, test_db, sample_player):
        """Test consistency of stat transformations across different positions."""
        # Change sample player position and create different stats
        positions = ["QB", "RB", "WR", "TE"]
        
        for position in positions:
            # Update player position
            service.db.query(Player).filter(
                Player.player_id == sample_player.player_id
            ).update({"position": position})
            service.db.commit()
            
            # Clear existing game stats
            service.db.query(GameStats).filter(
                GameStats.player_id == sample_player.player_id
            ).delete()
            service.db.commit()
            
            # Create position-specific game stats
            if position == "QB":
                stats = {
                    "pass_attempts": 40, "completions": 30, "pass_yards": 300, "pass_td": 2, "interceptions": 1,
                    "rush_attempts": 5, "rush_yards": 25, "rush_td": 0
                }
            elif position == "RB":
                stats = {
                    "rush_attempts": 20, "rush_yards": 100, "rush_td": 1,
                    "targets": 5, "receptions": 4, "rec_yards": 30, "rec_td": 0
                }
            elif position in ["WR", "TE"]:
                stats = {
                    "targets": 10, "receptions": 8, "rec_yards": 120, "rec_td": 1,
                    "rush_attempts": 1, "rush_yards": 5, "rush_td": 0
                }
            
            # Add game stat
            game_stat = GameStats(
                game_stat_id=str(uuid.uuid4()),
                player_id=sample_player.player_id,
                season=2023,
                week=1,
                opponent="OPP",
                game_location="home",
                result="W",
                team_score="28",
                opponent_score="21",
                stats=stats
            )
            service.db.add(game_stat)
            service.db.commit()
            
            # Clear existing base stats
            service.db.query(BaseStat).filter(
                BaseStat.player_id == sample_player.player_id
            ).delete()
            service.db.commit()
            
            # Calculate season totals
            await service.calculate_season_totals(2023)
            
            # Get the base stats
            base_stats = service.db.query(BaseStat).filter(
                BaseStat.player_id == sample_player.player_id,
                BaseStat.season == 2023
            ).all()
            
            # Convert to dict
            stat_dict = {stat.stat_type: stat.value for stat in base_stats}
            
            # Check for appropriate stats based on position
            if position == "QB":
                assert "pass_attempts" in stat_dict
                assert "completions" in stat_dict
                assert "pass_yards" in stat_dict
                assert "pass_td" in stat_dict
                assert "interceptions" in stat_dict
                assert stat_dict["pass_attempts"] == 40
            
            if position in ["RB", "WR", "TE"]:
                assert "targets" in stat_dict
                assert "receptions" in stat_dict
                assert "rec_yards" in stat_dict
                assert "rec_td" in stat_dict
                
                if position == "RB":
                    assert stat_dict["rush_attempts"] == 20
                    assert stat_dict["rush_yards"] == 100
                elif position in ["WR", "TE"]:
                    assert stat_dict["targets"] == 10
                    assert stat_dict["receptions"] == 8
            
            # All positions should have these stats
            assert "games" in stat_dict
            assert "half_ppr" in stat_dict
    
    @pytest.mark.asyncio
    async def test_fantasy_point_calculation(self, service, sample_player):
        """Test fantasy point calculation for different positions."""
        positions = ["QB", "RB", "WR", "TE"]
        expected_points = {
            # Let's match the actual calculation from the service:
            "QB": 21.5,  # (300 * 0.04) + (2 * 4) - (1 * 1) + (25 * 0.1) = 12 + 8 - 1 + 2.5 = 21.5
            "RB": 21.0,  # (100 * 0.1) + (1 * 6) + (4 * 0.5) + (30 * 0.1) = 10 + 6 + 2 + 3 = 21
            "WR": 22.5,  # (8 * 0.5) + (120 * 0.1) + (1 * 6) + (5 * 0.1) = 4 + 12 + 6 + 0.5 = 22.5
            "TE": 22.5    # Same as WR
        }
        
        for position in positions:
            # Create stats for each position
            if position == "QB":
                stats = {
                    "pass_yards": 300,
                    "pass_td": 2,
                    "interceptions": 1,
                    "rush_yards": 25,
                    "rush_td": 0
                }
            elif position == "RB":
                stats = {
                    "rush_yards": 100,
                    "rush_td": 1,
                    "receptions": 4,
                    "rec_yards": 30,
                    "rec_td": 0
                }
            elif position in ["WR", "TE"]:
                stats = {
                    "receptions": 8,
                    "rec_yards": 120,
                    "rec_td": 1,
                    "rush_yards": 5,
                    "rush_td": 0
                }
            
            # Call the fantasy point calculation method
            points = service._calculate_fantasy_points(stats, position)
            
            # Verify points calculation
            assert points == pytest.approx(expected_points[position], rel=0.1)