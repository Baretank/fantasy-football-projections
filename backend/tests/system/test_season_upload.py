class TestDataImport:
    async def test_full_import_pipeline(self, services):
        # Test complete data import process
        result = await services.import_season_data(2024)
        
        assert result.success_count > 0
        assert len(result.error_messages) == 0
        
        # Verify data consistency
        teams = await services.get_all_teams()
        for team in teams:
            assert await services.validate_team_totals(team)