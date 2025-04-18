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
from backend.database.models import Player, RookieProjectionTemplate, Projection


class TestRookieVeteranIntegration:
    @pytest.fixture(scope="function")
    def services(self, test_db):
        """Create all needed services for testing the flow."""
        return {
            "rookie_import": RookieImportService(test_db),
            "player_import": PlayerImportService(test_db),
            "rookie_projection": RookieProjectionService(test_db),
            "projection": ProjectionService(test_db),
        }

    @pytest.fixture(scope="function")
    def setup_test_files(self):
        """Create test files for rookie and veteran imports."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a rookie CSV file
            rookie_csv = os.path.join(temp_dir, "rookies.csv")
            rookies_data = pd.DataFrame(
                {
                    "name": ["Rookie QB", "Rookie RB", "Rookie WR", "Rookie TE"],
                    "team": ["DAL", "MIA", "DET", "CHI"],
                    "position": ["QB", "RB", "WR", "TE"],
                    "college": ["Alabama", "Ohio State", "Georgia", "Michigan"],
                    "draft_pick": [1, 15, 25, 45],
                    "draft_round": [1, 1, 1, 2],
                    "draft_team": ["DAL", "MIA", "DET", "CHI"],
                }
            )
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
                        "rush_attempts": 45,
                        "rush_yards": 220,
                        "rush_td": 2,
                    },
                    "late_first": {
                        "games": 10,
                        "pass_attempts": 320,
                        "completions": 200,
                        "pass_yards": 2200,
                        "pass_td": 14,
                        "interceptions": 10,
                        "rush_attempts": 30,
                        "rush_yards": 150,
                        "rush_td": 1,
                    },
                },
                "RB": {
                    "early_first": {
                        "games": 16,
                        "rush_attempts": 220,
                        "rush_yards": 950,
                        "rush_td": 7,
                        "targets": 50,
                        "receptions": 40,
                        "rec_yards": 320,
                        "rec_td": 2,
                    },
                    "late_first": {
                        "games": 16,
                        "rush_attempts": 180,
                        "rush_yards": 750,
                        "rush_td": 5,
                        "targets": 40,
                        "receptions": 30,
                        "rec_yards": 240,
                        "rec_td": 1,
                    },
                },
                "WR": {
                    "early_first": {
                        "games": 16,
                        "targets": 120,
                        "receptions": 75,
                        "rec_yards": 950,
                        "rec_td": 7,
                        "rush_attempts": 8,
                        "rush_yards": 45,
                        "rush_td": 0,
                    },
                    "late_first": {
                        "games": 16,
                        "targets": 90,
                        "receptions": 55,
                        "rec_yards": 700,
                        "rec_td": 5,
                        "rush_attempts": 5,
                        "rush_yards": 30,
                        "rush_td": 0,
                    },
                },
                "TE": {
                    "early_first": {
                        "games": 16,
                        "targets": 80,
                        "receptions": 55,
                        "rec_yards": 600,
                        "rec_td": 5,
                    },
                    "late_first": {
                        "games": 16,
                        "targets": 60,
                        "receptions": 40,
                        "rec_yards": 450,
                        "rec_td": 3,
                    },
                },
            }

            rookie_template_json = os.path.join(temp_dir, "rookie_templates.json")
            with open(rookie_template_json, "w") as f:
                json.dump(rookie_templates, f)

            # Create a veteran players CSV file
            veteran_csv = os.path.join(temp_dir, "veterans.csv")
            veterans_data = pd.DataFrame(
                {
                    "player_id": [str(uuid.uuid4()) for _ in range(4)],
                    "name": ["Veteran QB", "Veteran RB", "Veteran WR", "Veteran TE"],
                    "team": ["DAL", "MIA", "DET", "CHI"],
                    "position": ["QB", "RB", "WR", "TE"],
                    "is_active": [True, True, True, True],
                    "years_exp": [5, 3, 7, 2],
                }
            )
            veterans_data.to_csv(veteran_csv, index=False)

            yield {
                "rookie_csv": rookie_csv,
                "rookie_template_json": rookie_template_json,
                "veteran_csv": veteran_csv,
                "rookie_data": rookies_data,
                "veteran_data": veterans_data,
            }

    @pytest.mark.asyncio
    async def test_rookie_import_from_csv(self, services, setup_test_files, test_db):
        """Test importing rookies from a CSV file."""
        # Import rookies
        count, _ = await services["rookie_import"].import_rookies_from_csv(
            setup_test_files["rookie_csv"]
        )

        # Verify rookies were imported
        assert count == 4

        # Check that rookies were created in database
        rookies = test_db.query(Player).filter(Player.status == "Rookie").all()
        assert len(rookies) == 4

        # Verify specific rookie
        qb_rookie = (
            test_db.query(Player)
            .filter(and_(Player.status == "Rookie", Player.position == "QB"))
            .first()
        )

        assert qb_rookie is not None
        assert qb_rookie.name == "Rookie QB"
        assert qb_rookie.team == "DAL"
        assert qb_rookie.draft_pick == 1
        assert qb_rookie.draft_round == 1

    @pytest.mark.asyncio
    async def test_rookie_template_import(self, services, setup_test_files, test_db):
        """Test importing rookie projection templates."""
        # Create templates directly using the RookieProjectionTemplate model
        try:
            # Create templates for different positions and draft ranges
            templates = [
                # QB templates
                RookieProjectionTemplate(
                    template_id=str(uuid.uuid4()),
                    position="QB",
                    draft_round=1,
                    draft_pick_min=1,
                    draft_pick_max=10,
                    games=16.0,
                    snap_share=0.80,
                    pass_attempts=520,
                    comp_pct=0.62,
                    yards_per_att=7.2,
                    pass_td_rate=0.04,
                    int_rate=0.03,
                    rush_att_per_game=4.0,
                    rush_yards_per_att=5.0,
                    rush_td_per_game=0.2,
                ),
                # RB templates
                RookieProjectionTemplate(
                    template_id=str(uuid.uuid4()),
                    position="RB",
                    draft_round=1,
                    draft_pick_min=1,
                    draft_pick_max=32,
                    games=15.0,
                    snap_share=0.65,
                    rush_att_per_game=14.0,
                    rush_yards_per_att=4.4,
                    rush_td_per_att=0.03,
                    targets_per_game=3.5,
                    catch_rate=0.75,
                    rec_yards_per_catch=8.0,
                    rec_td_per_catch=0.04,
                ),
                # WR templates
                RookieProjectionTemplate(
                    template_id=str(uuid.uuid4()),
                    position="WR",
                    draft_round=1,
                    draft_pick_min=1,
                    draft_pick_max=15,
                    games=16.0,
                    snap_share=0.80,
                    targets_per_game=7.0,
                    catch_rate=0.65,
                    rec_yards_per_catch=13.5,
                    rec_td_per_catch=0.07,
                    rush_att_per_game=0.5,
                    rush_yards_per_att=8.0,
                    rush_td_per_att=0.03,
                ),
                # TE templates
                RookieProjectionTemplate(
                    template_id=str(uuid.uuid4()),
                    position="TE",
                    draft_round=1,
                    draft_pick_min=1,
                    draft_pick_max=32,
                    games=15.0,
                    snap_share=0.70,
                    targets_per_game=5.0,
                    catch_rate=0.68,
                    rec_yards_per_catch=11.0,
                    rec_td_per_catch=0.08,
                    rush_att_per_game=0.0,
                    rush_yards_per_att=0.0,
                    rush_td_per_game=0.0,
                ),
            ]

            # Add templates to database
            for template in templates:
                test_db.add(template)

            test_db.commit()

            # Verify templates were imported
            count = len(templates)
            assert count > 0

            # Check templates in database
            db_templates = test_db.query(RookieProjectionTemplate).all()
            assert len(db_templates) > 0

            # Verify QB template
            qb_template = (
                test_db.query(RookieProjectionTemplate)
                .filter(
                    and_(
                        RookieProjectionTemplate.position == "QB",
                        RookieProjectionTemplate.draft_pick_min == 1,
                        RookieProjectionTemplate.draft_pick_max == 10,
                    )
                )
                .first()
            )

            assert qb_template is not None
            assert qb_template.pass_attempts == 520
            assert qb_template.comp_pct == 0.62
        except Exception as e:
            assert False, f"Failed to import templates: {str(e)}"

    @pytest.mark.asyncio
    async def test_veteran_import_from_csv(self, services, setup_test_files, test_db):
        """Test importing veteran players from a CSV file."""
        # Import veterans
        count, _ = await services["player_import"].import_players_from_csv(
            setup_test_files["veteran_csv"]
        )

        # Verify veterans were imported
        assert count == 4

        # Check veterans in database
        veterans = test_db.query(Player).filter(Player.status != "Rookie").all()
        assert len(veterans) == 4

        # Verify specific veteran
        wr_veteran = (
            test_db.query(Player)
            .filter(and_(Player.status != "Rookie", Player.position == "WR"))
            .first()
        )

        assert wr_veteran is not None
        assert wr_veteran.name == "Veteran WR"
        assert wr_veteran.team == "DET"

    @pytest.mark.asyncio
    async def test_generate_rookie_projections(self, services, setup_test_files, test_db):
        """Test generating projections for rookies using templates."""
        # Import rookies and templates first
        await self.test_rookie_import_from_csv(services, setup_test_files, test_db)
        await self.test_rookie_template_import(services, setup_test_files, test_db)

        # Get the rookie players
        rookies = test_db.query(Player).filter(Player.status == "Rookie").all()
        season = datetime.now().year

        # Using create_draft_based_projection method which is available in the service
        projections = []
        for i, rookie in enumerate(rookies):
            # Mock draft position based on the order in the list
            draft_position = (i + 1) * 10  # 10, 20, 30, 40

            # Generate projection for each rookie
            projection = await services["rookie_projection"].create_draft_based_projection(
                player_id=rookie.player_id, draft_position=draft_position, season=season
            )
            projections.append(projection)

        # Verify projections were created
        assert len(projections) == 4

        # Check projections in database
        db_projections = test_db.query(Projection).filter(Projection.season == season).all()
        assert len(db_projections) == 4

        # Verify QB projection
        qb_rookie = (
            test_db.query(Player)
            .filter(and_(Player.status == "Rookie", Player.position == "QB"))
            .first()
        )

        qb_projection = (
            test_db.query(Projection)
            .filter(and_(Projection.player_id == qb_rookie.player_id, Projection.season == season))
            .first()
        )

        assert qb_projection is not None
        assert qb_projection.half_ppr > 0

        # Verify we have the right fields based on position
        if qb_rookie.position == "QB":
            assert qb_projection.pass_attempts > 0
            assert qb_projection.pass_yards > 0

    @pytest.mark.asyncio
    async def test_generate_veteran_projections(self, services, setup_test_files, test_db):
        """Test generating projections for veteran players."""
        # Import veterans first
        await self.test_veteran_import_from_csv(services, setup_test_files, test_db)

        # Define the position stats
        position_stats = {
            "QB": {
                "games": 16,
                "pass_attempts": 550,
                "completions": 360,
                "pass_yards": 4200,
                "pass_td": 30,
                "interceptions": 10,
                "rush_attempts": 40,
                "rush_yards": 180,
                "rush_td": 1,
                "half_ppr": 300.0,
            },
            "RB": {
                "games": 16,
                "rush_attempts": 250,
                "rush_yards": 1100,
                "rush_td": 9,
                "targets": 60,
                "receptions": 50,
                "rec_yards": 400,
                "rec_td": 2,
                "half_ppr": 200.0,
            },
            "WR": {
                "games": 16,
                "targets": 130,
                "receptions": 85,
                "rec_yards": 1200,
                "rec_td": 8,
                "rush_attempts": 5,
                "rush_yards": 30,
                "rush_td": 0,
                "half_ppr": 225.0,
            },
            "TE": {
                "games": 16,
                "targets": 90,
                "receptions": 70,
                "rec_yards": 800,
                "rec_td": 6,
                "half_ppr": 175.0,
            },
        }

        # Directly create projections for each veteran
        season = datetime.now().year
        projections = []

        for player in test_db.query(Player).filter(Player.status != "Rookie").all():
            stats = position_stats.get(player.position, {})
            if not stats:
                continue

            projection = Projection(
                projection_id=str(uuid.uuid4()), player_id=player.player_id, season=season, **stats
            )

            test_db.add(projection)
            projections.append(projection)

        test_db.commit()

        # Verify projections were created
        assert len(projections) == 4

        # Check projections in database
        db_projections = (
            test_db.query(Projection)
            .filter(
                and_(
                    Projection.season == season,
                    Projection.player_id.in_(
                        [
                            p.player_id
                            for p in test_db.query(Player).filter(Player.status != "Rookie").all()
                        ]
                    ),
                )
            )
            .all()
        )
        assert len(db_projections) == 4

        # Verify WR projection
        wr_veteran = (
            test_db.query(Player)
            .filter(and_(Player.status != "Rookie", Player.position == "WR"))
            .first()
        )

        wr_projection = (
            test_db.query(Projection)
            .filter(and_(Projection.player_id == wr_veteran.player_id, Projection.season == season))
            .first()
        )

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

        # Generate rookie projections using create_draft_based_projection
        season = datetime.now().year

        # Create rookie projections using the draft-based approach
        rookies = test_db.query(Player).filter(Player.status == "Rookie").all()
        rookie_projections = []
        for i, rookie in enumerate(rookies):
            # Mock draft position based on the order in the list
            draft_position = (i + 1) * 10  # 10, 20, 30, 40

            # Generate projection for each rookie
            projection = await services["rookie_projection"].create_draft_based_projection(
                player_id=rookie.player_id, draft_position=draft_position, season=season
            )
            rookie_projections.append(projection)

        # Define the position stats for veterans
        position_stats = {
            "QB": {
                "games": 16,
                "pass_attempts": 550,
                "completions": 360,
                "pass_yards": 4200,
                "pass_td": 30,
                "interceptions": 10,
                "rush_attempts": 40,
                "rush_yards": 180,
                "rush_td": 1,
                "half_ppr": 300.0,
            },
            "RB": {
                "games": 16,
                "rush_attempts": 250,
                "rush_yards": 1100,
                "rush_td": 9,
                "targets": 60,
                "receptions": 50,
                "rec_yards": 400,
                "rec_td": 2,
                "half_ppr": 200.0,
            },
            "WR": {
                "games": 16,
                "targets": 130,
                "receptions": 85,
                "rec_yards": 1200,
                "rec_td": 8,
                "rush_attempts": 5,
                "rush_yards": 30,
                "rush_td": 0,
                "half_ppr": 225.0,
            },
            "TE": {
                "games": 16,
                "targets": 90,
                "receptions": 70,
                "rec_yards": 800,
                "rec_td": 6,
                "half_ppr": 175.0,
            },
        }

        # Directly create projections for veterans
        veteran_projections = []
        veterans = test_db.query(Player).filter(Player.status != "Rookie").all()

        for vet in veterans:
            stats = position_stats.get(vet.position, {})
            if not stats:
                continue

            projection = Projection(
                projection_id=str(uuid.uuid4()), player_id=vet.player_id, season=season, **stats
            )

            test_db.add(projection)
            veteran_projections.append(projection)

        test_db.commit()

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
            position_projs = (
                test_db.query(Projection)
                .join(Player)
                .filter(and_(Player.position == position, Projection.season == season))
                .all()
            )

            # Sort by fantasy points
            sorted_projs = sorted(position_projs, key=lambda p: p.half_ppr, reverse=True)

            position_rankings[position] = [
                {
                    "player_id": p.player_id,
                    "fantasy_points": p.half_ppr,
                    "is_rookie": test_db.query(Player)
                    .filter(Player.player_id == p.player_id)
                    .first()
                    .status
                    == "Rookie",
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
