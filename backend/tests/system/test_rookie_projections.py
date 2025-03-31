import pytest
import uuid
from datetime import datetime
from sqlalchemy import and_

from backend.services.rookie_projection_service import RookieProjectionService
from backend.database.models import Player, TeamStat, Projection, RookieProjectionTemplate

class TestRookieProjections:
    @pytest.fixture(scope="function")
    def rookie_service(self, test_db):
        """Create rookie projection service for testing."""
        return RookieProjectionService(test_db)
    
    @pytest.fixture(scope="function")
    def setup_rookie_data(self, test_db):
        """Set up minimal test data for rookie player projections."""
        # Create test teams
        teams = ["KC", "SF", "BUF"]
        
        # Current season
        current_season = datetime.now().year
        
        # Add team stats for current season
        for team in teams:
            # Current season stats
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
                carries=380,
                rush_yards_per_carry=4.6,
                targets=620,
                receptions=400,
                rec_yards=4300,
                rec_td=32,
                rank=1
            )
            test_db.add(curr_stat)
        
        # Create rookie players
        rookies = [
            Player(
                player_id=str(uuid.uuid4()), 
                name="Top QB Rookie", 
                team="KC", 
                position="QB",
                status="Rookie",
                draft_pick=1,
                draft_round=1
            ),
            Player(
                player_id=str(uuid.uuid4()), 
                name="Mid QB Rookie", 
                team="SF", 
                position="QB",
                status="Rookie",
                draft_pick=15,
                draft_round=1
            ),
            Player(
                player_id=str(uuid.uuid4()), 
                name="Late QB Rookie", 
                team="BUF", 
                position="QB",
                status="Rookie",
                draft_pick=28,
                draft_round=1
            ),
            Player(
                player_id=str(uuid.uuid4()), 
                name="Top RB Rookie", 
                team="KC", 
                position="RB",
                status="Rookie",
                draft_pick=5,
                draft_round=1
            ),
            Player(
                player_id=str(uuid.uuid4()), 
                name="Mid RB Rookie", 
                team="SF", 
                position="RB",
                status="Rookie",
                draft_pick=20,
                draft_round=1
            ),
            Player(
                player_id=str(uuid.uuid4()), 
                name="Early WR Rookie", 
                team="BUF", 
                position="WR",
                status="Rookie",
                draft_pick=10,
                draft_round=1
            ),
            Player(
                player_id=str(uuid.uuid4()), 
                name="Late WR Rookie", 
                team="KC", 
                position="WR",
                status="Rookie",
                draft_pick=47,
                draft_round=2
            ),
            Player(
                player_id=str(uuid.uuid4()), 
                name="Early TE Rookie", 
                team="SF", 
                position="TE",
                status="Rookie",
                draft_pick=33,
                draft_round=2
            )
        ]
        
        # Add all rookies to database
        for rookie in rookies:
            test_db.add(rookie)
        
        # Add rookie projection templates
        rookie_templates = [
            # QB Templates
            RookieProjectionTemplate(
                template_id=str(uuid.uuid4()),
                position="QB",
                draft_round=1,
                draft_pick_min=1,
                draft_pick_max=10,
                games=16.0,
                snap_share=0.8,
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
                position="QB",
                draft_round=1,
                draft_pick_min=11,
                draft_pick_max=32,
                games=14.0,
                snap_share=0.7,
                pass_attempts=450.0,
                comp_pct=0.62,
                yards_per_att=7.0,
                pass_td_rate=0.042,
                int_rate=0.025,
                rush_att_per_game=4.0,
                rush_yards_per_att=4.8,
                rush_td_per_game=0.2
            ),
            
            # RB Templates
            RookieProjectionTemplate(
                template_id=str(uuid.uuid4()),
                position="RB",
                draft_round=1,
                draft_pick_min=1,
                draft_pick_max=15,
                games=16.0,
                snap_share=0.6,
                rush_att_per_game=14.0,
                rush_yards_per_att=4.4,
                rush_td_per_att=0.035,
                targets_per_game=3.5,
                catch_rate=0.75,
                rec_yards_per_catch=8.5,
                rec_td_per_catch=0.04
            ),
            RookieProjectionTemplate(
                template_id=str(uuid.uuid4()),
                position="RB",
                draft_round=1,
                draft_pick_min=16,
                draft_pick_max=32,
                games=16.0,
                snap_share=0.5,
                rush_att_per_game=11.0,
                rush_yards_per_att=4.2,
                rush_td_per_att=0.03,
                targets_per_game=3.0,
                catch_rate=0.7,
                rec_yards_per_catch=8.0,
                rec_td_per_catch=0.03
            ),
            
            # WR Templates
            RookieProjectionTemplate(
                template_id=str(uuid.uuid4()),
                position="WR",
                draft_round=1,
                draft_pick_min=1,
                draft_pick_max=15,
                games=17.0,
                snap_share=0.75,
                targets_per_game=7.0,
                catch_rate=0.65,
                rec_yards_per_catch=13.0,
                rec_td_per_catch=0.06,
                rush_att_per_game=0.5,
                rush_yards_per_att=8.0,
                rush_td_per_att=0.05
            ),
            RookieProjectionTemplate(
                template_id=str(uuid.uuid4()),
                position="WR",
                draft_round=2,
                draft_pick_min=33,
                draft_pick_max=64,
                games=16.0,
                snap_share=0.6,
                targets_per_game=5.0,
                catch_rate=0.62,
                rec_yards_per_catch=12.5,
                rec_td_per_catch=0.05,
                rush_att_per_game=0.3,
                rush_yards_per_att=7.0,
                rush_td_per_att=0.03
            ),
            
            # TE Templates
            RookieProjectionTemplate(
                template_id=str(uuid.uuid4()),
                position="TE",
                draft_round=2,
                draft_pick_min=33,
                draft_pick_max=64,
                games=16.0,
                snap_share=0.65,
                targets_per_game=4.0,
                catch_rate=0.65,
                rec_yards_per_catch=10.5,
                rec_td_per_catch=0.06
            )
        ]
        
        for template in rookie_templates:
            test_db.add(template)
        
        test_db.commit()
        
        return {
            "teams": teams,
            "rookies": rookies,
            "current_season": current_season
        }
    
    @pytest.mark.asyncio
    async def test_top_qb_rookie_projection(self, rookie_service, setup_rookie_data, test_db):
        """Test creating a projection for a top QB rookie."""
        # Get a top QB rookie
        qb_rookie = next(r for r in setup_rookie_data["rookies"] if r.position == "QB" and r.draft_pick == 1)
        
        # Create projection
        projection = await rookie_service.create_draft_based_projection(
            player_id=qb_rookie.player_id,
            draft_position=qb_rookie.draft_pick,
            season=setup_rookie_data["current_season"]
        )
        
        # Verify projection exists
        assert projection is not None
        assert projection.player_id == qb_rookie.player_id
        assert projection.season == setup_rookie_data["current_season"]
        
        # QB-specific stats
        assert projection.games > 0
        assert projection.pass_attempts > 0
        assert projection.pass_yards > 0
        assert projection.pass_td > 0
        assert projection.interceptions > 0
        assert projection.carries > 0
        assert projection.rush_yards > 0
        assert projection.rush_td > 0
        
        # Fantasy points
        assert projection.half_ppr > 0
        
        # Early draft pick should have better projection than later picks
        assert projection.pass_attempts >= 450  # Based on template values
    
    @pytest.mark.asyncio
    async def test_mid_round_qb_rookie_projection(self, rookie_service, setup_rookie_data, test_db):
        """Test creating a projection for a mid-round QB rookie."""
        # Get a mid-round QB rookie
        qb_rookie = next(r for r in setup_rookie_data["rookies"] if r.position == "QB" and r.draft_pick == 15)
        
        # Create projection
        projection = await rookie_service.create_draft_based_projection(
            player_id=qb_rookie.player_id,
            draft_position=qb_rookie.draft_pick,
            season=setup_rookie_data["current_season"]
        )
        
        # Verify projection exists and is appropriate
        assert projection is not None
        assert projection.player_id == qb_rookie.player_id
        
        # Mid-round QB should have reduced stats compared to early picks
        top_qb = next(r for r in setup_rookie_data["rookies"] if r.position == "QB" and r.draft_pick == 1)
        top_qb_proj = test_db.query(Projection).filter(
            Projection.player_id == top_qb.player_id,
            Projection.season == setup_rookie_data["current_season"]
        ).first()
        
        # Should be somewhat lower than top pick, but not by huge margin
        assert projection.pass_attempts <= top_qb_proj.pass_attempts
        assert projection.pass_yards <= top_qb_proj.pass_yards
    
    @pytest.mark.asyncio
    async def test_top_rb_rookie_projection(self, rookie_service, setup_rookie_data, test_db):
        """Test creating a projection for a top RB rookie."""
        # Get a top RB rookie
        rb_rookie = next(r for r in setup_rookie_data["rookies"] if r.position == "RB" and r.draft_pick == 5)
        
        # Create projection
        projection = await rookie_service.create_draft_based_projection(
            player_id=rb_rookie.player_id,
            draft_position=rb_rookie.draft_pick,
            season=setup_rookie_data["current_season"]
        )
        
        # Verify projection exists
        assert projection is not None
        assert projection.player_id == rb_rookie.player_id
        
        # RB-specific stats
        assert projection.games > 0
        assert projection.carries > 0
        assert projection.rush_yards > 0
        assert projection.rush_td > 0
        assert projection.targets > 0
        assert projection.receptions > 0
        assert projection.rec_yards > 0
        
        # Fantasy points
        assert projection.half_ppr > 0
    
    @pytest.mark.asyncio
    async def test_all_rookie_projections(self, rookie_service, setup_rookie_data, test_db):
        """Test creating projections for all rookies."""
        # Create projections for all rookies
        projections = []
        for rookie in setup_rookie_data["rookies"]:
            projection = await rookie_service.create_draft_based_projection(
                player_id=rookie.player_id,
                draft_position=rookie.draft_pick,
                season=setup_rookie_data["current_season"]
            )
            assert projection is not None
            projections.append(projection)
        
        # Verify we have the right number of projections
        assert len(projections) == len(setup_rookie_data["rookies"])
        
        # Verify positional patterns
        qb_projections = [p for p in projections 
            if test_db.query(Player).filter(Player.player_id == p.player_id).first().position == "QB"]
        rb_projections = [p for p in projections 
            if test_db.query(Player).filter(Player.player_id == p.player_id).first().position == "RB"]
        wr_projections = [p for p in projections 
            if test_db.query(Player).filter(Player.player_id == p.player_id).first().position == "WR"]
        te_projections = [p for p in projections 
            if test_db.query(Player).filter(Player.player_id == p.player_id).first().position == "TE"]
        
        # Verify all position groups have appropriate projections
        assert len(qb_projections) == 3
        assert len(rb_projections) == 2
        assert len(wr_projections) == 2
        assert len(te_projections) == 1
        
        # Verify draft position impact - earlier picks should have better projections
        if len(qb_projections) >= 2:
            qb_projs_sorted = sorted(qb_projections, 
                                     key=lambda p: test_db.query(Player).filter(Player.player_id == p.player_id).first().draft_pick)
            # First pick should have better projection than later picks
            assert qb_projs_sorted[0].half_ppr >= qb_projs_sorted[1].half_ppr
        
        if len(rb_projections) >= 2:
            rb_projs_sorted = sorted(rb_projections, 
                                     key=lambda p: test_db.query(Player).filter(Player.player_id == p.player_id).first().draft_pick)
            # Earlier pick should have better projection
            assert rb_projs_sorted[0].half_ppr >= rb_projs_sorted[1].half_ppr
    
    @pytest.mark.asyncio
    async def test_fantasy_points_calculation(self, rookie_service, setup_rookie_data, test_db):
        """Test that fantasy points are calculated correctly for rookies."""
        # Create projections for all rookies
        for rookie in setup_rookie_data["rookies"]:
            projection = await rookie_service.create_draft_based_projection(
                player_id=rookie.player_id,
                draft_position=rookie.draft_pick,
                season=setup_rookie_data["current_season"]
            )
            
            # Verify fantasy points are calculated
            assert projection.half_ppr > 0
            
            # Different positions should have different point ranges
            player = test_db.query(Player).filter(Player.player_id == rookie.player_id).first()
            if player.position == "QB":
                # QBs typically have highest point totals
                assert projection.half_ppr > 150
            elif player.position == "RB" and player.draft_pick < 20:
                # Early RBs should have good point totals
                assert projection.half_ppr > 100