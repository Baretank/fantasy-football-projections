import pytest
import uuid
from unittest.mock import patch, MagicMock
import tempfile
import os
import pandas as pd
import json
from datetime import datetime
from sqlalchemy import and_

from backend.services.nfl_data_import_service import NFLDataImportService
from backend.services.player_import_service import PlayerImportService
from backend.services.team_stat_service import TeamStatService
from backend.services.projection_service import ProjectionService
# Import these services if they exist
try:
    from backend.services.rookie_import_service import RookieImportService
    from backend.services.rookie_projection_service import RookieProjectionService
except ImportError:
    # Mock these services if they don't exist
    class RookieImportService:
        def __init__(self, db):
            self.db = db
    
    class RookieProjectionService:
        def __init__(self, db):
            self.db = db
from backend.services.scenario_service import ScenarioService
from backend.services.override_service import OverrideService
from backend.database.models import Player, BaseStat, TeamStat, Projection, Scenario, StatOverride, RookieProjectionTemplate

class TestCompleteSeasonPipeline:
    @pytest.fixture(scope="function")
    def services(self, test_db):
        """Create all services needed for complete pipeline testing."""
        return {
            "data_import": NFLDataImportService(test_db),
            "player_import": PlayerImportService(test_db),
            "team_stat": TeamStatService(test_db),
            "projection": ProjectionService(test_db),
            "rookie_import": RookieImportService(test_db),
            "rookie_projection": RookieProjectionService(test_db),
            "scenario": ScenarioService(test_db),
            "override": OverrideService(test_db)
        }
    
    @pytest.fixture(scope="function")
    def setup_test_data(self, test_db):
        """Set up minimal test data for the complete pipeline."""
        # Create test teams
        teams = ["KC", "SF", "BUF", "BAL"]
        
        # Create basic players (veterans)
        players = []
        for team in teams:
            players.extend([
                Player(player_id=str(uuid.uuid4()), name=f"{team} QB", team=team, position="QB"),
                Player(player_id=str(uuid.uuid4()), name=f"{team} RB1", team=team, position="RB"),
                Player(player_id=str(uuid.uuid4()), name=f"{team} WR1", team=team, position="WR"),
                Player(player_id=str(uuid.uuid4()), name=f"{team} TE", team=team, position="TE")
            ])
        
        # Add rookies (using status field instead of rookie_year)
        rookies = [
            Player(
                player_id=str(uuid.uuid4()), 
                name="Rookie QB", 
                team="KC", 
                position="QB",
                status="Rookie",
                draft_pick=1,
                draft_round=1
            ),
            Player(
                player_id=str(uuid.uuid4()), 
                name="Rookie RB", 
                team="SF", 
                position="RB",
                status="Rookie",
                draft_pick=15,
                draft_round=1
            )
        ]
        
        players.extend(rookies)
        
        # Add all players to database
        for player in players:
            test_db.add(player)
        
        # Add team stats for previous and current seasons
        previous_season = datetime.now().year - 1
        current_season = datetime.now().year
        
        for team in teams:
            # Previous season stats
            prev_stat = TeamStat(
                team_stat_id=str(uuid.uuid4()),
                team=team,
                season=previous_season,
                plays=1000,
                pass_percentage=0.60,
                pass_attempts=600,
                pass_yards=4200,
                pass_td=30,
                pass_td_rate=0.05,
                rush_attempts=400,
                rush_yards=1800,
                rush_td=15,
                rush_yards_per_carry=4.5,
                targets=600,
                receptions=390,
                rec_yards=4200,
                rec_td=30,
                rank=1
            )
            
            # Current season stats (with slight adjustments)
            curr_stat = TeamStat(
                team_stat_id=str(uuid.uuid4()),
                team=team,
                season=current_season,
                plays=1000,
                pass_percentage=0.62,
                pass_attempts=620,
                pass_yards=4300,
                pass_td=32,
                pass_td_rate=0.052,
                rush_attempts=380,
                rush_yards=1750,
                rush_td=14,
                rush_yards_per_carry=4.6,
                targets=620,
                receptions=400,
                rec_yards=4300,
                rec_td=32,
                rank=1
            )
            
            test_db.add(prev_stat)
            test_db.add(curr_stat)
        
        # Add historical stats for veteran players
        for player in players:
            if player.status != "Rookie":  # Skip rookies
                # Create appropriate stats based on position
                if player.position == "QB":
                    stats = [
                        BaseStat(player_id=player.player_id, season=previous_season, stat_type="games", value=17.0),
                        BaseStat(player_id=player.player_id, season=previous_season, stat_type="completions", value=380.0),
                        BaseStat(player_id=player.player_id, season=previous_season, stat_type="pass_attempts", value=580.0),
                        BaseStat(player_id=player.player_id, season=previous_season, stat_type="pass_yards", value=4100.0),
                        BaseStat(player_id=player.player_id, season=previous_season, stat_type="pass_td", value=28.0),
                        BaseStat(player_id=player.player_id, season=previous_season, stat_type="interceptions", value=10.0),
                        BaseStat(player_id=player.player_id, season=previous_season, stat_type="rush_attempts", value=55.0),
                        BaseStat(player_id=player.player_id, season=previous_season, stat_type="rush_yards", value=250.0),
                        BaseStat(player_id=player.player_id, season=previous_season, stat_type="rush_td", value=2.0)
                    ]
                elif player.position == "RB":
                    stats = [
                        BaseStat(player_id=player.player_id, season=previous_season, stat_type="games", value=16.0),
                        BaseStat(player_id=player.player_id, season=previous_season, stat_type="rush_attempts", value=240.0),
                        BaseStat(player_id=player.player_id, season=previous_season, stat_type="rush_yards", value=1100.0),
                        BaseStat(player_id=player.player_id, season=previous_season, stat_type="rush_td", value=9.0),
                        BaseStat(player_id=player.player_id, season=previous_season, stat_type="targets", value=60.0),
                        BaseStat(player_id=player.player_id, season=previous_season, stat_type="receptions", value=48.0),
                        BaseStat(player_id=player.player_id, season=previous_season, stat_type="rec_yards", value=380.0),
                        BaseStat(player_id=player.player_id, season=previous_season, stat_type="rec_td", value=2.0)
                    ]
                elif player.position == "WR":
                    stats = [
                        BaseStat(player_id=player.player_id, season=previous_season, stat_type="games", value=17.0),
                        BaseStat(player_id=player.player_id, season=previous_season, stat_type="targets", value=150.0),
                        BaseStat(player_id=player.player_id, season=previous_season, stat_type="receptions", value=105.0),
                        BaseStat(player_id=player.player_id, season=previous_season, stat_type="rec_yards", value=1300.0),
                        BaseStat(player_id=player.player_id, season=previous_season, stat_type="rec_td", value=10.0),
                        BaseStat(player_id=player.player_id, season=previous_season, stat_type="rush_attempts", value=10.0),
                        BaseStat(player_id=player.player_id, season=previous_season, stat_type="rush_yards", value=60.0),
                        BaseStat(player_id=player.player_id, season=previous_season, stat_type="rush_td", value=0.0)
                    ]
                elif player.position == "TE":
                    stats = [
                        BaseStat(player_id=player.player_id, season=previous_season, stat_type="games", value=16.0),
                        BaseStat(player_id=player.player_id, season=previous_season, stat_type="targets", value=80.0),
                        BaseStat(player_id=player.player_id, season=previous_season, stat_type="receptions", value=60.0),
                        BaseStat(player_id=player.player_id, season=previous_season, stat_type="rec_yards", value=650.0),
                        BaseStat(player_id=player.player_id, season=previous_season, stat_type="rec_td", value=5.0)
                    ]
                
                # Add stats to database
                for stat in stats:
                    test_db.add(stat)
        
        # Add rookie projection templates
        rookie_templates = [
            RookieProjectionTemplate(
                template_id=str(uuid.uuid4()),
                position="QB",
                draft_round=1,
                draft_pick_min=1,
                draft_pick_max=10,
                games=16.0,
                snap_share=0.7,
                pass_attempts=520.0,
                comp_pct=0.65,
                yards_per_att=7.3,
                pass_td_rate=0.046,
                int_rate=0.023,
                rush_att_per_game=4.5,
                rush_yards_per_att=5.0,
                rush_td_per_game=0.25
            ),
            RookieProjectionTemplate(
                template_id=str(uuid.uuid4()),
                position="RB",
                draft_round=1,
                draft_pick_min=11,
                draft_pick_max=32,
                games=16.0,
                snap_share=0.6,
                rush_att_per_game=11.0,
                rush_yards_per_att=4.2,
                rush_td_per_att=0.03,
                targets_per_game=3.0,
                catch_rate=0.7,
                rec_yards_per_catch=8.0,
                rec_td_per_catch=0.03
            )
        ]
        
        for template in rookie_templates:
            test_db.add(template)
        
        test_db.commit()
        
        return {
            "teams": teams,
            "players": players,
            "rookies": rookies,
            "previous_season": previous_season,
            "current_season": current_season
        }
    
    @pytest.mark.asyncio
    async def test_complete_pipeline(self, services, setup_test_data, test_db):
        """Test the complete season pipeline from data import to projection creation."""
        # 1. Create base projections for veteran players
        veteran_projections = []
        for player in setup_test_data["players"]:
            if player.status != "Rookie":  # Only veterans
                projection = await services["projection"].create_base_projection(
                    player_id=player.player_id,
                    season=setup_test_data["current_season"]
                )
                assert projection is not None
                veteran_projections.append(projection)
        
        # 2. Generate rookie projections
        rookie_projections = []
        for rookie in setup_test_data["rookies"]:
            projection = await services["rookie_projection"].create_draft_based_projection(
                player_id=rookie.player_id,
                draft_position=rookie.draft_pick,  # Use draft_pick as overall position
                season=setup_test_data["current_season"]
            )
            assert projection is not None
            rookie_projections.append(projection)
        # We've already checked each projection individually
        
        # 3. Apply team-level adjustments - simplify to just use the original method
        for team in setup_test_data["teams"]:
            # Simple static adjustments for testing
            adjustments = {
                'pass_volume': 1.05,
                'scoring_rate': 1.08
            }
            
            # Apply team adjustments using the original method (which is used by the API)
            updated_projections = await services["team_stat"].apply_team_adjustments(
                team=team,
                season=setup_test_data["current_season"],
                adjustments=adjustments
            )
            
            assert len(updated_projections) > 0
        
        # 4. Create scenarios
        # Injury scenario for KC QB
        kc_qb = next((p for p in setup_test_data["players"] if p.team == "KC" and p.position == "QB" and p.status != "Rookie"), None)
        assert kc_qb is not None
        
        injury_scenario = await services["scenario"].create_scenario(
            name="KC QB Injury",
            description="KC QB misses 4 games due to injury"
            # Removed invalid 'season' parameter
        )
        
        # Find the original projection
        original_proj = test_db.query(Projection).filter(
            and_(
                Projection.player_id == kc_qb.player_id,
                Projection.season == setup_test_data["current_season"]
            )
        ).first()
        
        # Apply scenario adjustment (reduce games by 25%)
        await services["scenario"].add_player_to_scenario(
            scenario_id=injury_scenario.scenario_id,
            player_id=kc_qb.player_id,
            adjustments={
                'games': original_proj.games * 0.75,  # Missing 4 games in a 16-game season
                'pass_attempts': original_proj.pass_attempts * 0.75,
                'pass_yards': original_proj.pass_yards * 0.75,
                'pass_td': original_proj.pass_td * 0.75
            }
        )
        
        # Verify scenario projection
        scenario_proj = await services["scenario"].get_player_scenario_projection(
            scenario_id=injury_scenario.scenario_id,
            player_id=kc_qb.player_id
        )
        
        assert scenario_proj is not None
        assert scenario_proj.games < original_proj.games
        assert scenario_proj.pass_attempts < original_proj.pass_attempts
        
        # 5. Apply specific player overrides
        # Find KC rookie QB
        kc_rookie_qb = next((p for p in setup_test_data["rookies"] if p.team == "KC" and p.position == "QB" and p.status == "Rookie"), None)
        assert kc_rookie_qb is not None
        
        # Get original rookie projection
        rookie_proj = test_db.query(Projection).filter(
            and_(
                Projection.player_id == kc_rookie_qb.player_id,
                Projection.season == setup_test_data["current_season"]
            )
        ).first()
        
        # With veteran QB injured, rookie gets more playing time
        await services["override"].create_override(
            player_id=kc_rookie_qb.player_id,
            projection_id=rookie_proj.projection_id,
            stat_name="games",
            manual_value=rookie_proj.games + 4,  # 4 more games
            notes="Rookie gets playing time due to veteran injury"
        )
        
        # Increase rookie's passing stats proportionally
        games_factor = (rookie_proj.games + 4) / rookie_proj.games
        
        await services["override"].create_override(
            player_id=kc_rookie_qb.player_id,
            projection_id=rookie_proj.projection_id,
            stat_name="pass_attempts",
            manual_value=rookie_proj.pass_attempts * games_factor,
            notes="Increased attempts due to more games"
        )
        
        # 6. Get final projections
        # Get all final projections
        final_projections = test_db.query(Projection).filter(
            and_(
                Projection.season == setup_test_data["current_season"],
                Projection.scenario_id.is_(None)  # Base projections, not scenario ones
            )
        ).all()
        
        # Veteran count (skip rookies)
        veteran_count = len([p for p in setup_test_data["players"] if p.status != "Rookie"])
        
        # Verify counts
        assert len(final_projections) == len(setup_test_data["players"])
        assert len(rookie_projections) == len(setup_test_data["rookies"])
        assert len(veteran_projections) == veteran_count
        
        # 7. Calculate fantasy rankings by position
        position_rankings = {}
        for position in ["QB", "RB", "WR", "TE"]:
            position_projs = [p for p in final_projections
                              if test_db.query(Player).filter(Player.player_id == p.player_id).first().position == position]
            
            # Sort by fantasy points
            sorted_projs = sorted(position_projs, key=lambda p: p.half_ppr, reverse=True)
            position_rankings[position] = sorted_projs
        
        # Verify rankings
        for position in ["QB", "RB", "WR", "TE"]:
            assert len(position_rankings[position]) > 0
            
            # Top player should have higher points than second player
            if len(position_rankings[position]) >= 2:
                assert position_rankings[position][0].half_ppr >= position_rankings[position][1].half_ppr
        
        # 8. Performance checks - we should have reasonable fantasy points for all players
        for proj in final_projections:
            player = test_db.query(Player).filter(Player.player_id == proj.player_id).first()
            
            # Verify position-specific fantasy points are reasonable
            if player.position == "QB":
                assert proj.half_ppr >= 200, f"QB {player.name} has too few fantasy points: {proj.half_ppr}"
            elif player.position == "RB":
                assert proj.half_ppr >= 100, f"RB {player.name} has too few fantasy points: {proj.half_ppr}"
            elif player.position == "WR":
                assert proj.half_ppr >= 100, f"WR {player.name} has too few fantasy points: {proj.half_ppr}"
            elif player.position == "TE":
                assert proj.half_ppr >= 70, f"TE {player.name} has too few fantasy points: {proj.half_ppr}"
        
        # 9. All team stats should be consistent for the position groups
        for team in setup_test_data["teams"]:
            # Get team stats
            team_stats = test_db.query(TeamStat).filter(
                and_(
                    TeamStat.team == team,
                    TeamStat.season == setup_test_data["current_season"]
                )
            ).first()
            
            # Get all team's projections
            team_projections = [p for p in final_projections
                                if test_db.query(Player).filter(Player.player_id == p.player_id).first().team == team]
            
            # Sum key team stats
            total_pass_attempts = sum(getattr(p, 'pass_attempts', 0) for p in team_projections)
            total_rush_attempts = sum(getattr(p, 'rush_attempts', 0) for p in team_projections)
            total_targets = sum(getattr(p, 'targets', 0) for p in team_projections)
            
            # Targets should be close to pass attempts
            if total_pass_attempts > 0 and total_targets > 0:
                ratio = total_targets / total_pass_attempts
                assert 0.8 <= ratio <= 1.2, f"Team {team} targets/pass_attempts ratio {ratio} is outside reasonable bounds"