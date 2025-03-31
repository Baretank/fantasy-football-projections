import pytest
import os
import uuid
import pandas as pd
from unittest.mock import patch, MagicMock
import tempfile
from sqlalchemy import and_
from datetime import datetime

from backend.services.data_import_service import DataImportService
from backend.services.projection_service import ProjectionService
from backend.services.data_validation import DataValidationService
from backend.services.team_stat_service import TeamStatService
from backend.services.batch_service import BatchService
from backend.database.models import Player, BaseStat, TeamStat, Projection

class TestImportProjectionFlow:
    @pytest.fixture(scope="function")
    def services(self, test_db):
        """Create all needed services for testing the flow."""
        return {
            "data_import": DataImportService(test_db),
            "projection": ProjectionService(test_db),
            "validation": DataValidationService(test_db),
            "team_stat": TeamStatService(test_db),
            "batch": BatchService(test_db)
        }
    
    @pytest.fixture(scope="function")
    def setup_test_files(self):
        """Create test CSV files for import testing."""
        # Create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a players CSV file
            players_csv = os.path.join(temp_dir, "players.csv")
            players_data = pd.DataFrame({
                "player_id": [str(uuid.uuid4()) for _ in range(5)],
                "name": ["Player 1", "Player 2", "Player 3", "Player 4", "Player 5"],
                "team": ["KC", "KC", "SF", "SF", "BUF"],
                "position": ["QB", "WR", "RB", "TE", "QB"]
            })
            players_data.to_csv(players_csv, index=False)
            
            # Create a stats CSV file
            stats_csv = os.path.join(temp_dir, "stats.csv")
            stats_data = pd.DataFrame({
                "player_id": players_data["player_id"].tolist(),
                "season": [2023, 2023, 2023, 2023, 2023],
                "games": [17, 16, 16, 15, 17],
                # QB stats
                "pass_attempts": [600, None, None, None, 580],
                "completions": [400, None, None, None, 390],
                "pass_yards": [4800, None, None, None, 4500],
                "pass_td": [38, None, None, None, 35],
                "interceptions": [10, None, None, None, 8],
                # RB stats
                "carries": [60, None, 280, None, None],
                "rush_yards": [350, None, 1400, None, None],
                "rush_td": [3, None, 12, None, None],
                # Receiving stats
                "targets": [None, 140, 70, 110, None],
                "receptions": [None, 95, 55, 80, None],
                "rec_yards": [None, 1200, 500, 900, None],
                "rec_td": [None, 9, 3, 6, None]
            })
            stats_data.to_csv(stats_csv, index=False)
            
            # Create a team stats CSV file
            team_stats_csv = os.path.join(temp_dir, "team_stats.csv")
            team_stats_data = pd.DataFrame({
                "team": ["KC", "SF", "BUF"],
                "season": [2023, 2023, 2023],
                "plays": [1000, 1000, 1000],
                "pass_percentage": [0.60, 0.55, 0.58],
                "pass_attempts": [600, 550, 580],
                "pass_yards": [4250, 4200, 4100],
                "pass_td": [30, 34, 28],
                "rush_attempts": [400, 450, 420],
                "rush_yards": [1600, 2250, 2100],
                "rush_td": [19, 28, 22]
            })
            team_stats_data.to_csv(team_stats_csv, index=False)
            
            yield {
                "players_csv": players_csv,
                "stats_csv": stats_csv,
                "team_stats_csv": team_stats_csv,
                "player_ids": players_data["player_id"].tolist()
            }
    
    @pytest.mark.asyncio
    async def test_player_import_from_csv(self, services, setup_test_files, test_db):
        """Test importing players from a CSV file."""
        # Create a function to mock the actual import function
        async def mock_import_player_csv(file_path):
            # Read the CSV
            players_df = pd.read_csv(file_path)
            
            # Import each player
            for _, row in players_df.iterrows():
                player = Player(
                    player_id=row["player_id"],
                    name=row["name"],
                    team=row["team"],
                    position=row["position"],
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                test_db.add(player)
            
            test_db.commit()
            return len(players_df)
        
        # Call the function with our mock
        with patch.object(services["data_import"], 'import_players_from_csv', mock_import_player_csv):
            imported_count = await services["data_import"].import_players_from_csv(
                setup_test_files["players_csv"]
            )
            
            # Verify players were imported
            assert imported_count == 5
            
            # Check database for players
            players = test_db.query(Player).all()
            assert len(players) == 5
            
            # Verify player details
            kc_qb = test_db.query(Player).filter(
                and_(Player.team == "KC", Player.position == "QB")
            ).first()
            assert kc_qb is not None
            assert kc_qb.name == "Player 1"
    
    @pytest.mark.asyncio
    async def test_stats_import_from_csv(self, services, setup_test_files, test_db):
        """Test importing stats from a CSV file."""
        # First import players
        await self.test_player_import_from_csv(services, setup_test_files, test_db)
        
        # Create a function to mock the actual stats import
        async def mock_import_stats_csv(file_path, season):
            # Read the CSV
            stats_df = pd.read_csv(file_path)
            
            # Import each player's stats
            for _, row in stats_df.iterrows():
                # Create season totals as BaseStat objects
                for col in stats_df.columns:
                    if col in ["player_id", "season"]:
                        continue
                    
                    if pd.notna(row[col]):
                        stat = BaseStat(
                            stat_id=str(uuid.uuid4()),
                            player_id=row["player_id"],
                            season=season,
                            week=None,  # Season totals
                            stat_type=col,
                            value=float(row[col])
                        )
                        test_db.add(stat)
            
            test_db.commit()
            return len(stats_df)
        
        # Call the function with our mock
        with patch.object(services["data_import"], 'import_stats_from_csv', mock_import_stats_csv):
            imported_count = await services["data_import"].import_stats_from_csv(
                setup_test_files["stats_csv"], 
                2023
            )
            
            # Verify stats were imported
            assert imported_count == 5
            
            # Check database for stats
            stats = test_db.query(BaseStat).all()
            assert len(stats) > 0
            
            # Verify specific stats
            kc_qb = test_db.query(Player).filter(
                and_(Player.team == "KC", Player.position == "QB")
            ).first()
            
            qb_pass_yards = test_db.query(BaseStat).filter(
                and_(
                    BaseStat.player_id == kc_qb.player_id,
                    BaseStat.season == 2023,
                    BaseStat.stat_type == "pass_yards"
                )
            ).first()
            
            assert qb_pass_yards is not None
            assert qb_pass_yards.value == 4800
    
    @pytest.mark.asyncio
    async def test_team_stats_import(self, services, setup_test_files, test_db):
        """Test importing team stats from a CSV file."""
        # Create a function to mock the actual team stats import
        async def mock_import_team_stats_csv(file_path, season):
            # Read the CSV
            team_stats_df = pd.read_csv(file_path)
            
            # Import each team's stats
            for _, row in team_stats_df.iterrows():
                # Create TeamStat object
                team_stat = TeamStat(
                    team_stat_id=str(uuid.uuid4()),
                    team=row["team"],
                    season=season,
                    plays=row["plays"],
                    pass_percentage=row["pass_percentage"],
                    pass_attempts=row["pass_attempts"],
                    pass_yards=row["pass_yards"],
                    pass_td=row["pass_td"],
                    pass_td_rate=row["pass_td"] / row["pass_attempts"],
                    rush_attempts=row["rush_attempts"],
                    rush_yards=row["rush_yards"],
                    rush_td=row["rush_td"],
                    carries=row["rush_attempts"],
                    rush_yards_per_carry=row["rush_yards"] / row["rush_attempts"],
                    targets=row["pass_attempts"],
                    receptions=row["pass_attempts"] * 0.65,  # Approximate
                    rec_yards=row["pass_yards"],
                    rec_td=row["pass_td"],
                    rank=1  # Default rank
                )
                test_db.add(team_stat)
            
            test_db.commit()
            return len(team_stats_df)
        
        # Call the function with our mock
        with patch.object(services["team_stat"], 'import_team_stats_csv', mock_import_team_stats_csv):
            imported_count = await services["team_stat"].import_team_stats_csv(
                setup_test_files["team_stats_csv"], 
                2023
            )
            
            # Verify team stats were imported
            assert imported_count == 3
            
            # Check database for team stats
            team_stats = test_db.query(TeamStat).all()
            assert len(team_stats) == 3
            
            # Verify KC team stats
            kc_stats = test_db.query(TeamStat).filter(
                and_(TeamStat.team == "KC", TeamStat.season == 2023)
            ).first()
            
            assert kc_stats is not None
            assert kc_stats.pass_attempts == 600
            assert kc_stats.pass_yards == 4250
            assert kc_stats.rush_attempts == 400
    
    @pytest.mark.asyncio
    async def test_data_validation(self, services, setup_test_files, test_db):
        """Test data validation after import."""
        # Import players, stats, and team stats
        await self.test_player_import_from_csv(services, setup_test_files, test_db)
        await self.test_stats_import_from_csv(services, setup_test_files, test_db)
        await self.test_team_stats_import(services, setup_test_files, test_db)
        
        # Get a player to validate
        kc_qb = test_db.query(Player).filter(
            and_(Player.team == "KC", Player.position == "QB")
        ).first()
        
        # Run validation
        issues = services["validation"].validate_player_data(kc_qb, 2023)
        
        # Since our data is coming from CSV (not game logs), we might expect some issues
        # But the function should handle them gracefully
        
        # Create a potential issue manually to test correction
        pass_attempts_stat = test_db.query(BaseStat).filter(
            and_(
                BaseStat.player_id == kc_qb.player_id,
                BaseStat.season == 2023,
                BaseStat.stat_type == "pass_attempts"
            )
        ).first()
        
        # Change it to an inconsistent value
        original_value = pass_attempts_stat.value
        pass_attempts_stat.value = original_value * 0.7  # 70% of original
        test_db.commit()
        
        # Run validation again
        issues = services["validation"].validate_player_data(kc_qb, 2023)
        
        # Should detect the issue
        assert len(issues) > 0
        
        # Verify the stat was corrected or reported
        pass_attempts_stat = test_db.query(BaseStat).filter(
            and_(
                BaseStat.player_id == kc_qb.player_id,
                BaseStat.season == 2023,
                BaseStat.stat_type == "pass_attempts"
            )
        ).first()
        
        # Either restored to original or flagged
        assert pass_attempts_stat.value == original_value or "pass_attempts" in " ".join(issues)
    
    @pytest.mark.asyncio
    async def test_projection_creation(self, services, setup_test_files, test_db):
        """Test creating projections from imported data."""
        # Import and validate data
        await self.test_data_validation(services, setup_test_files, test_db)
        
        # Create future season team stats (for projections)
        future_season = 2024
        
        # Clone 2023 team stats for 2024
        team_stats_2023 = test_db.query(TeamStat).filter(TeamStat.season == 2023).all()
        for ts in team_stats_2023:
            future_ts = TeamStat(
                team_stat_id=str(uuid.uuid4()),
                team=ts.team,
                season=future_season,
                plays=ts.plays,
                pass_percentage=ts.pass_percentage,
                pass_attempts=ts.pass_attempts,
                pass_yards=ts.pass_yards,
                pass_td=ts.pass_td,
                pass_td_rate=ts.pass_td_rate,
                rush_attempts=ts.rush_attempts,
                rush_yards=ts.rush_yards,
                rush_td=ts.rush_td,
                carries=ts.carries,
                rush_yards_per_carry=ts.rush_yards_per_carry,
                targets=ts.targets,
                receptions=ts.receptions,
                rec_yards=ts.rec_yards,
                rec_td=ts.rec_td,
                rank=ts.rank
            )
            test_db.add(future_ts)
        
        test_db.commit()
        
        # Get all players
        players = test_db.query(Player).all()
        
        # Create projections for each player
        projections = []
        for player in players:
            projection = await services["projection"].create_base_projection(
                player_id=player.player_id,
                season=future_season
            )
            assert projection is not None
            projections.append(projection)
        
        # Verify projections were created
        assert len(projections) == 5
        
        # Check specific projections by position
        for proj in projections:
            player = test_db.query(Player).filter(Player.player_id == proj.player_id).first()
            
            # Position-specific checks
            if player.position == "QB":
                assert proj.pass_attempts > 0
                assert proj.pass_yards > 0
                assert proj.pass_td > 0
                
            elif player.position == "RB":
                assert proj.carries > 0
                assert proj.rush_yards > 0
                assert proj.rush_td > 0
                
            elif player.position == "WR":
                assert proj.targets > 0
                assert proj.receptions > 0
                assert proj.rec_yards > 0
                
            elif player.position == "TE":
                assert proj.targets > 0
                assert proj.receptions > 0
                assert proj.rec_yards > 0
            
            # All projections should have fantasy points
            assert proj.half_ppr > 0
    
    @pytest.mark.asyncio
    async def test_projection_adjustments(self, services, setup_test_files, test_db):
        """Test applying adjustments to projections."""
        # Create projections first
        await self.test_projection_creation(services, setup_test_files, test_db)
        
        # Get all projections
        projections = test_db.query(Projection).all()
        assert len(projections) > 0
        
        # Apply adjustments to each position type
        future_season = 2024
        
        # Find a QB projection
        qb_proj = test_db.query(Projection).join(Player).filter(
            and_(Player.position == "QB", Projection.season == future_season)
        ).first()
        
        if qb_proj:
            # Store original values
            original_pass_att = qb_proj.pass_attempts
            original_pass_td = qb_proj.pass_td
            
            # Apply QB-specific adjustments
            qb_adjustments = {
                'pass_volume': 1.1,    # 10% more passing
                'td_rate': 1.15,       # 15% better TD rate
                'int_rate': 0.9        # 10% fewer interceptions
            }
            
            updated_qb = await services["projection"].update_projection(
                projection_id=qb_proj.projection_id,
                adjustments=qb_adjustments
            )
            
            # Verify adjustments were applied
            assert updated_qb.pass_attempts > original_pass_att
            assert updated_qb.pass_td > original_pass_td
            assert abs(updated_qb.pass_attempts / original_pass_att - 1.1) < 0.01
        
        # Find an RB projection
        rb_proj = test_db.query(Projection).join(Player).filter(
            and_(Player.position == "RB", Projection.season == future_season)
        ).first()
        
        if rb_proj:
            # Store original values
            original_carries = rb_proj.carries
            original_rush_td = rb_proj.rush_td
            
            # Apply RB-specific adjustments
            rb_adjustments = {
                'rush_volume': 1.15,    # 15% more rushing
                'rush_efficiency': 1.05, # 5% better efficiency
                'td_rate': 1.1          # 10% better TD rate
            }
            
            updated_rb = await services["projection"].update_projection(
                projection_id=rb_proj.projection_id,
                adjustments=rb_adjustments
            )
            
            # Verify adjustments were applied
            assert updated_rb.carries > original_carries
            assert updated_rb.rush_td > original_rush_td
            assert abs(updated_rb.carries / original_carries - 1.15) < 0.01
        
        # Find a WR projection
        wr_proj = test_db.query(Projection).join(Player).filter(
            and_(Player.position == "WR", Projection.season == future_season)
        ).first()
        
        if wr_proj:
            # Store original values
            original_targets = wr_proj.targets
            original_rec = wr_proj.receptions
            
            # Apply WR-specific adjustments
            wr_adjustments = {
                'rec_volume': 1.12,     # 12% more targets
                'rec_efficiency': 1.05,  # 5% better catch rate
                'td_rate': 1.08         # 8% better TD rate
            }
            
            updated_wr = await services["projection"].update_projection(
                projection_id=wr_proj.projection_id,
                adjustments=wr_adjustments
            )
            
            # Verify adjustments were applied
            assert updated_wr.targets > original_targets
            assert updated_wr.receptions > original_rec
            assert abs(updated_wr.targets / original_targets - 1.12) < 0.01
    
    @pytest.mark.asyncio
    async def test_team_level_adjustments(self, services, setup_test_files, test_db):
        """Test applying team-level adjustments to projections."""
        # Apply individual adjustments first
        await self.test_projection_adjustments(services, setup_test_files, test_db)
        
        # Apply team adjustments for KC
        team = "KC"
        future_season = 2024
        
        # Get KC players' projections before adjustment
        kc_projections_before = test_db.query(Projection).join(Player).filter(
            and_(Player.team == team, Projection.season == future_season)
        ).all()
        
        # Store original values
        original_values = {}
        for proj in kc_projections_before:
            original_values[proj.projection_id] = {
                'pass_attempts': getattr(proj, 'pass_attempts', 0),
                'rush_attempts': getattr(proj, 'carries', 0),
                'targets': getattr(proj, 'targets', 0),
                'fantasy_points': proj.half_ppr
            }
        
        # Apply team-level adjustments
        team_adjustments = {
            'pass_volume': 1.08,     # 8% more passing
            'scoring_rate': 1.05     # 5% more scoring
        }
        
        # Apply adjustments
        updated_projections = await services["team_stat"].apply_team_adjustments(
            team=team,
            season=future_season,
            adjustments=team_adjustments
        )
        
        # Verify adjustments were applied team-wide
        assert len(updated_projections) > 0
        
        for proj in updated_projections:
            original = original_values[proj.projection_id]
            player = test_db.query(Player).filter(Player.player_id == proj.player_id).first()
            
            # Check position-specific adjustments
            if player.position == "QB" and original['pass_attempts'] > 0:
                # QB should have more pass attempts
                assert proj.pass_attempts > original['pass_attempts']
                assert abs(proj.pass_attempts / original['pass_attempts'] - 1.08) < 0.02
                
            elif player.position in ["WR", "TE"] and original['targets'] > 0:
                # Receivers should have more targets
                assert proj.targets > original['targets']
                assert abs(proj.targets / original['targets'] - 1.08) < 0.02
            
            # All players should have increased fantasy points
            assert proj.half_ppr > original['fantasy_points']
    
    @pytest.mark.asyncio
    async def test_complete_flow(self, services, setup_test_files, test_db):
        """Test the complete import-to-projection flow with all adjustments."""
        # Perform all previous steps in sequence
        await self.test_team_level_adjustments(services, setup_test_files, test_db)
        
        # Final verification of complete pipeline
        future_season = 2024
        
        # Get all final projections
        final_projections = test_db.query(Projection).filter(
            Projection.season == future_season
        ).all()
        
        # Verify reasonable projections for each position
        for proj in final_projections:
            player = test_db.query(Player).filter(Player.player_id == proj.player_id).first()
            
            # Position-specific checks for reasonable values
            if player.position == "QB":
                # QBs should have significant passing stats
                assert proj.pass_attempts >= 500, f"QB {player.name} has too few pass attempts: {proj.pass_attempts}"
                assert proj.pass_yards >= 4000, f"QB {player.name} has too few pass yards: {proj.pass_yards}"
                assert proj.pass_td >= 25, f"QB {player.name} has too few pass TDs: {proj.pass_td}"
                
            elif player.position == "RB":
                # RBs should have significant rushing stats
                assert proj.carries >= 200, f"RB {player.name} has too few carries: {proj.carries}"
                assert proj.rush_yards >= 800, f"RB {player.name} has too few rush yards: {proj.rush_yards}"
                assert proj.rush_td >= 5, f"RB {player.name} has too few rush TDs: {proj.rush_td}"
                
            elif player.position == "WR":
                # WRs should have significant receiving stats
                assert proj.targets >= 80, f"WR {player.name} has too few targets: {proj.targets}"
                assert proj.receptions >= 50, f"WR {player.name} has too few receptions: {proj.receptions}"
                assert proj.rec_yards >= 700, f"WR {player.name} has too few rec yards: {proj.rec_yards}"
                
            elif player.position == "TE":
                # TEs should have moderate receiving stats
                assert proj.targets >= 60, f"TE {player.name} has too few targets: {proj.targets}"
                assert proj.receptions >= 40, f"TE {player.name} has too few receptions: {proj.receptions}"
                assert proj.rec_yards >= 500, f"TE {player.name} has too few rec yards: {proj.rec_yards}"
            
            # All players should have reasonable fantasy points
            assert proj.half_ppr > 0
        
        # Team totals should be consistent with individual projections
        for team in ["KC", "SF", "BUF"]:
            # Get team stats
            team_stats = test_db.query(TeamStat).filter(
                and_(TeamStat.team == team, TeamStat.season == future_season)
            ).first()
            
            # Get player projections for this team
            team_projections = test_db.query(Projection).join(Player).filter(
                and_(Player.team == team, Projection.season == future_season)
            ).all()
            
            # Calculate team totals from individual projections
            team_pass_attempts = sum(getattr(p, 'pass_attempts', 0) for p in team_projections)
            team_pass_yards = sum(getattr(p, 'pass_yards', 0) for p in team_projections)
            team_rush_attempts = sum(getattr(p, 'carries', 0) for p in team_projections)
            team_rush_yards = sum(getattr(p, 'rush_yards', 0) for p in team_projections)
            
            # Verify consistency (within reasonable margins)
            if team_stats.pass_attempts > 0:
                # Should be close to team stats with slight differences due to adjustments
                pass_att_diff = abs(team_pass_attempts - team_stats.pass_attempts)
                pass_att_pct = pass_att_diff / team_stats.pass_attempts
                assert pass_att_pct < 0.15, f"Team {team} pass attempts inconsistent: {team_pass_attempts} vs {team_stats.pass_attempts}"
            
            if team_stats.rush_attempts > 0:
                rush_att_diff = abs(team_rush_attempts - team_stats.rush_attempts)
                rush_att_pct = rush_att_diff / team_stats.rush_attempts
                assert rush_att_pct < 0.15, f"Team {team} rush attempts inconsistent: {team_rush_attempts} vs {team_stats.rush_attempts}"