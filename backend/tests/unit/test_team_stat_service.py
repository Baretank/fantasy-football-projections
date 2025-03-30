import pytest
import uuid
from backend.services.team_stat_service import TeamStatsService
from backend.database.models import TeamStat, Projection, Player

class TestTeamStatService:
    @pytest.mark.asyncio
    async def test_import_team_stats(self, team_stats_service, test_db):
        """Test importing team stats using mock data."""
        success_count, error_messages = await team_stats_service.import_team_stats(2024)
        
        print("\nTest import_team_stats:")
        print(f"Successfully imported {success_count} team stats")
        if error_messages:
            print("Errors:", error_messages)
            
        assert success_count == 4  # Our mock has 4 teams
        assert len(error_messages) == 0
        
        # Verify KC stats were imported correctly
        kc_stats = await team_stats_service.get_team_stats("KC", 2024)
        assert kc_stats is not None
        assert kc_stats.pass_attempts == 600
        assert kc_stats.rush_attempts == 400
        assert kc_stats.pass_td == 30
        assert kc_stats.rush_td == 19
        
        # Verify team total consistency
        assert abs(kc_stats.pass_attempts + kc_stats.rush_attempts - kc_stats.plays) < 0.01

    @pytest.mark.asyncio
    async def test_get_team_stats(self, team_stats_service, team_stats_2024):
        """Test retrieving team stats."""
        kc_stats = await team_stats_service.get_team_stats("KC", 2024)
        
        print("\nTest get_team_stats:")
        print(f"Retrieved KC 2024 stats:")
        print(f"- Total plays: {kc_stats.plays}")
        print(f"- Pass attempts: {kc_stats.pass_attempts}")
        print(f"- Rush attempts: {kc_stats.rush_attempts}")
        
        assert kc_stats is not None
        assert kc_stats.team == "KC"
        assert kc_stats.season == 2024
        assert kc_stats.pass_attempts == 600
        assert kc_stats.pass_percentage == 0.60
        assert kc_stats.rush_yards_per_carry == 4.0
        
    @pytest.mark.asyncio
    async def test_validate_team_stats(self, team_stats_service, team_stats_2024):
        """Test team stats validation."""
        # Test validation of known good stats
        kc_stats = await team_stats_service.get_team_stats("KC", 2024)
        is_valid = await team_stats_service.validate_team_stats(kc_stats)
        
        print("\nTest validate_team_stats:")
        print(f"Validating KC 2024 stats:")
        print(f"- Plays match: {abs(kc_stats.pass_attempts + kc_stats.rush_attempts - kc_stats.plays) < 0.01}")
        print(f"- Pass %: {kc_stats.pass_percentage:.3f}")
        print(f"- YPC: {kc_stats.rush_yards_per_carry:.2f}")
        
        assert is_valid, "Known good stats should validate"
        
        # Additional validation checks
        assert kc_stats.pass_yards == kc_stats.rec_yards, "Pass yards should match receiving yards"
        assert kc_stats.pass_td == kc_stats.rec_td, "Pass TDs should match receiving TDs"
        assert kc_stats.targets == kc_stats.pass_attempts, "Targets should match pass attempts"

    @pytest.fixture(scope="function")
    def sample_team_projections(self, test_db, sample_players):
        """Create sample projections for players on a team."""
        projections = []
        
        # Get KC players
        mahomes_id = sample_players["ids"]["Patrick Mahomes"]
        kelce_id = sample_players["ids"]["Travis Kelce"]
        
        # Create QB projection
        qb_proj = Projection(
            projection_id=str(uuid.uuid4()),
            player_id=mahomes_id,
            season=2024,
            games=17,
            half_ppr=350.5,
            
            # Passing stats
            pass_attempts=600,
            completions=400,
            pass_yards=4800,
            pass_td=38,
            interceptions=10,
            comp_pct=0.667,
            yards_per_att=8.0,
            pass_td_rate=0.063,
            int_rate=0.017,
            
            # Rushing stats
            carries=60,
            rush_yards=350,
            rush_td=3,
            yards_per_carry=5.83,
            
            # Usage metrics
            snap_share=0.99,
            has_overrides=False
        )
        projections.append(qb_proj)
        
        # Create TE projection
        te_proj = Projection(
            projection_id=str(uuid.uuid4()),
            player_id=kelce_id,
            season=2024,
            games=16,
            half_ppr=245.0,
            
            # Receiving stats
            targets=140,
            receptions=98,
            rec_yards=1200,
            rec_td=10,
            catch_pct=0.7,
            yards_per_target=8.57,
            rec_td_rate=0.071,
            
            has_overrides=False
        )
        projections.append(te_proj)
        
        for proj in projections:
            test_db.add(proj)
        
        test_db.commit()
        return projections

    @pytest.mark.asyncio
    async def test_apply_team_adjustments(self, team_stats_service, sample_team_projections, test_db):
        """Test applying team-level adjustments to player projections."""
        # Original KC team stats (from fixture)
        orig_kc_stats = await team_stats_service.get_team_stats("KC", 2024)
        
        # Create a modified team stat object with increased passing
        new_kc_stats = TeamStat(
            team_stat_id=str(uuid.uuid4()),
            team="KC",
            season=2024,
            plays=1100,                  # Increased from 1000
            pass_percentage=0.65,        # Increased from 0.60
            pass_attempts=715,           # Increased from 600
            pass_yards=5300,             # Increased from 4250
            pass_td=42,                  # Increased from 30
            pass_td_rate=0.0587,         # 42/715
            rush_attempts=385,           # Decreased due to more passes
            rush_yards=1540,             # Slightly decreased
            rush_td=16,                  # Decreased from 19
            carries=385,                 # Same as rush_attempts
            rush_yards_per_carry=4.0,    # 1540/385
            targets=715,                 # Same as pass_attempts
            receptions=465,              # Increased
            rec_yards=5300,              # Same as pass_yards
            rec_td=42,                   # Same as pass_td
            rank=1
        )
        
        # Apply team adjustments to players
        adjusted_projs = await team_stats_service.apply_team_adjustments(
            original_stats=orig_kc_stats,
            new_stats=new_kc_stats,
            players=sample_team_projections
        )
        
        assert len(adjusted_projs) == 2
        
        # Verify QB adjustments
        qb_proj = next(p for p in adjusted_projs if p.player_id == sample_players["ids"]["Patrick Mahomes"])
        
        # QB should see increased pass attempts and yards
        assert qb_proj.pass_attempts > 600
        assert qb_proj.pass_yards > 4800
        assert qb_proj.pass_td > 38
        
        # Calculate expected values with simple scaling
        pass_att_scale = 715 / 600  # ~1.19x increase
        assert qb_proj.pass_attempts == pytest.approx(600 * pass_att_scale, rel=0.05)
        assert qb_proj.pass_yards == pytest.approx(4800 * pass_att_scale, rel=0.05)
        
        # Efficiency metrics should remain similar
        assert qb_proj.yards_per_att == pytest.approx(8.0, rel=0.05)
        
        # Verify TE adjustments
        te_proj = next(p for p in adjusted_projs if p.player_id == sample_players["ids"]["Travis Kelce"])
        
        # TE should see increased targets due to more team passing
        assert te_proj.targets > 140
        assert te_proj.rec_yards > 1200
        
        # Calculate expected TE scaling
        target_scale = 715 / 600  # Same as pass attempts scale
        assert te_proj.targets == pytest.approx(140 * target_scale, rel=0.05)
        
        # Efficiency metrics should remain similar
        assert te_proj.yards_per_target == pytest.approx(8.57, rel=0.05)
        assert te_proj.catch_pct == pytest.approx(0.7, rel=0.05)

    @pytest.mark.asyncio
    async def test_calculate_team_adjustment_factors(self, team_stats_service):
        """Test calculation of team adjustment factors."""
        # Original KC team stats (from fixture)
        orig_kc_stats = await team_stats_service.get_team_stats("KC", 2024)
        
        # Create a new team stat with specific changes
        new_kc_stats = TeamStat(
            team_stat_id=str(uuid.uuid4()),
            team="KC",
            season=2024,
            plays=1000,                  # Same total plays
            pass_percentage=0.70,        # Increased from 0.60
            pass_attempts=700,           # Increased from 600
            pass_yards=4800,             # Increased from 4250
            pass_td=35,                  # Increased from 30
            pass_td_rate=0.05,           # 35/700
            rush_attempts=300,           # Decreased from 400
            rush_yards=1300,             # Decreased from 1600
            rush_td=15,                  # Decreased from 19
            carries=300,                 # Same as rush_attempts
            rush_yards_per_carry=4.33,   # 1300/300
            targets=700,                 # Same as pass_attempts
            receptions=455,              # Increased from 390
            rec_yards=4800,              # Same as pass_yards
            rec_td=35,                   # Same as pass_td
            rank=1
        )
        
        # Calculate adjustment factors
        factors = team_stats_service.calculate_team_adjustment_factors(
            original_stats=orig_kc_stats,
            new_stats=new_kc_stats
        )
        
        # Check all adjustment factors
        assert "pass_volume" in factors
        assert "pass_efficiency" in factors
        assert "rush_volume" in factors
        assert "rush_efficiency" in factors
        assert "scoring_rate" in factors
        
        # Verify pass volume increase
        assert factors["pass_volume"] > 1.0
        assert factors["pass_volume"] == pytest.approx(700 / 600, rel=0.01)  # 1.167
        
        # Verify rush volume decrease
        assert factors["rush_volume"] < 1.0
        assert factors["rush_volume"] == pytest.approx(300 / 400, rel=0.01)  # 0.75
        
        # Verify efficiency changes
        pass_eff_factor = factors["pass_efficiency"]
        rush_eff_factor = factors["rush_efficiency"]
        
        # Pass efficiency is yards per attempt change
        orig_yards_per_att = orig_kc_stats.pass_yards / orig_kc_stats.pass_attempts
        new_yards_per_att = new_kc_stats.pass_yards / new_kc_stats.pass_attempts
        assert pass_eff_factor == pytest.approx(new_yards_per_att / orig_yards_per_att, rel=0.01)
        
        # Rush efficiency is yards per carry change
        assert rush_eff_factor == pytest.approx(4.33 / 4.0, rel=0.01)  # 1.0825
        
        # Scoring rate factor includes both rush and pass TDs
        orig_total_td = orig_kc_stats.pass_td + orig_kc_stats.rush_td
        new_total_td = new_kc_stats.pass_td + new_kc_stats.rush_td
        assert factors["scoring_rate"] == pytest.approx(new_total_td / orig_total_td, rel=0.01)

    @pytest.mark.asyncio
    async def test_get_team_adjustment_factors(self, team_stats_service, test_db):
        """Test calculating team adjustment factors from season to season."""
        # Get KC stats for 2024
        kc_2024 = await team_stats_service.get_team_stats("KC", 2024)
        
        # Create a 2023 team stat record with different values
        kc_2023 = TeamStat(
            team_stat_id=str(uuid.uuid4()),
            team="KC",
            season=2023,
            plays=950,                   # Fewer plays
            pass_percentage=0.58,        # Less passing
            pass_attempts=550,           # Fewer attempts
            pass_yards=4000,             # Fewer yards
            pass_td=27,                  # Fewer TDs
            pass_td_rate=0.049,          # 27/550
            rush_attempts=400,           # Same rush attempts
            rush_yards=1550,             # Slightly fewer yards
            rush_td=17,                  # Fewer TDs
            carries=400,                 # Same as rush_attempts
            rush_yards_per_carry=3.875,  # 1550/400
            targets=550,                 # Same as pass_attempts
            receptions=360,              # Fewer
            rec_yards=4000,              # Same as pass_yards
            rec_td=27,                   # Same as pass_td
            rank=2                       # Lower rank
        )
        
        test_db.add(kc_2023)
        test_db.commit()
        
        # Calculate adjustment factors from 2023 to 2024
        factors = await team_stats_service.get_team_adjustment_factors("KC", 2023, 2024)
        
        assert factors is not None
        
        # Verify year-over-year changes
        assert factors["pass_volume"] > 1.0  # More passing in 2024
        assert factors["pass_volume"] == pytest.approx(600 / 550, rel=0.01)  # 1.09
        
        assert factors["rush_volume"] == pytest.approx(400 / 400, rel=0.01)  # 1.0
        
        # Efficiency changes
        pass_yd_per_att_2023 = 4000 / 550  # 7.27
        pass_yd_per_att_2024 = 4250 / 600  # 7.08
        assert factors["pass_efficiency"] == pytest.approx(pass_yd_per_att_2024 / pass_yd_per_att_2023, rel=0.01)
        
        # Scoring changes
        tds_2023 = 27 + 17  # 44
        tds_2024 = 30 + 19  # 49
        assert factors["scoring_rate"] == pytest.approx(tds_2024 / tds_2023, rel=0.01)  # 1.11