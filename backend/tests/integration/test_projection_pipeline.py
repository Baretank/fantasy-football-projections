class TestProjectionPipeline:
    async def test_create_base_projection(self, service):
        # Test full projection creation pipeline
        player_id = "test_player"
        projection = await service.create_base_projection(player_id, 2024)
        
        assert projection is not None
        assert projection.season == 2024
        assert projection.half_ppr > 0

    async def test_team_consistency(self, service):
        # Test team-level stat consistency
        team = "KC"
        stats = await service.get_team_stats(team, 2024)
        
        assert stats.pass_attempts + stats.rush_attempts == stats.plays