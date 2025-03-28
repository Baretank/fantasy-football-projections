import pytest
import uuid
from backend.services.projection_service import ProjectionService
from backend.database.models import TeamStat, Projection, Player

class TestProjectionService:
    @pytest.fixture(scope="function")
    def service(self, test_db):
        """Create ProjectionService instance for testing."""
        return ProjectionService(test_db)

    @pytest.fixture(scope="function")
    def team_stats_2024(self, test_db):
        """Ensure 2024 team stats exist for testing."""
        # Add 2024 stats if not present
        kc_stats = test_db.query(TeamStat).filter(
            TeamStat.team == "KC",
            TeamStat.season == 2024
        ).first()

        if not kc_stats:
            kc_stats = TeamStat(
                team_stat_id=str(uuid.uuid4()),
                team="KC",
                season=2024,
                plays=1090,
                pass_percentage=0.63,
                pass_attempts=590,
                pass_yards=4250,
                pass_td=30,
                pass_td_rate=0.0508,
                rush_attempts=410,
                rush_yards=1950,
                rush_td=19,
                carries=410,
                rush_yards_per_carry=4.76,
                targets=590,
                receptions=405,
                rec_yards=4250,
                rec_td=30,
                rank=1
            )
            test_db.add(kc_stats)
            test_db.commit()
        return kc_stats

    @pytest.mark.asyncio
    async def test_projection_adjustments(self, service, sample_players, team_stats_2024):
        """Test applying adjustments to projections."""
        mahomes_id = sample_players["ids"]["Patrick Mahomes"]

        # First create base projection
        base_proj = await service.create_base_projection(
            player_id=mahomes_id,
            season=2024
        )

        assert base_proj is not None, "Base projection creation failed"

        # Apply adjustments
        adjustments = {
            'pass_volume': 1.05,  # 5% increase in passing volume
            'td_rate': 1.10,      # 10% increase in TD rate
            'int_rate': 0.90      # 10% decrease in interceptions
        }

        updated_proj = await service.update_projection(
            projection_id=base_proj.projection_id,
            adjustments=adjustments
        )

        print("\nTest projection_adjustments:")
        print("Original vs Adjusted Projections:")
        print(f"Pass Attempts: {base_proj.pass_attempts} -> {updated_proj.pass_attempts}")
        print(f"Pass TDs: {base_proj.pass_td} -> {updated_proj.pass_td}")
        print(f"Fantasy Points: {base_proj.half_ppr} -> {updated_proj.half_ppr}")

        # Verify adjustments
        assert updated_proj.pass_attempts > base_proj.pass_attempts
        assert updated_proj.pass_td > base_proj.pass_td
        assert updated_proj.half_ppr != base_proj.half_ppr

    @pytest.mark.asyncio
    async def test_team_level_adjustments(self, service, sample_players, team_stats_2024):
        """Test applying team-level adjustments to projections."""
        # Add a method to get players by team to the service
        async def get_players_by_team(team):
            return service.db.query(Player).filter(Player.team == team).all()

        # Create base projections for KC players first
        kc_players = await get_players_by_team("KC")
        
        for player in kc_players:
            proj = await service.create_base_projection(
                player_id=player.player_id,
                season=2024
            )
            assert proj is not None, f"Failed to create projection for {player.name}"

        # Apply team-level adjustments
        team_adjustments = {
            'pass_volume': 1.08,    # 8% increase in passing
            'scoring_rate': 1.05    # 5% increase in scoring
        }

        updated_projs = await service.apply_team_adjustments(
            team="KC",
            season=2024,
            adjustments=team_adjustments
        )

        print("\nTest team_level_adjustments:")
        print("Updated KC Projections:")
        for proj in updated_projs:
            print(f"{proj.player.name}:")
            if proj.pass_attempts:
                print(f"- Pass Attempts: {proj.pass_attempts}")
            if proj.targets:
                print(f"- Targets: {proj.targets}")
            print(f"- Fantasy Points: {proj.half_ppr}")

        assert len(updated_projs) > 0
        for proj in updated_projs:
            assert proj.half_ppr > 0