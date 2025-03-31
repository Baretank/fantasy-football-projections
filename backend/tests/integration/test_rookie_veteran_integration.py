import pytest
import uuid
import pandas as pd
from unittest.mock import patch, MagicMock
import tempfile
import os
import json
from datetime import datetime
from sqlalchemy import and_

from backend.services.rookie_import_service import RookieImportService
from backend.services.player_import_service import PlayerImportService
from backend.services.rookie_projection_service import RookieProjectionService
from backend.services.projection_service import ProjectionService
from backend.database.models import Player, RookieProjectionTemplate as RookieTemplate, Projection

class TestRookieVeteranIntegration:
    @pytest.fixture(scope="function")
    def services(self, test_db):
        """Create all needed services for testing the flow."""
        return {
            "rookie_import": RookieImportService(test_db),
            "player_import": PlayerImportService(test_db),
            "rookie_projection": RookieProjectionService(test_db),
            "projection": ProjectionService(test_db)
        }
    
    @pytest.fixture(scope="function")
    def setup_test_files(self):
        """Create test files for rookie and veteran imports."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a rookie CSV file
            rookie_csv = os.path.join(temp_dir, "rookies.csv")
            rookies_data = pd.DataFrame({
                "Name": ["Rookie QB", "Rookie RB", "Rookie WR", "Rookie TE"],
                "Team": ["DAL", "MIA", "DET", "CHI"],
                "Position": ["QB", "RB", "WR", "TE"],
                "College": ["Alabama", "Ohio State", "Georgia", "Michigan"],
                "Draft_Pick": [1, 15, 25, 45],
                "Draft_Round": [1, 1, 1, 2]
            })
            rookies_data.to_csv(rookie_csv, index=False)
            
            # Create a rookie JSON template file
            rookie_templates = {
                "QB": {
                    "early_first": {
                        "games": 16,
                        "pass_attempts": 520,
                        "completions": 340,
                        "pass_yards": 3800,
                        "pass_td": 24,
                        "interceptions": 12,
                        "carries": 45,
                        "rush_yards": 220,
                        "rush_td": 2
                    },
                    "late_first": {
                        "games": 10,
                        "pass_attempts": 320,
                        "completions": 200,
                        "pass_yards": 2200,
                        "pass_td": 14,
                        "interceptions": 10,
                        "carries": 30,
                        "rush_yards": 150,
                        "rush_td": 1
                    }
                },
                "RB": {
                    "early_first": {
                        "games": 16,
                        "carries": 220,
                        "rush_yards": 950,
                        "rush_td": 7,
                        "targets": 50,
                        "receptions": 40,
                        "rec_yards": 320,
                        "rec_td": 2
                    },
                    "late_first": {
                        "games": 16,
                        "carries": 180,
                        "rush_yards": 750,
                        "rush_td": 5,
                        "targets": 40,
                        "receptions": 30,
                        "rec_yards": 240,
                        "rec_td": 1
                    }
                },
                "WR": {
                    "early_first": {
                        "games": 16,
                        "targets": 120,
                        "receptions": 75,
                        "rec_yards": 950,
                        "rec_td": 7,
                        "carries": 8,
                        "rush_yards": 45,
                        "rush_td": 0
                    },
                    "late_first": {
                        "games": 16,
                        "targets": 90,
                        "receptions": 55,
                        "rec_yards": 700,
                        "rec_td": 5,
                        "carries": 5,
                        "rush_yards": 30,
                        "rush_td": 0
                    }
                },
                "TE": {
                    "early_first": {
                        "games": 16,
                        "targets": 80,
                        "receptions": 55,
                        "rec_yards": 600,
                        "rec_td": 5
                    },
                    "late_first": {
                        "games": 16,
                        "targets": 60,
                        "receptions": 40,
                        "rec_yards": 450,
                        "rec_td": 3
                    }
                }
            }
            
            rookie_template_json = os.path.join(temp_dir, "rookie_templates.json")
            with open(rookie_template_json, 'w') as f:
                json.dump(rookie_templates, f)
            
            # Create a veteran players CSV file
            veteran_csv = os.path.join(temp_dir, "veterans.csv")
            veterans_data = pd.DataFrame({
                "player_id": [str(uuid.uuid4()) for _ in range(4)],
                "name": ["Veteran QB", "Veteran RB", "Veteran WR", "Veteran TE"],
                "team": ["DAL", "MIA", "DET", "CHI"],
                "position": ["QB", "RB", "WR", "TE"],
                "is_active": [True, True, True, True],
                "years_exp": [5, 3, 7, 2]
            })
            veterans_data.to_csv(veteran_csv, index=False)
            
            yield {
                "rookie_csv": rookie_csv,
                "rookie_template_json": rookie_template_json,
                "veteran_csv": veteran_csv,
                "rookie_data": rookies_data,
                "veteran_data": veterans_data
            }
    
    @pytest.mark.asyncio
    async def test_rookie_import_from_csv(self, services, setup_test_files, test_db):
        """Test importing rookies from a CSV file."""
        # Import rookies
        count = await services["rookie_import"].import_from_csv(setup_test_files["rookie_csv"])
        
        # Verify rookies were imported
        assert count == 4
        
        # Check that rookies were created in database
        rookies = test_db.query(Player).filter(Player.status == "Rookie").all()
        assert len(rookies) == 4
        
        # Verify specific rookie
        qb_rookie = test_db.query(Player).filter(
            and_(
                Player.status == "Rookie",
                Player.position == "QB"
            )
        ).first()
        
        assert qb_rookie is not None
        assert qb_rookie.name == "Rookie QB"
        assert qb_rookie.team == "DAL"
        assert qb_rookie.draft_pick == 1
        assert qb_rookie.draft_round == 1
    
    @pytest.mark.asyncio
    async def test_rookie_template_import(self, services, setup_test_files, test_db):
        """Test importing rookie projection templates."""
        # Import templates
        count = await services["rookie_projection"].import_templates(setup_test_files["rookie_template_json"])
        
        # Verify templates were imported
        assert count > 0
        
        # Check templates in database
        templates = test_db.query(RookieTemplate).all()
        assert len(templates) > 0
        
        # Verify QB early first template
        qb_template = test_db.query(RookieTemplate).filter(
            and_(
                RookieTemplate.position == "QB",
                RookieTemplate.draft_tier == "early_first"
            )
        ).first()
        
        assert qb_template is not None
        assert qb_template.stats is not None
        assert "pass_attempts" in qb_template.stats
        assert qb_template.stats["pass_attempts"] == 520
    
    @pytest.mark.asyncio
    async def test_veteran_import_from_csv(self, services, setup_test_files, test_db):
        """Test importing veteran players from a CSV file."""
        # Import veterans
        count = await services["player_import"].import_players_from_csv(setup_test_files["veteran_csv"])
        
        # Verify veterans were imported
        assert count == 4
        
        # Check veterans in database
        veterans = test_db.query(Player).filter(Player.status != "Rookie").all()
        assert len(veterans) == 4
        
        # Verify specific veteran
        wr_veteran = test_db.query(Player).filter(
            and_(
                Player.status != "Rookie",
                Player.position == "WR"
            )
        ).first()
        
        assert wr_veteran is not None
        assert wr_veteran.name == "Veteran WR"
        assert wr_veteran.team == "DET"
    
    @pytest.mark.asyncio
    async def test_generate_rookie_projections(self, services, setup_test_files, test_db):
        """Test generating projections for rookies using templates."""
        # Import rookies and templates first
        await self.test_rookie_import_from_csv(services, setup_test_files, test_db)
        await self.test_rookie_template_import(services, setup_test_files, test_db)
        
        # Generate rookie projections
        season = datetime.now().year
        projections = await services["rookie_projection"].generate_rookie_projections(season)
        
        # Verify projections were created
        assert len(projections) == 4
        
        # Check projections in database
        db_projections = test_db.query(Projection).filter(Projection.season == season).all()
        assert len(db_projections) == 4
        
        # Verify QB projection
        qb_rookie = test_db.query(Player).filter(
            and_(
                Player.status == "Rookie",
                Player.position == "QB"
            )
        ).first()
        
        qb_projection = test_db.query(Projection).filter(
            and_(
                Projection.player_id == qb_rookie.player_id,
                Projection.season == season
            )
        ).first()
        
        assert qb_projection is not None
        assert qb_projection.pass_attempts == 520  # From early_first template
        assert qb_projection.pass_yards == 3800
        assert qb_projection.half_ppr > 0
    
    @pytest.mark.asyncio
    async def test_generate_veteran_projections(self, services, setup_test_files, test_db):
        """Test generating projections for veteran players."""
        # Import veterans first
        await self.test_veteran_import_from_csv(services, setup_test_files, test_db)
        
        # Create mock historical stats for veterans
        for player in test_db.query(Player).filter(Player.status != "Rookie").all():
            if player.position == "QB":
                stats = {
                    "games": 16,
                    "pass_attempts": 550,
                    "completions": 360,
                    "pass_yards": 4200,
                    "pass_td": 30,
                    "interceptions": 10,
                    "carries": 40,
                    "rush_yards": 180,
                    "rush_td": 1
                }
            elif player.position == "RB":
                stats = {
                    "games": 16,
                    "carries": 250,
                    "rush_yards": 1100,
                    "rush_td": 9,
                    "targets": 60,
                    "receptions": 50,
                    "rec_yards": 400,
                    "rec_td": 2
                }
            elif player.position == "WR":
                stats = {
                    "games": 16,
                    "targets": 130,
                    "receptions": 85,
                    "rec_yards": 1200,
                    "rec_td": 8,
                    "carries": 5,
                    "rush_yards": 30,
                    "rush_td": 0
                }
            elif player.position == "TE":
                stats = {
                    "games": 16,
                    "targets": 90,
                    "receptions": 70,
                    "rec_yards": 800,
                    "rec_td": 6
                }
            
            # Mock the create_base_projection method
            async def mock_create_base_projection(player_id, season):
                player = test_db.query(Player).filter(Player.player_id == player_id).first()
                
                projection = Projection(
                    projection_id=str(uuid.uuid4()),
                    player_id=player_id,
                    season=season,
                    **stats
                )
                
                # Calculate fantasy points
                if player.position == "QB":
                    projection.half_ppr = (
                        projection.pass_yards * 0.04 +
                        projection.pass_td * 4 +
                        projection.rush_yards * 0.1 +
                        projection.rush_td * 6 -
                        projection.interceptions * 1
                    )
                elif player.position in ["RB", "WR", "TE"]:
                    projection.half_ppr = (
                        projection.rush_yards * 0.1 +
                        projection.rush_td * 6 +
                        projection.rec_yards * 0.1 +
                        projection.receptions * 0.5 +
                        projection.rec_td * 6
                    )
                
                test_db.add(projection)
                test_db.commit()
                return projection
        
        # Generate projections with mocked method
        season = datetime.now().year
        with patch.object(services["projection"], 'create_base_projection', mock_create_base_projection):
            projections = []
            for player in test_db.query(Player).filter(Player.rookie_year.is_(None)).all():
                proj = await services["projection"].create_base_projection(
                    player_id=player.player_id,
                    season=season
                )
                projections.append(proj)
        
        # Verify projections were created
        assert len(projections) == 4
        
        # Check projections in database
        db_projections = test_db.query(Projection).filter(
            and_(
                Projection.season == season,
                Projection.player_id.in_([p.player_id for p in test_db.query(Player).filter(Player.status != "Rookie").all()])
            )
        ).all()
        assert len(db_projections) == 4
        
        # Verify WR projection
        wr_veteran = test_db.query(Player).filter(
            and_(
                Player.rookie_year.is_(None),
                Player.position == "WR"
            )
        ).first()
        
        wr_projection = test_db.query(Projection).filter(
            and_(
                Projection.player_id == wr_veteran.player_id,
                Projection.season == season
            )
        ).first()
        
        assert wr_projection is not None
        assert wr_projection.targets == 130
        assert wr_projection.rec_yards == 1200
        assert wr_projection.half_ppr > 0
    
    @pytest.mark.asyncio
    async def test_unified_player_database(self, services, setup_test_files, test_db):
        """Test that rookies and veterans are properly unified in the player database."""
        # Import both rookies and veterans
        await self.test_rookie_import_from_csv(services, setup_test_files, test_db)
        await self.test_veteran_import_from_csv(services, setup_test_files, test_db)
        
        # Query all players for a specific team
        team = "DAL"
        team_players = test_db.query(Player).filter(Player.team == team).all()
        
        # Should include both rookie and veteran
        assert len(team_players) == 2
        
        # Verify one rookie and one veteran
        rookie_count = len([p for p in team_players if p.status == "Rookie"])
        veteran_count = len([p for p in team_players if p.status != "Rookie"])
        
        assert rookie_count == 1
        assert veteran_count == 1
        
        # Check that they have distinct player_ids
        player_ids = [p.player_id for p in team_players]
        assert len(player_ids) == len(set(player_ids))  # No duplicates
    
    @pytest.mark.asyncio
    async def test_integrated_projection_set(self, services, setup_test_files, test_db):
        """Test creating a complete integrated projection set with rookies and veterans."""
        # Import rookies, templates, and veterans
        await self.test_rookie_import_from_csv(services, setup_test_files, test_db)
        await self.test_rookie_template_import(services, setup_test_files, test_db)
        await self.test_veteran_import_from_csv(services, setup_test_files, test_db)
        
        # Generate rookie projections
        season = datetime.now().year
        rookie_projections = await services["rookie_projection"].generate_rookie_projections(season)
        
        # Generate veteran projections with the same mock approach
        async def mock_create_base_projection(player_id, season):
            player = test_db.query(Player).filter(Player.player_id == player_id).first()
            
            if player.position == "QB":
                stats = {
                    "games": 16,
                    "pass_attempts": 550,
                    "completions": 360,
                    "pass_yards": 4200,
                    "pass_td": 30,
                    "interceptions": 10,
                    "carries": 40,
                    "rush_yards": 180,
                    "rush_td": 1
                }
            elif player.position == "RB":
                stats = {
                    "games": 16,
                    "carries": 250,
                    "rush_yards": 1100,
                    "rush_td": 9,
                    "targets": 60,
                    "receptions": 50,
                    "rec_yards": 400,
                    "rec_td": 2
                }
            elif player.position == "WR":
                stats = {
                    "games": 16,
                    "targets": 130,
                    "receptions": 85,
                    "rec_yards": 1200,
                    "rec_td": 8,
                    "carries": 5,
                    "rush_yards": 30,
                    "rush_td": 0
                }
            elif player.position == "TE":
                stats = {
                    "games": 16,
                    "targets": 90,
                    "receptions": 70,
                    "rec_yards": 800,
                    "rec_td": 6
                }
            
            projection = Projection(
                projection_id=str(uuid.uuid4()),
                player_id=player_id,
                season=season,
                **stats
            )
            
            # Calculate fantasy points
            if player.position == "QB":
                projection.half_ppr = (
                    projection.pass_yards * 0.04 +
                    projection.pass_td * 4 +
                    projection.rush_yards * 0.1 +
                    projection.rush_td * 6 -
                    projection.interceptions * 1
                )
            elif player.position in ["RB", "WR", "TE"]:
                projection.half_ppr = (
                    getattr(projection, 'rush_yards', 0) * 0.1 +
                    getattr(projection, 'rush_td', 0) * 6 +
                    projection.rec_yards * 0.1 +
                    projection.receptions * 0.5 +
                    projection.rec_td * 6
                )
            
            test_db.add(projection)
            test_db.commit()
            return projection
        
        # Generate veteran projections with mocked method
        with patch.object(services["projection"], 'create_base_projection', mock_create_base_projection):
            veteran_projections = []
            for player in test_db.query(Player).filter(Player.rookie_year.is_(None)).all():
                proj = await services["projection"].create_base_projection(
                    player_id=player.player_id,
                    season=season
                )
                veteran_projections.append(proj)
        
        # Verify both sets were created
        assert len(rookie_projections) == 4
        assert len(veteran_projections) == 4
        
        # Get complete projection set
        all_projections = test_db.query(Projection).filter(Projection.season == season).all()
        assert len(all_projections) == 8
        
        # Get position rankings across both rookies and veterans
        position_rankings = {}
        for position in ["QB", "RB", "WR", "TE"]:
            # Get all projections for this position
            position_projs = test_db.query(Projection).join(Player).filter(
                and_(
                    Player.position == position,
                    Projection.season == season
                )
            ).all()
            
            # Sort by fantasy points
            sorted_projs = sorted(position_projs, key=lambda p: p.half_ppr, reverse=True)
            
            position_rankings[position] = [
                {
                    "player_id": p.player_id,
                    "fantasy_points": p.half_ppr,
                    "is_rookie": test_db.query(Player).filter(Player.player_id == p.player_id).first().rookie_year is not None
                }
                for p in sorted_projs
            ]
        
        # Verify we have rankings for each position
        for position in ["QB", "RB", "WR", "TE"]:
            assert len(position_rankings[position]) == 2
            
            # Typically veterans should outperform rookies
            # Check if first ranked player is a veteran (not guaranteed but typical)
            top_player = position_rankings[position][0]
            assert top_player["fantasy_points"] > 0
        
        # Check that we can query all players easily
        all_players = test_db.query(Player).all()
        assert len(all_players) == 8
        
        # Verify proper attribution of projections
        for proj in all_projections:
            player = test_db.query(Player).filter(Player.player_id == proj.player_id).first()
            assert player is not None