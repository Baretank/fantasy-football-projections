import pytest
from backend.services import DataService

class TestDataService:
    @pytest.fixture(scope="function")
    def service(self, test_db):
        """Create DataService instance for testing."""
        return DataService(test_db)

    @pytest.mark.asyncio
    async def test_get_player(self, service, sample_players):
        """Test player retrieval by ID."""
        mahomes_id = sample_players["ids"]["Patrick Mahomes"]
        
        # Test successful retrieval
        player = await service.get_player(mahomes_id)
        print("\nTest get_player:")
        print(f"Retrieved player: {player.name} ({player.position}) - {player.team}")
        
        assert player is not None
        assert player.name == "Patrick Mahomes"
        assert player.team == "KC"
        assert player.position == "QB"

        # Test non-existent player
        player = await service.get_player("nonexistent")
        assert player is None

    @pytest.mark.asyncio
    async def test_get_players(self, service, sample_players):
        """Test player retrieval with filters."""
        # Test all players
        players = await service.get_players()
        print("\nTest get_players:")
        print("All players:")
        for player in players:
            print(f"- {player.name} ({player.position}) - {player.team}")

        assert len(players) == 4  # We have 4 sample players

        # Test position filter
        qbs = await service.get_players(position="QB")
        print("\nQBs only:")
        for qb in qbs:
            print(f"- {qb.name} ({qb.position}) - {qb.team}")
        assert len(qbs) == 2  # Mahomes and Purdy

        # Test team filter
        sf_players = await service.get_players(team="SF")
        print("\nSF players only:")
        for player in sf_players:
            print(f"- {player.name} ({player.position}) - {player.team}")
        assert len(sf_players) == 2  # Purdy and McCaffrey

    @pytest.mark.asyncio
    async def test_get_player_stats(self, service, sample_players, sample_stats):
        """Test player statistics retrieval."""
        mahomes_id = sample_players["ids"]["Patrick Mahomes"]
        mccaffrey_id = sample_players["ids"]["Christian McCaffrey"]

        # Test Mahomes stats
        print("\nTest get_player_stats (Mahomes):")
        mahomes_stats = await service.get_player_stats(mahomes_id, season=2023)
        print("Stats for Patrick Mahomes (2023):")
        for stat in mahomes_stats:
            print(f"- {stat.stat_type}: {stat.value}")
        
        # Verify Mahomes stats
        assert len(mahomes_stats) == 7  # Number of stats we created
        pass_attempts = next(stat for stat in mahomes_stats if stat.stat_type == "pass_attempts")
        assert pass_attempts.value == 584
        pass_yards = next(stat for stat in mahomes_stats if stat.stat_type == "pass_yards")
        assert pass_yards.value == 4183

        # Test McCaffrey stats
        print("\nTest get_player_stats (McCaffrey):")
        mccaffrey_stats = await service.get_player_stats(mccaffrey_id, season=2023)
        print("Stats for Christian McCaffrey (2023):")
        for stat in mccaffrey_stats:
            print(f"- {stat.stat_type}: {stat.value}")
        
        # Verify McCaffrey stats
        assert len(mccaffrey_stats) == 7  # Number of stats we created
        rush_yards = next(stat for stat in mccaffrey_stats if stat.stat_type == "rush_yards")
        assert rush_yards.value == 1459
        rec_td = next(stat for stat in mccaffrey_stats if stat.stat_type == "rec_td")
        assert rec_td.value == 7