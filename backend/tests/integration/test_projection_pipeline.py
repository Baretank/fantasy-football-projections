import pytest
import uuid
from datetime import datetime
from sqlalchemy import and_

from backend.services.projection_service import ProjectionService
from backend.services.data_service import DataService
from backend.services.team_stat_service import TeamStatService
from backend.services.data_validation import DataValidationService
from backend.services.override_service import OverrideService
from backend.database.models import Player, BaseStat, TeamStat, Projection, GameStats, StatOverride

class TestProjectionPipeline:
    @pytest.fixture(scope="function")
    def projection_service(self, test_db):
        """Create ProjectionService instance for testing."""
        return ProjectionService(test_db)
    
    @pytest.fixture(scope="function")
    def data_service(self, test_db):
        """Create DataService instance for testing."""
        return DataService(test_db)
    
    @pytest.fixture(scope="function")
    def team_stat_service(self, test_db):
        """Create TeamStatService instance for testing."""
        return TeamStatService(test_db)
    
    @pytest.fixture(scope="function")
    def validation_service(self, test_db):
        """Create DataValidationService instance for testing."""
        return DataValidationService(test_db)
        
    @pytest.fixture(scope="function")
    def override_service(self, test_db):
        """Create OverrideService instance for testing."""
        return OverrideService(test_db)
    
    @pytest.fixture(scope="function")
    def setup_test_data(self, test_db):
        """Set up test data for the pipeline."""
        season = 2023  # Historical season
        projection_season = 2024  # Projection target season
        
        # Create test teams
        teams = ["KC", "SF", "GB", "DAL"]
        
        # Create team stats for both seasons
        team_stats = []
        for team in teams:
            # Historical stats (2023)
            ts_2023 = TeamStat(
                team_stat_id=str(uuid.uuid4()),
                team=team,
                season=season,
                plays=1000,
                pass_percentage=0.6,
                pass_attempts=600,
                pass_yards=4200,
                pass_td=30,
                pass_td_rate=0.05,
                rush_attempts=400,
                rush_yards=1800,
                rush_td=15,
                carries=400,
                rush_yards_per_carry=4.5,
                targets=600,
                receptions=390,
                rec_yards=4200,
                rec_td=30,
                rank=1
            )
            
            # Projection season stats (2024)
            ts_2024 = TeamStat(
                team_stat_id=str(uuid.uuid4()),
                team=team,
                season=projection_season,
                plays=1000,
                pass_percentage=0.6,
                pass_attempts=600,
                pass_yards=4200,
                pass_td=30,
                pass_td_rate=0.05,
                rush_attempts=400,
                rush_yards=1800,
                rush_td=15,
                carries=400,
                rush_yards_per_carry=4.5,
                targets=600,
                receptions=390,
                rec_yards=4200,
                rec_td=30,
                rank=1
            )
            
            team_stats.extend([ts_2023, ts_2024])
        
        # Add team stats to database
        for ts in team_stats:
            test_db.add(ts)
        
        # Create test players for each team
        players = []
        for team in teams:
            # Create one player of each position for each team
            players.extend([
                Player(player_id=str(uuid.uuid4()), name=f"{team} QB", team=team, position="QB"),
                Player(player_id=str(uuid.uuid4()), name=f"{team} RB1", team=team, position="RB"),
                Player(player_id=str(uuid.uuid4()), name=f"{team} RB2", team=team, position="RB"),
                Player(player_id=str(uuid.uuid4()), name=f"{team} WR1", team=team, position="WR"),
                Player(player_id=str(uuid.uuid4()), name=f"{team} WR2", team=team, position="WR"),
                Player(player_id=str(uuid.uuid4()), name=f"{team} TE", team=team, position="TE")
            ])
        
        # Add players to database
        for player in players:
            test_db.add(player)
        
        test_db.commit()
        
        # Create historical stats for players
        for player in players:
            # Create appropriate stats based on position
            if player.position == "QB":
                stats = [
                    BaseStat(player_id=player.player_id, season=season, stat_type="games", value=17.0),
                    BaseStat(player_id=player.player_id, season=season, stat_type="completions", value=380.0),
                    BaseStat(player_id=player.player_id, season=season, stat_type="pass_attempts", value=580.0),
                    BaseStat(player_id=player.player_id, season=season, stat_type="pass_yards", value=4100.0),
                    BaseStat(player_id=player.player_id, season=season, stat_type="pass_td", value=28.0),
                    BaseStat(player_id=player.player_id, season=season, stat_type="interceptions", value=10.0),
                    BaseStat(player_id=player.player_id, season=season, stat_type="rush_attempts", value=55.0),
                    BaseStat(player_id=player.player_id, season=season, stat_type="rush_yards", value=250.0),
                    BaseStat(player_id=player.player_id, season=season, stat_type="rush_td", value=2.0)
                ]
            
            elif player.position == "RB":
                if "RB1" in player.name:
                    # Lead back
                    stats = [
                        BaseStat(player_id=player.player_id, season=season, stat_type="games", value=16.0),
                        BaseStat(player_id=player.player_id, season=season, stat_type="rush_attempts", value=240.0),
                        BaseStat(player_id=player.player_id, season=season, stat_type="rush_yards", value=1100.0),
                        BaseStat(player_id=player.player_id, season=season, stat_type="rush_td", value=9.0),
                        BaseStat(player_id=player.player_id, season=season, stat_type="targets", value=60.0),
                        BaseStat(player_id=player.player_id, season=season, stat_type="receptions", value=48.0),
                        BaseStat(player_id=player.player_id, season=season, stat_type="rec_yards", value=380.0),
                        BaseStat(player_id=player.player_id, season=season, stat_type="rec_td", value=2.0)
                    ]
                else:
                    # Backup
                    stats = [
                        BaseStat(player_id=player.player_id, season=season, stat_type="games", value=16.0),
                        BaseStat(player_id=player.player_id, season=season, stat_type="rush_attempts", value=120.0),
                        BaseStat(player_id=player.player_id, season=season, stat_type="rush_yards", value=520.0),
                        BaseStat(player_id=player.player_id, season=season, stat_type="rush_td", value=3.0),
                        BaseStat(player_id=player.player_id, season=season, stat_type="targets", value=30.0),
                        BaseStat(player_id=player.player_id, season=season, stat_type="receptions", value=22.0),
                        BaseStat(player_id=player.player_id, season=season, stat_type="rec_yards", value=180.0),
                        BaseStat(player_id=player.player_id, season=season, stat_type="rec_td", value=1.0)
                    ]
            
            elif player.position == "WR":
                if "WR1" in player.name:
                    # Primary receiver
                    stats = [
                        BaseStat(player_id=player.player_id, season=season, stat_type="games", value=17.0),
                        BaseStat(player_id=player.player_id, season=season, stat_type="targets", value=150.0),
                        BaseStat(player_id=player.player_id, season=season, stat_type="receptions", value=105.0),
                        BaseStat(player_id=player.player_id, season=season, stat_type="rec_yards", value=1300.0),
                        BaseStat(player_id=player.player_id, season=season, stat_type="rec_td", value=10.0),
                        BaseStat(player_id=player.player_id, season=season, stat_type="rush_attempts", value=10.0),
                        BaseStat(player_id=player.player_id, season=season, stat_type="rush_yards", value=60.0),
                        BaseStat(player_id=player.player_id, season=season, stat_type="rush_td", value=0.0)
                    ]
                else:
                    # Secondary receiver
                    stats = [
                        BaseStat(player_id=player.player_id, season=season, stat_type="games", value=17.0),
                        BaseStat(player_id=player.player_id, season=season, stat_type="targets", value=110.0),
                        BaseStat(player_id=player.player_id, season=season, stat_type="receptions", value=75.0),
                        BaseStat(player_id=player.player_id, season=season, stat_type="rec_yards", value=900.0),
                        BaseStat(player_id=player.player_id, season=season, stat_type="rec_td", value=7.0),
                        BaseStat(player_id=player.player_id, season=season, stat_type="rush_attempts", value=5.0),
                        BaseStat(player_id=player.player_id, season=season, stat_type="rush_yards", value=30.0),
                        BaseStat(player_id=player.player_id, season=season, stat_type="rush_td", value=0.0)
                    ]
            
            elif player.position == "TE":
                stats = [
                    BaseStat(player_id=player.player_id, season=season, stat_type="games", value=16.0),
                    BaseStat(player_id=player.player_id, season=season, stat_type="targets", value=80.0),
                    BaseStat(player_id=player.player_id, season=season, stat_type="receptions", value=60.0),
                    BaseStat(player_id=player.player_id, season=season, stat_type="rec_yards", value=650.0),
                    BaseStat(player_id=player.player_id, season=season, stat_type="rec_td", value=5.0)
                ]
            
            # Add stats to database
            for stat in stats:
                test_db.add(stat)
        
        # Add game logs for validation tests
        player_to_add_games = players[0]  # Use first player (KC QB)
        for week in range(1, 17):
            game_log = GameStats(
                player_id=player_to_add_games.player_id,
                season=season,
                week=week,
                opponent="OPP",
                game_location="home",
                result="W 30-7",  # Add required result
                team_score=30,    # Add required scores
                opponent_score=7,
                stats={
                    "cmp": "22", 
                    "att": "34", 
                    "pass_yds": "241", 
                    "pass_td": "1.7", 
                    "int": "0.6",
                    "rush_att": "3.2", 
                    "rush_yds": "14.7", 
                    "rush_td": "0.12"
                }
            )
            test_db.add(game_log)
        
        test_db.commit()
        
        # Return test data context for tests to use
        return {
            "teams": teams,
            "players": players,
            "season": season,
            "projection_season": projection_season
        }
    
    @pytest.mark.asyncio
    async def test_create_base_projection(self, projection_service, setup_test_data):
        """Test creating a baseline projection from historical data."""
        player = setup_test_data["players"][0]  # First player (KC QB)
        projection_season = setup_test_data["projection_season"]
        
        # Create base projection
        projection = await projection_service.create_base_projection(player.player_id, projection_season)
        
        # Verify projection was created successfully
        assert projection is not None
        assert projection.season == projection_season
        assert projection.player_id == player.player_id
        
        # Verify position-specific stats
        assert projection.pass_attempts > 0
        assert projection.pass_yards > 0
        assert projection.pass_td > 0
        assert projection.half_ppr > 0
    
    @pytest.mark.asyncio
    async def test_data_validation_integration(self, validation_service, setup_test_data):
        """Test data validation as part of the pipeline."""
        player = setup_test_data["players"][0]  # First player (KC QB)
        season = setup_test_data["season"]
        
        # Introduce an inconsistency for testing
        games_stat = validation_service.db.query(BaseStat).filter(
            and_(
                BaseStat.player_id == player.player_id,
                BaseStat.season == season,
                BaseStat.stat_type == "games"
            )
        ).first()
        
        # Set to incorrect value
        games_stat.value = 15.0
        validation_service.db.commit()
        
        # Run validation
        issues = validation_service.validate_player_data(player, season)
        
        # Verify issues were found and fixed
        assert len(issues) > 0
        assert any("game logs" in issue for issue in issues)
        
        # Check that the issue was fixed
        updated_stat = validation_service.db.query(BaseStat).filter(
            and_(
                BaseStat.player_id == player.player_id,
                BaseStat.season == season,
                BaseStat.stat_type == "games"
            )
        ).first()
        
        assert updated_stat.value == 16.0  # Should match the number of game logs
    
    @pytest.mark.asyncio
    async def test_apply_projection_adjustments(self, projection_service, setup_test_data):
        """Test applying adjustments to a player projection."""
        player = setup_test_data["players"][0]  # First player (KC QB)
        projection_season = setup_test_data["projection_season"]
        
        # Create base projection
        base_projection = await projection_service.create_base_projection(player.player_id, projection_season)
        assert base_projection is not None
        
        # Store original values
        original_pass_attempts = base_projection.pass_attempts
        original_pass_td = base_projection.pass_td
        original_fantasy_points = base_projection.half_ppr
        
        # Apply adjustments
        adjustments = {
            'pass_volume': 1.10,  # 10% increase in passing volume
            'td_rate': 1.15,      # 15% increase in TD rate
            'int_rate': 0.90      # 10% decrease in interceptions
        }
        
        # Update projection with adjustments
        updated_projection = await projection_service.update_projection(
            projection_id=base_projection.projection_id,
            adjustments=adjustments
        )
        
        # Verify adjustments were applied correctly
        assert updated_projection is not None
        assert updated_projection.pass_attempts > original_pass_attempts
        assert updated_projection.pass_td > original_pass_td
        assert updated_projection.half_ppr != original_fantasy_points
        
        # Verify specific adjustment factors
        assert abs(updated_projection.pass_attempts / original_pass_attempts - 1.10) < 0.01
        assert abs(updated_projection.pass_td / original_pass_td - 1.15) < 0.01
    
    @pytest.mark.asyncio
    async def test_team_level_adjustments(self, team_stat_service, projection_service, setup_test_data):
        """Test applying team-level adjustments that affect multiple players."""
        team = setup_test_data["teams"][0]  # First team (KC)
        projection_season = setup_test_data["projection_season"]
        
        # Get all players for the team
        team_players = [p for p in setup_test_data["players"] if p.team == team]
        
        # Create base projections for all team players
        for player in team_players:
            projection = await projection_service.create_base_projection(player.player_id, projection_season)
            assert projection is not None
        
        # Get all projections before adjustment
        projections_before = await projection_service.get_player_projections(
            team=team, 
            season=projection_season
        )
        
        # Store original values for later comparison
        original_values = {}
        for proj in projections_before:
            original_values[proj.player_id] = {
                'pass_attempts': getattr(proj, 'pass_attempts', 0),
                'pass_yards': getattr(proj, 'pass_yards', 0),
                'rush_attempts': getattr(proj, 'carries', 0),
                'rush_yards': getattr(proj, 'rush_yards', 0),
                'targets': getattr(proj, 'targets', 0),
                'fantasy_points': proj.half_ppr
            }
        
        # Apply team-level adjustments
        team_adjustments = {
            'pass_volume': 1.08,    # 8% increase in passing
            'rush_volume': 0.95,    # 5% decrease in rushing
            'scoring_rate': 1.05    # 5% increase in scoring
        }
        
        # Apply adjustments via team stat service
        updated_projections = await team_stat_service.apply_team_adjustments(
            team=team,
            season=projection_season,
            adjustments=team_adjustments
        )
        
        # Verify adjustments were applied to all players
        assert len(updated_projections) > 0
        
        # Check position-specific adjustments
        for proj in updated_projections:
            original = original_values[proj.player_id]
            
            # QBs should have increased passing volume
            if proj.player.position == 'QB':
                assert proj.pass_attempts > original['pass_attempts']
                assert abs(proj.pass_attempts / original['pass_attempts'] - 1.08) < 0.01
            
            # RBs should have decreased rushing volume
            if proj.player.position == 'RB':
                assert proj.carries < original['rush_attempts']
                assert abs(proj.carries / original['rush_attempts'] - 0.95) < 0.01
            
            # All receiving players should have adjusted targets in line with pass volume
            if proj.player.position in ['WR', 'TE', 'RB'] and original['targets'] > 0:
                assert abs(proj.targets / original['targets'] - 1.08) < 0.01
            
            # Fantasy points should be different
            assert proj.half_ppr != original['fantasy_points']
    
    @pytest.mark.asyncio
    async def test_player_share_adjustments(self, team_stat_service, projection_service, setup_test_data):
        """Test adjusting player usage shares within a team."""
        team = setup_test_data["teams"][0]  # First team (KC)
        projection_season = setup_test_data["projection_season"]
        
        # Get all players for the team
        team_players = [p for p in setup_test_data["players"] if p.team == team]
        
        # Create base projections for all team players
        for player in team_players:
            projection = await projection_service.create_base_projection(player.player_id, projection_season)
            assert projection is not None
        
        # Get projections and identify specific players to adjust
        projections = await projection_service.get_player_projections(
            team=team, 
            season=projection_season
        )
        
        # Find a WR to adjust
        wr1 = next((p for p in team_players if 'WR1' in p.name), None)
        assert wr1 is not None
        
        # Get original target share
        usage_before = await team_stat_service.get_team_usage_breakdown(team, projection_season)
        wr1_targets_before = 0
        total_targets_before = 0
        
        if 'targets' in usage_before:
            for player_id, data in usage_before['targets']['players'].items():
                total_targets_before += data['value']
                if player_id == wr1.player_id:
                    wr1_targets_before = data['value']
        
        assert wr1_targets_before > 0
        original_share = wr1_targets_before / total_targets_before
        
        # Increase WR1's target share by 20%
        new_share = min(0.45, original_share * 1.2)  # Cap at 45% to keep realistic
        
        # Apply player-specific share adjustment
        player_shares = {
            wr1.player_id: {'target_share': new_share}
        }
        
        # Apply team adjustments with player shares
        team_adjustments = {}  # No team-level changes, just player shares
        
        await team_stat_service.apply_team_adjustments(
            team=team,
            season=projection_season,
            adjustments=team_adjustments,
            player_shares=player_shares
        )
        
        # Get updated usage
        usage_after = await team_stat_service.get_team_usage_breakdown(team, projection_season)
        
        # Verify WR1's target share increased
        wr1_targets_after = 0
        total_targets_after = 0
        
        if 'targets' in usage_after:
            for player_id, data in usage_after['targets']['players'].items():
                total_targets_after += data['value']
                if player_id == wr1.player_id:
                    wr1_targets_after = data['value']
        
        new_actual_share = wr1_targets_after / total_targets_after
        
        # Verify the share is close to the requested share
        assert abs(new_actual_share - new_share) < 0.05
        assert new_actual_share > original_share
    
    @pytest.mark.asyncio
    async def test_complete_projection_pipeline(
        self, 
        projection_service, 
        team_stat_service, 
        validation_service,
        setup_test_data
    ):
        """Test the complete projection pipeline from validation to team adjustments."""
        team = setup_test_data["teams"][0]  # First team (KC)
        season = setup_test_data["season"]
        projection_season = setup_test_data["projection_season"]
        
        # Step 1: Validate historical data
        team_players = [p for p in setup_test_data["players"] if p.team == team]
        
        for player in team_players:
            # Validate and fix any data issues
            issues = validation_service.validate_player_data(player, season)
            if issues:
                print(f"Validation issues for {player.name}: {issues}")
        
        # Step 2: Create base projections
        base_projections = []
        for player in team_players:
            proj = await projection_service.create_base_projection(player.player_id, projection_season)
            assert proj is not None
            base_projections.append(proj)
        
        # Step 3: Apply individual adjustments to key players
        qb = next((p for p in team_players if p.position == 'QB'), None)
        assert qb is not None
        
        qb_proj = next((p for p in base_projections if p.player_id == qb.player_id), None)
        assert qb_proj is not None
        
        # Apply QB-specific adjustments
        qb_adjustments = {
            'pass_volume': 1.05,
            'td_rate': 1.10
        }
        
        updated_qb_proj = await projection_service.update_projection(
            projection_id=qb_proj.projection_id,
            adjustments=qb_adjustments
        )
        assert updated_qb_proj is not None
        
        # Step 4: Apply team-level adjustments
        team_adjustments = {
            'scoring_rate': 1.08,  # 8% more scoring
            'pass_volume': 1.04,   # 4% more passing
            'rush_efficiency': 1.05  # 5% more efficient rushing
        }
        
        # Adjust WR1 target share
        wr1 = next((p for p in team_players if 'WR1' in p.name), None)
        assert wr1 is not None
        
        player_shares = {
            wr1.player_id: {'target_share': 0.30}  # Set WR1 to 30% target share
        }
        
        final_projections = await team_stat_service.apply_team_adjustments(
            team=team,
            season=projection_season,
            adjustments=team_adjustments,
            player_shares=player_shares
        )
        
        # Verify the complete pipeline results
        assert len(final_projections) > 0
        
        # Check that key players have reasonable projections
        for proj in final_projections:
            # Fantasy points should be positive
            assert proj.half_ppr > 0
            
            # Position-specific checks
            if proj.player.position == 'QB':
                assert proj.pass_attempts > 500  # QB should have significant attempts
                assert proj.pass_yards > 3500
                
            elif proj.player.position == 'RB' and 'RB1' in proj.player.name:
                assert proj.carries > 200  # RB1 should have significant carries
                
            elif proj.player.position == 'WR' and 'WR1' in proj.player.name:
                # WR1 should have ~30% target share
                wr1_targets = proj.targets
                team_targets = sum(p.targets for p in final_projections if hasattr(p, 'targets') and p.targets)
                wr1_share = wr1_targets / team_targets
                assert abs(wr1_share - 0.30) < 0.05
                
        # Final consistency check - team totals should add up
        total_pass_attempts = sum(getattr(p, 'pass_attempts', 0) for p in final_projections)
        total_targets = sum(getattr(p, 'targets', 0) for p in final_projections)
        
        # Passing attempts should roughly equal targets (with small margin for error)
        assert abs(total_pass_attempts - total_targets) < 10
        
    @pytest.mark.asyncio
    @pytest.fixture(scope="function")
    async def import_test_data(self, test_db):
        """Create mock data import service and test player."""
        from unittest.mock import patch, MagicMock
        from backend.services.data_import_service import DataImportService
        
        # Create a test player
        player = Player(
            player_id=str(uuid.uuid4()),
            name="Test Import Player",
            team="SF",
            position="RB"
        )
        test_db.add(player)
        test_db.commit()
        
        # Create mock service with mocked external data fetching
        service = DataImportService(test_db)
        
        # Mock response data for fetch methods
        mock_game_log = pd.DataFrame({
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
        
        mock_season_totals = pd.DataFrame({
            "Rk": [1],
            "Player": ["Test Import Player"],
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
        
        # Patch the service's fetch methods
        with patch.object(service, '_fetch_game_log_data', return_value=mock_game_log), \
             patch.object(service, '_fetch_season_totals', return_value=mock_season_totals):
             
            yield {
                "service": service,
                "player": player,
                "mock_game_log": mock_game_log,
                "mock_season_totals": mock_season_totals
            }
    
    @pytest.mark.asyncio
    async def test_import_to_projection_pipeline(
        self, 
        import_test_data, 
        projection_service, 
        validation_service, 
        team_stats_2024
    ):
        """Test the complete import-to-projection pipeline."""
        data_import_service = import_test_data["service"]
        player = import_test_data["player"]
        
        # Step 1: Import player data
        success = await data_import_service._import_player_data(player.player_id, 2023)
        assert success is True
        
        # Step 2: Validate imported data
        issues = validation_service.validate_player_data(player, 2023)
        for issue in issues:
            print(f"Validation issue: {issue}")
        # Some issues may be expected due to the mock data
        
        # Step 3: Create base projection from imported data
        projection = await projection_service.create_base_projection(player.player_id, 2024)
        assert projection is not None
        
        # Verify projection was generated based on imported data
        base_stats = data_import_service.db.query(BaseStat).filter(
            BaseStat.player_id == player.player_id,
            BaseStat.season == 2023,
            BaseStat.week.is_(None)  # Season totals
        ).first()
        assert base_stats is not None
        
        # Projection should be related to historical data
        # RB rush attempts should be similar to historical
        if base_stats.carries:
            assert projection.carries > 0
            # Allow for reasonable range around historical value
            assert 0.7 * base_stats.carries <= projection.carries <= 1.3 * base_stats.carries
        
        # Step 4: Apply adjustments
        adjustments = {
            'rush_volume': 1.1,  # 10% more rushing
            'rec_volume': 0.9,   # 10% less receiving
            'td_rate': 1.05      # 5% more TDs
        }
        
        updated_projection = await projection_service.update_projection(
            projection_id=projection.projection_id,
            adjustments=adjustments
        )
        
        # Verify adjustments were applied
        assert updated_projection.carries > projection.carries
        assert updated_projection.targets < projection.targets
        
        # Fantasy points should be calculated
        assert updated_projection.half_ppr > 0
        
        # Calculate expected points and verify they match (within reasonable margin)
        expected_points = (
            updated_projection.rush_yards * 0.1 +   # 1 pt per 10 rush yards
            updated_projection.rush_td * 6 +        # 6 pts per rush TD
            updated_projection.rec_yards * 0.1 +    # 1 pt per 10 rec yards
            updated_projection.receptions * 0.5 +   # 0.5 pt per reception (half PPR)
            updated_projection.rec_td * 6           # 6 pts per rec TD
        )
        
        assert updated_projection.half_ppr == pytest.approx(expected_points, rel=0.01)
        
        # Verify position-specific stats are reasonable
        assert updated_projection.carries > 200  # RB1 should have significant carries
        assert updated_projection.rush_yards > 900
        assert updated_projection.targets > 0
        assert updated_projection.receptions > 0
    
    @pytest.mark.asyncio
    async def test_batch_import_and_projection(
        self,
        setup_test_data,
        projection_service,
        test_db
    ):
        """Test batch import followed by projection creation for multiple players."""
        from unittest.mock import patch, MagicMock
        from backend.services.batch_service import BatchService
        from backend.services.data_import_service import DataImportService
        
        # Get a subset of players to test batch processing
        players = setup_test_data["players"][:5]  # First 5 players
        player_ids = [p.player_id for p in players]
        
        # Create batch service
        batch_service = BatchService(test_db)
        
        # Create data import service with mocked import method
        data_service = DataImportService(test_db)
        
        # Mock successful import for all players
        successful_imports = {}
        for player_id in player_ids:
            successful_imports[player_id] = True
        
        # Mock the batch import process
        with patch.object(batch_service, 'process_batch', return_value=successful_imports):
            # Step 1: Batch import players
            results = await batch_service.process_batch(
                service=data_service,
                method_name="_import_player_data",
                items=player_ids,
                season=2023,
                batch_size=2,
                delay=0.1
            )
            
            # Verify all imports were successful
            assert all(results.values())
            assert len(results) == len(player_ids)
            
            # Step 2: Batch create projections
            projections = []
            for player_id in player_ids:
                # Create base projection
                proj = await projection_service.create_base_projection(player_id, 2024)
                assert proj is not None
                projections.append(proj)
            
            # Apply the same adjustment to all projections
            common_adjustments = {
                'td_rate': 1.05  # 5% more TDs for everyone
            }
            
            updated_projections = []
            for proj in projections:
                updated_proj = await projection_service.update_projection(
                    projection_id=proj.projection_id,
                    adjustments=common_adjustments
                )
                updated_projections.append(updated_proj)
            
            # Verify results
            assert len(updated_projections) == len(player_ids)
            
            # Each player should have increased TDs relative to base
            for i, proj in enumerate(updated_projections):
                base_proj = projections[i]
                
                # Stats that should increase
                if hasattr(base_proj, 'pass_td') and base_proj.pass_td:
                    assert proj.pass_td > base_proj.pass_td
                
                if hasattr(base_proj, 'rush_td') and base_proj.rush_td:
                    assert proj.rush_td > base_proj.rush_td
                
                if hasattr(base_proj, 'rec_td') and base_proj.rec_td:
                    assert proj.rec_td > base_proj.rec_td
                
                # Fantasy points should increase
                assert proj.half_ppr > base_proj.half_ppr
    
    @pytest.mark.asyncio
    async def test_override_and_projection_integration(
        self,
        setup_test_data,
        projection_service,
        override_service
    ):
        """Test the integration of overrides with the projection pipeline."""
        team = setup_test_data["teams"][0]  # First team (KC)
        projection_season = setup_test_data["projection_season"]
        
        # Get all players for the team
        team_players = [p for p in setup_test_data["players"] if p.team == team]
        
        # Step 1: Create base projections for all team players
        projections = {}
        for player in team_players:
            projection = await projection_service.create_base_projection(player.player_id, projection_season)
            assert projection is not None
            projections[player.player_id] = projection
        
        # Step 2: Find a QB player to override
        qb = next((p for p in team_players if p.position == 'QB'), None)
        assert qb is not None
        qb_proj = projections[qb.player_id]
        
        # Store original values for comparison
        original_pass_attempts = qb_proj.pass_attempts 
        original_pass_yards = qb_proj.pass_yards
        original_fantasy_points = qb_proj.half_ppr
        
        # Step 3: Create an override to increase pass attempts by 20%
        new_pass_attempts = original_pass_attempts * 1.2
        
        override = await override_service.create_override(
            player_id=qb.player_id,
            projection_id=qb_proj.projection_id,
            stat_name="pass_attempts",
            manual_value=new_pass_attempts,
            notes="Testing override integration"
        )
        
        assert override is not None
        assert override.manual_value == new_pass_attempts
        
        # Step 4: Verify the override was applied and dependent stats recalculated
        updated_qb_proj = await projection_service.get_projection(qb_proj.projection_id)
        assert updated_qb_proj is not None
        
        # Pass attempts should match our override
        assert updated_qb_proj.pass_attempts == new_pass_attempts
        
        # Verify the yards per attempt has been recalculated (should be lower with more attempts)
        original_yards_per_att = original_pass_yards / original_pass_attempts if original_pass_attempts > 0 else 0
        new_yards_per_att = updated_qb_proj.pass_yards / new_pass_attempts if new_pass_attempts > 0 else 0
        
        assert new_yards_per_att < original_yards_per_att  # Should decrease with more attempts
        
        # Step 5: Apply another override to a RB and test compound effects
        rb = next((p for p in team_players if p.position == 'RB' and 'RB1' in p.name), None)
        if not rb:
            rb = next((p for p in team_players if p.position == 'RB'), None)  # Any RB if no RB1
            
        assert rb is not None
        rb_proj = projections[rb.player_id]
        
        # Store original rushing TD value
        original_rush_td = rb_proj.rush_td
        original_rb_fantasy_points = rb_proj.half_ppr
        
        # Create override to increase rush TDs by 50%
        new_rush_td = original_rush_td * 1.5
        
        override_rb = await override_service.create_override(
            player_id=rb.player_id,
            projection_id=rb_proj.projection_id,
            stat_name="rush_td",
            manual_value=new_rush_td,
            notes="Testing TD override"
        )
        
        assert override_rb is not None
        
        # Verify fantasy points increased
        rb_proj_after = await projection_service.get_projection(rb_proj.projection_id)
        assert rb_proj_after.half_ppr > original_rb_fantasy_points
        
        # Step 6: Test override removal and restoration of calculated values
        # Delete the QB override
        delete_result = await override_service.delete_override(override.override_id)
        assert delete_result is True
        
        # Verify stats were restored to pre-override values
        restored_qb_proj = await projection_service.get_projection(qb_proj.projection_id)
        assert abs(restored_qb_proj.pass_attempts - original_pass_attempts) < 0.01