import pytest
from backend.services.data_import_service import DataImportService
from backend.database.models import Player, BaseStat, TeamStat

class TestDataImport:
    @pytest.fixture(scope="function")
    def import_service(self, test_db):
        """Create DataImportService instance for testing."""
        return DataImportService(test_db)

    @pytest.mark.asyncio
    async def test_basic_data_import(self, import_service, test_db):
        """Test basic data import functionality."""
        # Import 2023 data (for 2024 projections)
        success_count, error_messages = await import_service.import_season_data(2023)
        
        print(f"\nImported {success_count} players")
        if error_messages:
            print("Errors encountered:", error_messages)

        # Verify players were imported
        players = test_db.query(Player).all()
        assert len(players) > 0, "No players were imported"
        
        # Check key positions
        positions = {player.position for player in players}
        assert all(pos in positions for pos in ['QB', 'RB', 'WR', 'TE']), "Missing key positions"
        
        # Verify base stats were created
        stats = test_db.query(BaseStat).all()
        assert len(stats) > 0, "No stats were imported"
        
        # Verify a known player (e.g., Patrick Mahomes)
        mahomes = test_db.query(Player).filter(
            Player.name == "Patrick Mahomes",
            Player.team == "KC"
        ).first()
        
        assert mahomes is not None, "Failed to import Patrick Mahomes"
        
        # Check Mahomes' stats
        mahomes_stats = test_db.query(BaseStat).filter(
            BaseStat.player_id == mahomes.player_id
        ).all()
        
        assert len(mahomes_stats) > 0, "No stats found for Mahomes"
        
        # Verify specific stats
        stat_types = {stat.stat_type for stat in mahomes_stats}
        expected_stats = {'pass_attempts', 'pass_yards', 'pass_td', 'completions'}
        assert all(stat in stat_types for stat in expected_stats), "Missing key QB stats"

    @pytest.mark.asyncio
    async def test_data_consistency(self, import_service, test_db):
        """Test data consistency across player and team stats."""
        await import_service.import_season_data(2023)
        
        # Get team totals
        kc_players = test_db.query(Player).filter(Player.team == "KC").all()
        assert len(kc_players) > 0, "No KC players found"
        
        # Get team passing stats
        kc_qb_stats = test_db.query(BaseStat).join(Player).filter(
            Player.team == "KC",
            Player.position == "QB",
            BaseStat.season == 2023
        ).all()
        
        # Get receiver stats
        kc_receiver_stats = test_db.query(BaseStat).join(Player).filter(
            Player.team == "KC",
            Player.position.in_(["WR", "TE"]),
            BaseStat.season == 2023
        ).all()
        
        # Verify pass attempts match targets
        qb_attempts = sum(stat.value for stat in kc_qb_stats 
                         if stat.stat_type == "pass_attempts")
        receiver_targets = sum(stat.value for stat in kc_receiver_stats 
                             if stat.stat_type == "targets")
        
        # Allow for small discrepancy due to floating point
        assert abs(qb_attempts - receiver_targets) < 5, "Pass attempts/targets mismatch"

    @pytest.mark.asyncio
    async def test_stat_validation(self, import_service, test_db):
        """Test validation of imported statistics."""
        await import_service.import_season_data(2023)
        
        # Test rushing stats
        rb_stats = test_db.query(BaseStat).join(Player).filter(
            Player.position == "RB",
            BaseStat.season == 2023
        ).all()
        
        for stat in rb_stats:
            if stat.stat_type in ["rush_yards", "rush_attempts", "rush_td"]:
                assert stat.value >= 0, f"Invalid negative value for {stat.stat_type}"
            if stat.stat_type == "rush_yards":
                assert stat.value < 3000, f"Unrealistic rushing yards: {stat.value}"
            if stat.stat_type == "rush_td":
                assert stat.value < 30, f"Unrealistic rushing TDs: {stat.value}"