import pytest
import uuid
import numpy as np
from backend.services.projection_service import ProjectionService
from backend.database.models import TeamStat, Projection, Player, BaseStat

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

    @pytest.fixture(scope="function")
    def sample_base_stats(self, test_db, sample_players):
        """Create sample base stats for testing projection creation."""
        mahomes_id = sample_players["ids"]["Patrick Mahomes"]
        
        # Add past season stats for Mahomes
        base_stats = [
            BaseStat(
                stat_id=str(uuid.uuid4()),
                player_id=mahomes_id,
                season=2023,
                games=17,
                pass_attempts=580,
                completions=401,
                pass_yards=4183,
                pass_td=27,
                interceptions=14,
                
                carries=75,
                rush_yards=389,
                rush_td=4,
                
                targets=0,  # QB doesn't have receiving stats
                receptions=0,
                rec_yards=0,
                rec_td=0
            ),
            BaseStat(
                stat_id=str(uuid.uuid4()),
                player_id=mahomes_id,
                season=2022,
                games=17,
                pass_attempts=648,
                completions=435,
                pass_yards=5250,
                pass_td=41,
                interceptions=12,
                
                carries=61,
                rush_yards=358,
                rush_td=4,
                
                targets=0,
                receptions=0,
                rec_yards=0,
                rec_td=0
            )
        ]
        
        for stat in base_stats:
            test_db.add(stat)
        test_db.commit()
        
        # Add stats for other players too
        kelce_id = sample_players["ids"]["Travis Kelce"]
        kelce_stats = BaseStat(
            stat_id=str(uuid.uuid4()),
            player_id=kelce_id,
            season=2023,
            games=15,
            
            targets=121,
            receptions=93,
            rec_yards=984,
            rec_td=5,
            
            # No QB or rushing stats
            pass_attempts=0,
            completions=0,
            pass_yards=0,
            pass_td=0,
            interceptions=0,
            carries=0,
            rush_yards=0,
            rush_td=0
        )
        test_db.add(kelce_stats)
        test_db.commit()
        
        return base_stats

    @pytest.mark.asyncio
    async def test_create_base_projection(self, service, sample_players, team_stats_2024, sample_base_stats):
        """Test creating base projections from historical data."""
        mahomes_id = sample_players["ids"]["Patrick Mahomes"]
        
        # Create base projection
        base_proj = await service.create_base_projection(
            player_id=mahomes_id,
            season=2024
        )
        
        assert base_proj is not None, "Base projection creation failed"
        
        # Verify projection uses historical averages
        assert base_proj.pass_attempts > 0
        assert base_proj.pass_yards > 0
        assert base_proj.pass_td > 0
        
        # Should be somewhat between 2022 and 2023 stats
        assert 580 <= base_proj.pass_attempts <= 648 or 648 <= base_proj.pass_attempts <= 580
        
        # Check calculation of fantasy points
        assert base_proj.half_ppr > 0
        
        # Check pass efficiency metrics
        assert base_proj.yards_per_att > 0
        assert base_proj.comp_pct > 0
        assert base_proj.pass_td_rate > 0

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
        
        # Verify specific adjustment factors were applied correctly
        assert updated_proj.pass_attempts == pytest.approx(base_proj.pass_attempts * 1.05, rel=0.01)
        
        # TD rate adjustment should increase TDs
        expected_td_increase = base_proj.pass_td * 1.10 / base_proj.pass_td
        assert updated_proj.pass_td == pytest.approx(base_proj.pass_td * expected_td_increase, rel=0.01)
        
        # INT rate adjustment should decrease INTs
        if base_proj.interceptions:
            expected_int_decrease = base_proj.interceptions * 0.90 / base_proj.interceptions
            assert updated_proj.interceptions == pytest.approx(base_proj.interceptions * expected_int_decrease, rel=0.01)

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
        
        # Verify QB pass volume increased
        qb_proj = next((p for p in updated_projs if p.player.position == "QB"), None)
        if qb_proj and qb_proj.pass_attempts:
            assert qb_proj.pass_attempts > 0
            # Should have ~8% more pass attempts
            assert qb_proj.pass_attempts > service.db.query(Projection).filter(
                Projection.projection_id == qb_proj.projection_id
            ).first().pass_attempts
        
        # Verify TE targets increased
        te_proj = next((p for p in updated_projs if p.player.position == "TE"), None)
        if te_proj and te_proj.targets:
            assert te_proj.targets > 0
            # Targets should scale with pass volume
            assert te_proj.targets > service.db.query(Projection).filter(
                Projection.projection_id == te_proj.projection_id
            ).first().targets

    @pytest.mark.asyncio
    async def test_projection_creation_update_flow(self, service, sample_players, team_stats_2024):
        """Test full flow of creating and updating projections."""
        mahomes_id = sample_players["ids"]["Patrick Mahomes"]
        
        # Create initial projection
        base_proj = await service.create_base_projection(
            player_id=mahomes_id,
            season=2024
        )
        
        # Update with minor adjustment
        minor_adjustments = {
            'pass_volume': 1.03,  # 3% increase in passing volume
        }
        
        minor_update = await service.update_projection(
            projection_id=base_proj.projection_id,
            adjustments=minor_adjustments
        )
        
        # Now significant adjustment
        major_adjustments = {
            'pass_volume': 1.10,   # 10% increase
            'td_rate': 1.15,       # 15% more TDs
            'int_rate': 0.85,      # 15% fewer INTs
            'rush_volume': 0.90    # 10% fewer rushes
        }
        
        major_update = await service.update_projection(
            projection_id=minor_update.projection_id,
            adjustments=major_adjustments
        )
        
        # Verify compounding effects
        assert major_update.pass_attempts > minor_update.pass_attempts
        assert major_update.pass_td > minor_update.pass_td
        
        # Pass attempts should be approximately 1.03 * 1.10 = 1.133 times the base
        assert major_update.pass_attempts == pytest.approx(
            base_proj.pass_attempts * 1.03 * 1.10, rel=0.01
        )
        
        # Fantasy points should increase
        assert major_update.half_ppr > base_proj.half_ppr

    @pytest.mark.asyncio
    async def test_projection_variance(self, service, sample_players, team_stats_2024):
        """Test generating projection variance/confidence intervals."""
        mahomes_id = sample_players["ids"]["Patrick Mahomes"]
        
        # Create base projection
        base_proj = await service.create_base_projection(
            player_id=mahomes_id,
            season=2024
        )
        
        # Generate variance ranges
        variance_ranges = await service.generate_projection_variance(
            projection_id=base_proj.projection_id
        )
        
        assert variance_ranges is not None
        assert "low" in variance_ranges
        assert "high" in variance_ranges
        
        # Verify ranges for key stats
        for stat in ["pass_yards", "pass_td", "rush_yards", "half_ppr"]:
            assert stat in variance_ranges["low"]
            assert stat in variance_ranges["high"]
            assert variance_ranges["low"][stat] < getattr(base_proj, stat)
            assert variance_ranges["high"][stat] > getattr(base_proj, stat)
        
        # Check that variance is reasonable (not too wide or narrow)
        for stat in ["pass_yards", "pass_td"]:
            base_value = getattr(base_proj, stat)
            low_value = variance_ranges["low"][stat]
            high_value = variance_ranges["high"][stat]
            
            # Range shouldn't be more than ±30% for most stats
            range_pct = (high_value - low_value) / base_value
            assert range_pct <= 0.60, f"Variance range for {stat} is too wide"
            assert range_pct >= 0.10, f"Variance range for {stat} is too narrow"

    @pytest.mark.asyncio
    async def test_projection_consistency(self, service, sample_players, team_stats_2024):
        """Test consistency of projections (e.g., yards per attempt stays reasonable)."""
        mahomes_id = sample_players["ids"]["Patrick Mahomes"]
        
        # Create base projection
        base_proj = await service.create_base_projection(
            player_id=mahomes_id,
            season=2024
        )
        
        # Apply extreme adjustments
        extreme_adjustments = {
            'pass_volume': 1.30,   # 30% more passes
            'td_rate': 1.25        # 25% more TDs
        }
        
        updated_proj = await service.update_projection(
            projection_id=base_proj.projection_id,
            adjustments=extreme_adjustments
        )
        
        # Even with extreme adjustments, efficiency metrics should remain realistic
        # Yards per attempt shouldn't change significantly
        assert updated_proj.yards_per_att == pytest.approx(base_proj.yards_per_att, rel=0.05)
        
        # Completion percentage shouldn't change significantly
        assert updated_proj.comp_pct == pytest.approx(base_proj.comp_pct, rel=0.05)
        
        # TD rate should change proportional to the adjustment
        assert updated_proj.pass_td_rate == pytest.approx(base_proj.pass_td_rate * 1.25, rel=0.05)
        
        # Fantasy points should increase
        assert updated_proj.half_ppr > base_proj.half_ppr

    @pytest.mark.asyncio
    async def test_fantasy_points_calculation(self, service, sample_players, team_stats_2024):
        """Test fantasy points calculation from individual stats."""
        mahomes_id = sample_players["ids"]["Patrick Mahomes"]
        
        # Create base projection
        proj = await service.create_base_projection(
            player_id=mahomes_id,
            season=2024
        )
        
        # Calculate expected half PPR points manually
        expected_points = (
            proj.pass_yards * 0.04 +  # 1 pt per 25 yards
            proj.pass_td * 4 +        # 4 pts per TD
            proj.interceptions * -1 + # -1 pt per INT
            proj.rush_yards * 0.1 +   # 1 pt per 10 yards
            proj.rush_td * 6          # 6 pts per TD
        )
        
        # Should match within small margin
        assert proj.half_ppr == pytest.approx(expected_points, rel=0.01)
        
        # Test with manual changes
        proj.pass_yards = 5000
        proj.pass_td = 40
        proj.interceptions = 10
        proj.rush_yards = 400
        proj.rush_td = 4
        
        # Recalculate fantasy points
        proj.half_ppr = proj.calculate_fantasy_points()
        
        # Calculate expected half PPR points again
        expected_points = (
            5000 * 0.04 +  # 200
            40 * 4 +       # 160
            10 * -1 +      # -10
            400 * 0.1 +    # 40
            4 * 6          # 24
        )                  # = 414
        
        assert proj.half_ppr == pytest.approx(expected_points, rel=0.01)