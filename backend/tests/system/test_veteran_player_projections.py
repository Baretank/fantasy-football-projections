import pytest
import uuid
from datetime import datetime
from sqlalchemy import and_

from backend.services.projection_service import ProjectionService
from backend.database.models import Player, BaseStat, TeamStat, Projection

class TestVeteranPlayerProjections:
    @pytest.fixture(scope="function")
    def projection_service(self, test_db):
        """Create projection service for testing."""
        return ProjectionService(test_db)
    
    @pytest.fixture(scope="function")
    def setup_veteran_data(self, test_db):
        """Set up minimal test data for veteran player projections."""
        # Create test teams
        teams = ["KC", "SF", "BUF"]
        
        # Create basic players (veterans)
        players = []
        for team in teams:
            players.extend([
                Player(player_id=str(uuid.uuid4()), name=f"{team} QB", team=team, position="QB"),
                Player(player_id=str(uuid.uuid4()), name=f"{team} RB1", team=team, position="RB"),
                Player(player_id=str(uuid.uuid4()), name=f"{team} WR1", team=team, position="WR"),
                Player(player_id=str(uuid.uuid4()), name=f"{team} TE", team=team, position="TE")
            ])
        
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
        
        test_db.commit()
        
        return {
            "teams": teams,
            "players": players,
            "previous_season": previous_season,
            "current_season": current_season
        }
    
    @pytest.mark.asyncio
    async def test_qb_projection_creation(self, projection_service, setup_veteran_data, test_db):
        """Test creating a projection for a QB."""
        # Get a QB player
        qb_player = next(p for p in setup_veteran_data["players"] if p.position == "QB")
        
        # Create projection
        projection = await projection_service.create_base_projection(
            player_id=qb_player.player_id,
            season=setup_veteran_data["current_season"]
        )
        
        # Verify projection exists
        assert projection is not None
        assert projection.player_id == qb_player.player_id
        assert projection.season == setup_veteran_data["current_season"]
        
        # QB-specific stats
        assert projection.pass_attempts > 0
        assert projection.pass_yards > 0
        assert projection.pass_td > 0
        
        # Fantasy points
        assert projection.half_ppr > 200
    
    @pytest.mark.asyncio
    async def test_rb_projection_creation(self, projection_service, setup_veteran_data, test_db):
        """Test creating a projection for a RB."""
        # Get a RB player
        rb_player = next(p for p in setup_veteran_data["players"] if p.position == "RB")
        
        # Create projection
        projection = await projection_service.create_base_projection(
            player_id=rb_player.player_id,
            season=setup_veteran_data["current_season"]
        )
        
        # Verify projection exists
        assert projection is not None
        assert projection.player_id == rb_player.player_id
        assert projection.season == setup_veteran_data["current_season"]
        
        # RB-specific stats
        assert projection.rush_attempts > 0
        assert projection.rush_yards > 0
        assert projection.rush_td > 0
        assert projection.targets > 0
        
        # Fantasy points
        assert projection.half_ppr > 100
    
    @pytest.mark.asyncio
    async def test_wr_projection_creation(self, projection_service, setup_veteran_data, test_db):
        """Test creating a projection for a WR."""
        # Get a WR player
        wr_player = next(p for p in setup_veteran_data["players"] if p.position == "WR")
        
        # Create projection
        projection = await projection_service.create_base_projection(
            player_id=wr_player.player_id,
            season=setup_veteran_data["current_season"]
        )
        
        # Verify projection exists
        assert projection is not None
        assert projection.player_id == wr_player.player_id
        assert projection.season == setup_veteran_data["current_season"]
        
        # WR-specific stats
        assert projection.targets > 0
        assert projection.receptions > 0
        assert projection.rec_yards > 0
        assert projection.rec_td > 0
        
        # Fantasy points
        assert projection.half_ppr > 100
    
    @pytest.mark.asyncio
    async def test_te_projection_creation(self, projection_service, setup_veteran_data, test_db):
        """Test creating a projection for a TE."""
        # Get a TE player
        te_player = next(p for p in setup_veteran_data["players"] if p.position == "TE")
        
        # Create projection
        projection = await projection_service.create_base_projection(
            player_id=te_player.player_id,
            season=setup_veteran_data["current_season"]
        )
        
        # Verify projection exists
        assert projection is not None
        assert projection.player_id == te_player.player_id
        assert projection.season == setup_veteran_data["current_season"]
        
        # TE-specific stats
        assert projection.targets > 0
        assert projection.receptions > 0
        assert projection.rec_yards > 0
        assert projection.rec_td > 0
        
        # Fantasy points
        assert projection.half_ppr > 70
    
    @pytest.mark.asyncio
    async def test_all_veteran_projections(self, projection_service, setup_veteran_data, test_db):
        """Test creating projections for all veteran players at once."""
        # Create projections for all players
        projections = []
        for player in setup_veteran_data["players"]:
            projection = await projection_service.create_base_projection(
                player_id=player.player_id,
                season=setup_veteran_data["current_season"]
            )
            assert projection is not None
            projections.append(projection)
        
        # Verify we have the right number of projections
        assert len(projections) == len(setup_veteran_data["players"])
        
        # Get projections from database to verify persistence
        db_projections = test_db.query(Projection).filter(
            Projection.season == setup_veteran_data["current_season"]
        ).all()
        
        assert len(db_projections) == len(setup_veteran_data["players"])
        
        # Verify positional scoring patterns are reasonable
        for projection in db_projections:
            player = test_db.query(Player).filter(Player.player_id == projection.player_id).first()
            
            # Different fantasy expectations per position
            if player.position == "QB":
                assert projection.half_ppr > 200
            elif player.position == "RB":
                assert projection.half_ppr > 100
            elif player.position == "WR":
                assert projection.half_ppr > 100
            elif player.position == "TE":
                assert projection.half_ppr > 70