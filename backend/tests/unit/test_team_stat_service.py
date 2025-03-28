import pytest
from backend.services.team_stat_service import TeamStatsService

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