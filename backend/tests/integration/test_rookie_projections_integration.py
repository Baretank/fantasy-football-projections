import pytest
import os
import tempfile
import json
import uuid
from pathlib import Path
import logging
from datetime import datetime
from sqlalchemy import and_
import shutil

from backend.database.models import Player, Projection, RookieProjectionTemplate
from backend.services.rookie_import_service import RookieImportService
from backend.services.rookie_projection_service import RookieProjectionService

logger = logging.getLogger(__name__)

# Test file paths
TEST_DATA_DIR = "/tmp/test_data"
TEST_ROOKIES_JSON = os.path.join(TEST_DATA_DIR, "test_rookies_projections.json")


@pytest.fixture
def rookie_import_service(test_db):
    """Create rookie import service with test db."""
    return RookieImportService(test_db)


@pytest.fixture
def rookie_projection_service(test_db):
    """Create rookie projection service with test db."""
    return RookieProjectionService(test_db)


@pytest.fixture
def setup_rookies_json():
    """Create a temporary rookies.json file for testing."""
    # Create a temporary rookies.json in the test data directory
    test_rookies = {
        "rookies": [
            {
                "name": "Caleb Williams",
                "position": "QB",
                "team": "CHI",
                "height": 74,
                "weight": 215,
                "date_of_birth": "2001-11-18",
                "draft_team": "CHI",
                "draft_round": 1,
                "draft_pick": 1,
                "draft_position": 1,
                "projected_stats": {
                    "games": 17,
                    "pass_attempts": 520,
                    "completions": 328,
                    "pass_yards": 3900,
                    "pass_td": 24,
                    "interceptions": 12,
                    "rush_attempts": 65,
                    "rush_yards": 320,
                    "rush_td": 3,
                },
            },
            {
                "name": "Marvin Harrison Jr.",
                "position": "WR",
                "team": "ARI",
                "height": 74,
                "weight": 209,
                "date_of_birth": "2001-08-11",
                "draft_team": "ARI",
                "draft_round": 1,
                "draft_pick": 4,
                "draft_position": 4,
                "projected_stats": {
                    "games": 17,
                    "targets": 125,
                    "receptions": 80,
                    "rec_yards": 1100,
                    "rec_td": 7,
                    "rush_attempts": 3,
                    "rush_yards": 25,
                    "rush_td": 0,
                },
            },
            {
                "name": "Brock Bowers",
                "position": "TE",
                "team": "LV",
                "height": 76,
                "weight": 243,
                "date_of_birth": "2002-08-14",
                "draft_team": "LV",
                "draft_round": 1,
                "draft_pick": 13,
                "draft_position": 13,
                "projected_stats": {
                    "games": 17,
                    "targets": 95,
                    "receptions": 70,
                    "rec_yards": 850,
                    "rec_td": 6,
                },
            },
        ]
    }

    # Ensure directory exists
    os.makedirs(TEST_DATA_DIR, exist_ok=True)

    # Write test data
    with open(TEST_ROOKIES_JSON, "w") as f:
        json.dump(test_rookies, f)

    # Copy to the expected location for the service to find it
    target_dir = Path(__file__).parent.parent.parent.parent / "data"
    os.makedirs(target_dir, exist_ok=True)
    shutil.copy(TEST_ROOKIES_JSON, target_dir / "rookies.json")

    yield TEST_ROOKIES_JSON

    # Cleanup
    if os.path.exists(TEST_ROOKIES_JSON):
        os.remove(TEST_ROOKIES_JSON)

    # Remove copy from target dir
    if os.path.exists(target_dir / "rookies.json"):
        os.remove(target_dir / "rookies.json")


@pytest.fixture
def rookie_templates(test_db):
    """Create rookie projection templates for testing."""
    templates = [
        # QB templates
        RookieProjectionTemplate(
            template_id=str(uuid.uuid4()),
            position="QB",
            draft_round=1,  # Added required field
            draft_pick_min=1,
            draft_pick_max=10,
            games=16.0,
            snap_share=0.9,
            pass_attempts=34.0,  # per game
            comp_pct=0.62,
            yards_per_att=7.2,
            pass_td_rate=0.045,
            int_rate=0.025,
            rush_att_per_game=4.5,
            rush_yards_per_att=5.2,
            rush_td_per_game=0.25,
        ),
        RookieProjectionTemplate(
            template_id=str(uuid.uuid4()),
            position="QB",
            draft_round=1,  # Added required field
            draft_pick_min=11,
            draft_pick_max=32,
            games=10.0,
            snap_share=0.65,
            pass_attempts=30.0,  # per game
            comp_pct=0.60,
            yards_per_att=6.8,
            pass_td_rate=0.04,
            int_rate=0.03,
            rush_att_per_game=3.5,
            rush_yards_per_att=4.8,
            rush_td_per_game=0.18,
        ),
        # WR templates
        RookieProjectionTemplate(
            template_id=str(uuid.uuid4()),
            position="WR",
            draft_round=1,  # Added required field
            draft_pick_min=1,
            draft_pick_max=15,
            games=16.0,
            snap_share=0.85,
            targets_per_game=7.2,
            catch_rate=0.64,
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
            draft_round=1,  # Added required field
            draft_pick_min=1,
            draft_pick_max=50,
            games=15.0,
            snap_share=0.70,
            targets_per_game=5.1,
            catch_rate=0.66,
            rec_yards_per_catch=10.8,
            rec_td_per_catch=0.06,
            rush_att_per_game=0.0,
            rush_yards_per_att=0.0,
            rush_td_per_att=0.0,
        ),
    ]

    for template in templates:
        test_db.add(template)

    test_db.commit()
    return templates


@pytest.mark.asyncio
async def test_create_rookie_projections(test_db, rookie_projection_service, setup_rookies_json):
    """Test creating projections for rookies based on rookies.json data."""
    # Create players first
    for rookie_data in [
        {"name": "Caleb Williams", "position": "QB", "team": "CHI"},
        {"name": "Marvin Harrison Jr.", "position": "WR", "team": "ARI"},
        {"name": "Brock Bowers", "position": "TE", "team": "LV"},
    ]:
        player = Player(
            player_id=str(uuid.uuid4()),
            name=rookie_data["name"],
            position=rookie_data["position"],
            team=rookie_data["team"],
            status="Rookie",
        )
        test_db.add(player)
    test_db.commit()

    # Create rookie projections
    season = 2025
    success_count, errors = await rookie_projection_service.create_rookie_projections(season)

    # Verify results
    assert success_count == 3, f"Expected 3 projections to be created, got {success_count}"
    assert len(errors) == 0, f"Expected no errors, got: {errors}"

    # Verify database state
    projections = test_db.query(Projection).filter(Projection.season == season).all()
    assert len(projections) == 3

    # Verify specific projections
    caleb_proj = (
        test_db.query(Projection)
        .join(Player)
        .filter(Player.name == "Caleb Williams", Projection.season == season)
        .first()
    )

    assert caleb_proj is not None
    # These assertions might be modified by the comp model
    assert caleb_proj.pass_attempts is not None
    assert caleb_proj.pass_yards is not None
    assert caleb_proj.rush_yards is not None

    # Check fantasy points calculation
    assert caleb_proj.half_ppr > 0, "Fantasy points should be calculated"


@pytest.mark.asyncio
async def test_enhance_rookie_projection(test_db, rookie_projection_service, setup_rookies_json):
    """Test enhancing a rookie projection with the comp model."""
    # First create the projections
    season = 2025
    await rookie_projection_service.create_rookie_projections(season)

    # Get a rookie player
    player = test_db.query(Player).filter(Player.name == "Marvin Harrison Jr.").first()
    assert player is not None

    # Get original projection values
    original_proj = (
        test_db.query(Projection)
        .filter(Projection.player_id == player.player_id, Projection.season == season)
        .first()
    )

    original_targets = original_proj.targets
    original_rec_yards = original_proj.rec_yards

    # Enhance with "high" comp level
    enhanced_proj = await rookie_projection_service.enhance_rookie_projection(
        player_id=player.player_id, comp_level="high", playing_time_pct=0.9, season=season
    )

    # Verify enhancement
    assert enhanced_proj is not None
    assert enhanced_proj.targets != original_targets, "Targets should be adjusted"
    assert enhanced_proj.rec_yards != original_rec_yards, "Rec yards should be adjusted"

    # Verify efficiency metrics are set
    assert enhanced_proj.catch_pct is not None
    assert enhanced_proj.yards_per_target is not None


@pytest.mark.asyncio
async def test_draft_position_based_projection(
    test_db, rookie_projection_service, rookie_templates
):
    """Test creating projections based on draft position and templates."""
    # Create a new rookie player
    rookie = Player(
        player_id=str(uuid.uuid4()),
        name="Test Rookie QB",
        position="QB",
        team="NYJ",
        status="Rookie",
    )
    test_db.add(rookie)
    test_db.commit()

    # Create projection based on draft position
    season = 2025
    draft_position = 5  # First round, high template

    projection = await rookie_projection_service.create_draft_based_projection(
        player_id=rookie.player_id, draft_position=draft_position, season=season
    )

    # Verify projection was created using the template
    assert projection is not None
    assert projection.games == 16.0  # From the template for picks 1-10
    assert projection.pass_attempts == 16.0 * 34.0  # From the template
    assert projection.comp_pct == 0.62  # From the template

    # Verify the player was updated
    updated_rookie = test_db.query(Player).get(rookie.player_id)
    assert updated_rookie.draft_position == 5
    assert updated_rookie.status == "Rookie"


@pytest.mark.asyncio
async def test_template_fallback_behavior(test_db, rookie_projection_service, rookie_templates):
    """Test fallback behavior when no exact template match exists."""
    # Create a new rookie player with a position that has templates but no exact match
    rookie = Player(
        player_id=str(uuid.uuid4()),
        name="Late Round QB",
        position="QB",
        team="DEN",
        status="Rookie",
    )
    test_db.add(rookie)
    test_db.commit()

    # Create projection with draft position outside defined templates
    season = 2025
    draft_position = 150  # Outside the template ranges

    projection = await rookie_projection_service.create_draft_based_projection(
        player_id=rookie.player_id, draft_position=draft_position, season=season
    )

    # Verify it falls back to the comp model
    assert projection is not None

    # Should use the "low" comp model
    for template in rookie_templates:
        if template.position == "QB" and template.draft_pick_min <= 32:
            assert projection.pass_attempts != template.pass_attempts * template.games
            break


@pytest.mark.asyncio
async def test_multiple_scenario_projections(
    test_db, rookie_projection_service, setup_rookies_json
):
    """Test creating multiple projections for different scenarios."""
    # First create base projections
    season = 2025
    await rookie_projection_service.create_rookie_projections(season)

    # Create a scenario
    scenario = {
        "scenario_id": str(uuid.uuid4()),
        "name": "Test Scenario",
        "description": "Scenario for testing rookie projections",
    }

    # Create projections for the scenario
    success_count, errors = await rookie_projection_service.create_rookie_projections(
        season=season, scenario_id=scenario["scenario_id"]
    )

    # Verify results
    assert success_count == 3, f"Expected 3 projections to be created, got {success_count}"

    # Verify we have both base and scenario projections
    base_projections = (
        test_db.query(Projection)
        .filter(Projection.season == season, Projection.scenario_id == None)
        .all()
    )

    scenario_projections = (
        test_db.query(Projection)
        .filter(Projection.season == season, Projection.scenario_id == scenario["scenario_id"])
        .all()
    )

    assert len(base_projections) == 3, "Should have 3 base projections"
    assert len(scenario_projections) == 3, "Should have 3 scenario projections"
