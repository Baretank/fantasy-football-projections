import pytest
import uuid
from datetime import datetime
from sqlalchemy import and_

from backend.services.projection_service import ProjectionService
from backend.services.data_service import DataService
from backend.services.team_stat_service import TeamStatsService
from backend.services.data_validation import DataValidationService
from backend.database.models import Player, BaseStat, TeamStat, Projection, GameStats

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
        """Create TeamStatsService instance for testing."""
        return TeamStatsService(test_db)
    
    @pytest.fixture(scope="function")
    def validation_service(self, test_db):
        """Create DataValidationService instance for testing."""
        return DataValidationService(test_db)
    
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