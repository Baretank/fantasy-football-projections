import pytest
import uuid
from datetime import datetime
from sqlalchemy import and_
from typing import Dict, List, Optional

from backend.services.team_stat_service import TeamStatService
from backend.services.projection_service import ProjectionService
from backend.database.models import Player, TeamStat, Projection


class TestTeamAdjustments:
    @pytest.fixture(scope="function")
    def services(self, test_db):
        """Create services needed for testing."""
        return {"team_stat": TeamStatService(test_db), "projection": ProjectionService(test_db)}

    @pytest.fixture(scope="function")
    def setup_team_data(self, test_db):
        """Set up minimal test data for team adjustment testing."""
        # Create test team
        team = "KC"

        # Current season
        current_season = datetime.now().year

        # Create players for the team
        players = [
            Player(player_id=str(uuid.uuid4()), name="KC QB1", team=team, position="QB"),
            Player(player_id=str(uuid.uuid4()), name="KC RB1", team=team, position="RB"),
            Player(player_id=str(uuid.uuid4()), name="KC RB2", team=team, position="RB"),
            Player(player_id=str(uuid.uuid4()), name="KC WR1", team=team, position="WR"),
            Player(player_id=str(uuid.uuid4()), name="KC WR2", team=team, position="WR"),
            Player(player_id=str(uuid.uuid4()), name="KC WR3", team=team, position="WR"),
            Player(player_id=str(uuid.uuid4()), name="KC TE1", team=team, position="TE"),
        ]

        # Add players to database
        for player in players:
            test_db.add(player)

        # Create team stats
        original_team_stat = TeamStat(
            team_stat_id=str(uuid.uuid4()),
            team=team,
            season=current_season,
            plays=1000,
            pass_percentage=0.60,  # 60% pass, 40% run
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
            rank=1,
        )

        test_db.add(original_team_stat)

        # Create baseline projections for each player
        projections = []
        for player in players:
            if player.position == "QB":
                proj = Projection(
                    projection_id=str(uuid.uuid4()),
                    player_id=player.player_id,
                    season=current_season,
                    games=17,
                    completions=390,
                    pass_attempts=600,
                    pass_yards=4200,
                    pass_td=30,
                    interceptions=10,
                    rush_attempts=50,
                    rush_yards=250,
                    rush_td=2,
                    half_ppr=300,
                )
            elif player.position == "RB" and player.name.endswith("RB1"):
                proj = Projection(
                    projection_id=str(uuid.uuid4()),
                    player_id=player.player_id,
                    season=current_season,
                    games=16,
                    rush_attempts=250,
                    rush_yards=1100,
                    rush_td=9,
                    targets=60,
                    receptions=50,
                    rec_yards=400,
                    rec_td=2,
                    half_ppr=225,
                )
            elif player.position == "RB" and player.name.endswith("RB2"):
                proj = Projection(
                    projection_id=str(uuid.uuid4()),
                    player_id=player.player_id,
                    season=current_season,
                    games=16,
                    rush_attempts=150,
                    rush_yards=700,
                    rush_td=6,
                    targets=30,
                    receptions=24,
                    rec_yards=200,
                    rec_td=1,
                    half_ppr=142,
                )
            elif player.position == "WR" and player.name.endswith("WR1"):
                proj = Projection(
                    projection_id=str(uuid.uuid4()),
                    player_id=player.player_id,
                    season=current_season,
                    games=17,
                    targets=150,
                    receptions=100,
                    rec_yards=1400,
                    rec_td=10,
                    rush_attempts=10,
                    rush_yards=60,
                    rush_td=0,
                    half_ppr=250,
                )
            elif player.position == "WR" and player.name.endswith("WR2"):
                proj = Projection(
                    projection_id=str(uuid.uuid4()),
                    player_id=player.player_id,
                    season=current_season,
                    games=17,
                    targets=120,
                    receptions=80,
                    rec_yards=1000,
                    rec_td=7,
                    rush_attempts=5,
                    rush_yards=25,
                    rush_td=0,
                    half_ppr=182,
                )
            elif player.position == "WR" and player.name.endswith("WR3"):
                proj = Projection(
                    projection_id=str(uuid.uuid4()),
                    player_id=player.player_id,
                    season=current_season,
                    games=17,
                    targets=80,
                    receptions=50,
                    rec_yards=600,
                    rec_td=5,
                    rush_attempts=0,
                    rush_yards=0,
                    rush_td=0,
                    half_ppr=115,
                )
            elif player.position == "TE":
                proj = Projection(
                    projection_id=str(uuid.uuid4()),
                    player_id=player.player_id,
                    season=current_season,
                    games=16,
                    targets=100,
                    receptions=75,
                    rec_yards=800,
                    rec_td=8,
                    half_ppr=165.5,
                )

            projections.append(proj)
            test_db.add(proj)

        test_db.commit()

        return {
            "team": team,
            "players": players,
            "current_season": current_season,
            "original_team_stat": original_team_stat,
            "original_projections": projections,
        }

    @pytest.mark.asyncio
    async def test_pass_volume_adjustment(self, services, setup_team_data, test_db):
        """Test adjusting a team's passing volume."""
        # Define the adjustment - 10% increase in pass volume
        adjustments = {"pass_volume": 1.1}  # 10% increase

        # Get players by position
        qb_player = next(p for p in setup_team_data["players"] if p.position == "QB")
        wr1_player = next(p for p in setup_team_data["players"] if p.name.endswith("WR1"))

        # Get original projections from database
        qb_proj = (
            test_db.query(Projection)
            .filter(
                Projection.player_id == qb_player.player_id,
                Projection.season == setup_team_data["current_season"],
            )
            .first()
        )

        wr1_proj = (
            test_db.query(Projection)
            .filter(
                Projection.player_id == wr1_player.player_id,
                Projection.season == setup_team_data["current_season"],
            )
            .first()
        )

        # Store original values before they get changed
        original_qb_pass_attempts = qb_proj.pass_attempts
        original_qb_pass_yards = qb_proj.pass_yards
        original_wr1_targets = wr1_proj.targets
        original_wr1_rec_yards = wr1_proj.rec_yards
        original_qb_half_ppr = qb_proj.half_ppr
        original_wr1_half_ppr = wr1_proj.half_ppr

        # Apply team adjustments
        updated_projections = await services["team_stat"].apply_team_adjustments(
            team=setup_team_data["team"],
            season=setup_team_data["current_season"],
            adjustments=adjustments,
        )

        # Verify the right projections were returned
        assert len(updated_projections) > 0
        assert all(p.player_id for p in updated_projections)

        # Get updated projections from database
        updated_qb_proj = (
            test_db.query(Projection)
            .filter(
                Projection.player_id == qb_player.player_id,
                Projection.season == setup_team_data["current_season"],
            )
            .first()
        )

        updated_wr1_proj = (
            test_db.query(Projection)
            .filter(
                Projection.player_id == wr1_player.player_id,
                Projection.season == setup_team_data["current_season"],
            )
            .first()
        )

        # Verify QB passing stats increased by approximately 10%
        pass_att_increase = updated_qb_proj.pass_attempts / original_qb_pass_attempts
        assert 1.05 <= pass_att_increase <= 1.15  # Allow for rounding/adjustments

        pass_yards_increase = updated_qb_proj.pass_yards / original_qb_pass_yards
        assert 1.05 <= pass_yards_increase <= 1.15

        # Verify WR receiving stats increased
        targets_increase = updated_wr1_proj.targets / original_wr1_targets
        assert 1.05 <= targets_increase <= 1.15

        rec_yards_increase = updated_wr1_proj.rec_yards / original_wr1_rec_yards
        assert 1.05 <= rec_yards_increase <= 1.15

        # Fantasy points should increase too
        assert updated_qb_proj.half_ppr > original_qb_half_ppr
        assert updated_wr1_proj.half_ppr > original_wr1_half_ppr

    @pytest.mark.asyncio
    async def test_scoring_rate_adjustment(self, services, setup_team_data, test_db):
        """Test adjusting a team's TD scoring rate."""
        # Define the adjustment - 20% increase in TD scoring rate
        adjustments = {"scoring_rate": 1.2}  # 20% increase

        # Get original projections
        qb_player = next(p for p in setup_team_data["players"] if p.position == "QB")
        rb1_player = next(p for p in setup_team_data["players"] if p.name.endswith("RB1"))

        qb_proj = (
            test_db.query(Projection)
            .filter(
                Projection.player_id == qb_player.player_id,
                Projection.season == setup_team_data["current_season"],
            )
            .first()
        )

        rb1_proj = (
            test_db.query(Projection)
            .filter(
                Projection.player_id == rb1_player.player_id,
                Projection.season == setup_team_data["current_season"],
            )
            .first()
        )

        # Store original values before they get changed
        original_qb_pass_td = qb_proj.pass_td
        original_rb1_rush_td = rb1_proj.rush_td
        original_qb_half_ppr = qb_proj.half_ppr
        original_rb1_half_ppr = rb1_proj.half_ppr

        # Apply team adjustments
        updated_projections = await services["team_stat"].apply_team_adjustments(
            team=setup_team_data["team"],
            season=setup_team_data["current_season"],
            adjustments=adjustments,
        )

        # Verify the right projections were returned
        assert len(updated_projections) > 0

        # Get updated projections from database
        updated_qb_proj = (
            test_db.query(Projection)
            .filter(
                Projection.player_id == qb_player.player_id,
                Projection.season == setup_team_data["current_season"],
            )
            .first()
        )

        updated_rb1_proj = (
            test_db.query(Projection)
            .filter(
                Projection.player_id == rb1_player.player_id,
                Projection.season == setup_team_data["current_season"],
            )
            .first()
        )

        # Verify QB TD stats increased by approximately 20%
        pass_td_increase = updated_qb_proj.pass_td / original_qb_pass_td
        assert 1.15 <= pass_td_increase <= 1.25  # Allow for rounding/adjustments

        # Verify RB TD stats increased
        rush_td_increase = updated_rb1_proj.rush_td / original_rb1_rush_td
        assert 1.15 <= rush_td_increase <= 1.25

        # Fantasy points should increase too
        assert updated_qb_proj.half_ppr > original_qb_half_ppr
        assert updated_rb1_proj.half_ppr > original_rb1_half_ppr

    @pytest.mark.asyncio
    async def test_multiple_adjustments(self, services, setup_team_data, test_db):
        """Test applying multiple team adjustments at once."""
        # Define multiple adjustments
        adjustments = {
            "pass_volume": 1.1,  # 10% increase in passing
            "scoring_rate": 1.15,  # 15% increase in TDs
            "rush_volume": 0.9,  # 10% decrease in rushing
        }

        # Get original projections and store their values
        qb_player = next(p for p in setup_team_data["players"] if p.position == "QB")
        rb1_player = next(p for p in setup_team_data["players"] if p.name.endswith("RB1"))

        qb_proj = (
            test_db.query(Projection)
            .filter(
                Projection.player_id == qb_player.player_id,
                Projection.season == setup_team_data["current_season"],
            )
            .first()
        )

        rb1_proj = (
            test_db.query(Projection)
            .filter(
                Projection.player_id == rb1_player.player_id,
                Projection.season == setup_team_data["current_season"],
            )
            .first()
        )

        # Store original values before they get changed
        original_qb_pass_attempts = qb_proj.pass_attempts
        original_qb_pass_yards = qb_proj.pass_yards
        original_qb_pass_td = qb_proj.pass_td

        original_rb1_rush_attempts = rb1_proj.rush_attempts
        original_rb1_rush_yards = rb1_proj.rush_yards
        original_rb1_rush_td = rb1_proj.rush_td

        # Apply team adjustments
        updated_projections = await services["team_stat"].apply_team_adjustments(
            team=setup_team_data["team"],
            season=setup_team_data["current_season"],
            adjustments=adjustments,
        )

        # Get updated projections from database
        updated_qb_proj = (
            test_db.query(Projection)
            .filter(
                Projection.player_id == qb_player.player_id,
                Projection.season == setup_team_data["current_season"],
            )
            .first()
        )

        updated_rb1_proj = (
            test_db.query(Projection)
            .filter(
                Projection.player_id == rb1_player.player_id,
                Projection.season == setup_team_data["current_season"],
            )
            .first()
        )

        # QB passing should increase, TDs should increase
        assert updated_qb_proj.pass_attempts > original_qb_pass_attempts
        assert updated_qb_proj.pass_yards > original_qb_pass_yards
        assert updated_qb_proj.pass_td > original_qb_pass_td

        # RB rushing should decrease, TDs should still increase
        assert updated_rb1_proj.rush_attempts < original_rb1_rush_attempts
        assert updated_rb1_proj.rush_yards < original_rb1_rush_yards
        assert (
            updated_rb1_proj.rush_td > original_rb1_rush_td
        )  # TD rate increase outweighs volume decrease

    @pytest.mark.asyncio
    async def test_player_share_adjustments(self, services, setup_team_data, test_db):
        """Test adjusting individual player shares within team adjustments."""
        # Define team-level adjustments
        adjustments = {"pass_volume": 1.1}  # 10% increase in passing

        # Define player-specific share adjustments
        player_shares = {}

        # Find our WR1 and WR2
        wr1 = next(p for p in setup_team_data["players"] if p.name.endswith("WR1"))
        wr2 = next(p for p in setup_team_data["players"] if p.name.endswith("WR2"))

        # Increase WR1's target share, decrease WR2's
        player_shares[wr1.player_id] = {"target_share": 1.2}  # 20% more targets for WR1
        player_shares[wr2.player_id] = {"target_share": 0.8}  # 20% fewer targets for WR2

        # Get original projections from database to ensure we have separate objects
        wr1_proj = (
            test_db.query(Projection)
            .filter(
                Projection.player_id == wr1.player_id,
                Projection.season == setup_team_data["current_season"],
            )
            .first()
        )

        wr2_proj = (
            test_db.query(Projection)
            .filter(
                Projection.player_id == wr2.player_id,
                Projection.season == setup_team_data["current_season"],
            )
            .first()
        )

        # Store original values
        original_wr1_targets = wr1_proj.targets
        original_wr1_half_ppr = wr1_proj.half_ppr
        original_wr2_targets = wr2_proj.targets
        original_wr2_half_ppr = wr2_proj.half_ppr

        # Apply team adjustments with player shares
        updated_projections = await services["team_stat"].apply_team_adjustments(
            team=setup_team_data["team"],
            season=setup_team_data["current_season"],
            adjustments=adjustments,
            player_shares=player_shares,
        )

        # Get updated projections from database
        updated_wr1_proj = (
            test_db.query(Projection)
            .filter(
                Projection.player_id == wr1.player_id,
                Projection.season == setup_team_data["current_season"],
            )
            .first()
        )

        updated_wr2_proj = (
            test_db.query(Projection)
            .filter(
                Projection.player_id == wr2.player_id,
                Projection.season == setup_team_data["current_season"],
            )
            .first()
        )

        # WR1 should see a larger increase in targets (team pass volume * player share increase)
        # Expected increase is roughly 1.1 * 1.2 = 1.32
        wr1_target_increase = updated_wr1_proj.targets / original_wr1_targets
        assert 1.25 <= wr1_target_increase <= 1.35

        # WR2 should see a decrease despite team pass volume increase
        # Expected change is roughly 1.1 * 0.8 = 0.88
        wr2_target_change = updated_wr2_proj.targets / original_wr2_targets
        assert 0.85 <= wr2_target_change <= 0.95

        # Fantasy points should reflect these changes
        assert updated_wr1_proj.half_ppr > original_wr1_half_ppr
        assert updated_wr2_proj.half_ppr < original_wr2_half_ppr

    @pytest.mark.asyncio
    async def test_apply_team_stats_directly(self, services, setup_team_data, test_db):
        """Test using the alternative apply_team_stats_directly method."""
        # Get original team stats
        original_stats = setup_team_data["original_team_stat"]

        # Create new team stats with adjustments
        new_stats = TeamStat(
            team_stat_id=str(uuid.uuid4()),
            team=original_stats.team,
            season=original_stats.season,
            plays=original_stats.plays,
            pass_percentage=0.65,  # Increased from 0.60
            pass_attempts=650,  # Increased from 600
            pass_yards=4550,  # Increased from 4200
            pass_td=35,  # Increased from 30
            pass_td_rate=0.054,  # Increased from 0.05
            rush_attempts=350,  # Decreased from 400
            rush_yards=1650,  # Decreased from 1800
            rush_td=14,  # Slightly decreased from 15
            rush_yards_per_carry=4.7,  # Increased from 4.5
            targets=650,  # Increased from 600
            receptions=422,  # Increased from 390
            rec_yards=4550,  # Increased from 4200
            rec_td=35,  # Increased from 30
            rank=1,
        )

        # Get players by position
        qb = next(p for p in setup_team_data["players"] if p.position == "QB")
        rb1 = next(p for p in setup_team_data["players"] if p.name.endswith("RB1"))

        # Get original projections from database to ensure we have separate copies
        qb_proj = (
            test_db.query(Projection)
            .filter(
                Projection.player_id == qb.player_id,
                Projection.season == setup_team_data["current_season"],
            )
            .first()
        )

        rb1_proj = (
            test_db.query(Projection)
            .filter(
                Projection.player_id == rb1.player_id,
                Projection.season == setup_team_data["current_season"],
            )
            .first()
        )

        # Store original values
        original_qb_pass_attempts = qb_proj.pass_attempts
        original_qb_pass_yards = qb_proj.pass_yards
        original_qb_pass_td = qb_proj.pass_td
        original_rb1_rush_attempts = rb1_proj.rush_attempts

        # Create a list of all projections to pass to the service
        original_projections = (
            test_db.query(Projection)
            .filter(
                Projection.season == setup_team_data["current_season"],
                Projection.player_id.in_([p.player_id for p in setup_team_data["players"]]),
            )
            .all()
        )

        # Apply team stats directly
        updated_projections = await services["team_stat"].apply_team_stats_directly(
            original_stats=original_stats, new_stats=new_stats, players=original_projections
        )

        # Verify the right projections were returned
        assert len(updated_projections) > 0

        # Get updated projections from database
        updated_qb_proj = (
            test_db.query(Projection)
            .filter(
                Projection.player_id == qb.player_id,
                Projection.season == setup_team_data["current_season"],
            )
            .first()
        )

        updated_rb1_proj = (
            test_db.query(Projection)
            .filter(
                Projection.player_id == rb1.player_id,
                Projection.season == setup_team_data["current_season"],
            )
            .first()
        )

        # QB passing attempts should increase proportionally to team pass_attempts increase
        expected_increase = new_stats.pass_attempts / original_stats.pass_attempts
        actual_increase = updated_qb_proj.pass_attempts / original_qb_pass_attempts
        assert abs(actual_increase - expected_increase) < 0.05  # Within 5% of expected

        # QB passing yards should also increase
        yards_increase = updated_qb_proj.pass_yards / original_qb_pass_yards
        assert abs(yards_increase - expected_increase) < 0.05  # Within 5% of expected

        # TD increase should match or exceed the yardage increase due to improved TD rate
        td_increase = updated_qb_proj.pass_td / original_qb_pass_td
        assert td_increase >= yards_increase

        # RB rush_attempts should decrease proportionally to team rush_attempts decrease
        expected_rush_change = new_stats.rush_attempts / original_stats.rush_attempts
        actual_rush_change = updated_rb1_proj.rush_attempts / original_rb1_rush_attempts
        assert abs(actual_rush_change - expected_rush_change) < 0.05  # Within 5% of expected
