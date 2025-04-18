import pytest
import json
import logging
import uuid
from pathlib import Path
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine, and_, or_
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from backend.main import app
from backend.database.models import Player, Projection, DraftStatus
from backend.database.database import Base, get_db

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestDraftDayTools:
    """System tests for draft day tool functionality."""

    @pytest.fixture(scope="function")
    def test_db_engine(self):
        """Create a test database engine using a unique file-based DB for each test."""
        # Create a file-based database that will be deleted after the test
        test_db_file = f"/tmp/test_db_{uuid.uuid4()}.sqlite"
        db_url = f"sqlite:///{test_db_file}"
        logger.debug(f"Creating test database at: {db_url}")

        engine = create_engine(
            db_url, connect_args={"check_same_thread": False}, poolclass=StaticPool
        )

        # Create all tables
        Base.metadata.create_all(bind=engine)

        # Yield the engine for use
        yield engine

        # Clean up by dropping all tables and removing the file
        Base.metadata.drop_all(bind=engine)
        engine.dispose()

        # Delete the database file
        try:
            Path(test_db_file).unlink(missing_ok=True)
            logger.debug(f"Deleted test database file: {test_db_file}")
        except Exception as e:
            logger.error(f"Failed to delete test database file: {str(e)}")

    @pytest.fixture(scope="function")
    def test_db(self, test_db_engine):
        """Create a test database session."""
        # Create a sessionmaker
        TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)

        # Create a session
        db = TestSession()

        # Make sure tables are empty before starting
        logger.debug("Ensuring database starts empty")
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()

        # Yield the session for use
        try:
            yield db
        finally:
            # Explicitly rollback any uncommitted changes
            logger.debug("Rolling back any uncommitted changes")
            db.rollback()

            # Clear all data from tables
            logger.debug("Clearing all tables")
            for table in reversed(Base.metadata.sorted_tables):
                db.execute(table.delete())
            db.commit()

            # Properly close the session
            db.close()

    @pytest.fixture(scope="function")
    def test_client(self, test_db):
        """Create a FastAPI test client with DB override."""
        # Log for debugging
        logger.debug("Creating test client with complete isolation")

        # Create a separate FastAPI app instance for testing to avoid
        # dependency override conflicts between tests
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        from backend.api.routes import (
            players_router,
            projections_router,
            overrides_router,
            scenarios_router,
        )
        from backend.api.routes.batch import router as batch_router
        from backend.api.routes.draft import router as draft_router
        from backend.api.routes.performance import router as performance_router
        from backend.database.database import get_db

        # Create test-specific app
        test_app = FastAPI()

        # Add middleware
        test_app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:5173"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Include same routers as the main app
        test_app.include_router(players_router, prefix="/api/players", tags=["players"])
        test_app.include_router(projections_router, prefix="/api/projections", tags=["projections"])
        test_app.include_router(overrides_router, prefix="/api/overrides", tags=["overrides"])
        test_app.include_router(scenarios_router, prefix="/api/scenarios", tags=["scenarios"])
        test_app.include_router(batch_router, prefix="/api/batch", tags=["batch operations"])
        test_app.include_router(draft_router, prefix="/api/draft", tags=["draft tools"])
        test_app.include_router(performance_router, prefix="/api/performance", tags=["performance"])

        # Define the dependency override specifically for this test
        def override_get_db():
            try:
                yield test_db
            finally:
                # No need to close here as that's done in the test_db fixture
                pass

        # Set up our override on our test-specific app
        test_app.dependency_overrides[get_db] = override_get_db

        # Create a test client with the isolated app
        with TestClient(test_app) as client:
            yield client

        logger.debug("Test client fixture cleanup complete")

    @pytest.fixture(scope="function")
    def sample_players(self, test_db):
        """Create sample players for testing draft tools."""
        fixture_id = str(uuid.uuid4())[:8]
        logger.debug(f"Setting up sample_players fixture for draft day tests (ID: {fixture_id})")

        # Create sample players with draft-related fields
        players = [
            Player(
                player_id="player1",
                name="Patrick Mahomes",
                team="KC",
                position="QB",
                is_rookie=False,
                draft_status="available",
            ),
            Player(
                player_id="player2",
                name="Caleb Williams",
                team="CHI",
                position="QB",
                is_rookie=True,
                draft_status="available",
                draft_round=1,
                draft_pick=1,
            ),
            Player(
                player_id="player3",
                name="Jayden Daniels",
                team="WAS",
                position="QB",
                is_rookie=True,
                draft_status="available",
                draft_round=1,
                draft_pick=2,
            ),
            Player(
                player_id="player4",
                name="Marvin Harrison Jr.",
                team="ARI",
                position="WR",
                is_rookie=True,
                draft_status="available",
                draft_round=1,
                draft_pick=4,
            ),
        ]

        # Add all players to the database
        for player in players:
            test_db.add(player)

        test_db.commit()
        logger.debug(f"Created {len(players)} sample players for draft day tests")

        # Verify players are in the database
        db_players = test_db.query(Player).all()
        logger.debug(f"Players in DB: {len(db_players)}")
        assert len(db_players) == 4, "Not all test players were saved"

        return players

    def test_update_draft_status(self, test_client, sample_players, test_db):
        """Test updating a player's draft status."""
        # Draft a player
        response = test_client.post(
            "/api/draft/draft-status",
            json={
                "player_id": "player1",
                "draft_status": "drafted",
                "fantasy_team": "Team A",
                "draft_order": 5,
            },
        )

        if response.status_code != 200:
            logger.debug(f"Update response: {response.status_code} - {response.text}")

        assert response.status_code == 200, f"Update failed: {response.text}"

        # Verify the player was updated
        updated_player = test_db.query(Player).filter(Player.player_id == "player1").first()
        assert updated_player is not None, "Player not found in database"
        assert (
            updated_player.draft_status == "drafted"
        ), f"Wrong draft status: {updated_player.draft_status}"
        assert updated_player.draft_order == 5, f"Wrong draft order: {updated_player.draft_order}"
        assert (
            updated_player.fantasy_team == "Team A"
        ), f"Wrong fantasy team: {updated_player.fantasy_team}"

    def test_batch_update_draft_status(self, test_client, sample_players, test_db):
        """Test batch updating multiple players' draft status."""
        # Draft multiple players
        response = test_client.post(
            "/api/draft/batch-draft-status",
            json={
                "updates": [
                    {
                        "player_id": "player2",
                        "draft_status": "drafted",
                        "fantasy_team": "Team B",
                        "draft_order": 1,
                    },
                    {
                        "player_id": "player3",
                        "draft_status": "drafted",
                        "fantasy_team": "Team C",
                        "draft_order": 2,
                    },
                ]
            },
        )

        if response.status_code != 200:
            logger.debug(f"Batch update response: {response.status_code} - {response.text}")

        assert response.status_code == 200, f"Batch update failed: {response.text}"

        # Verify both players were updated
        player2 = test_db.query(Player).filter(Player.player_id == "player2").first()
        player3 = test_db.query(Player).filter(Player.player_id == "player3").first()

        assert player2 is not None, "Player 2 not found"
        assert player3 is not None, "Player 3 not found"

        assert player2.draft_status == "drafted", f"Wrong draft status: {player2.draft_status}"
        assert player2.draft_order == 1, f"Wrong draft order: {player2.draft_order}"
        assert player2.fantasy_team == "Team B", f"Wrong fantasy team: {player2.fantasy_team}"

        assert player3.draft_status == "drafted", f"Wrong draft status: {player3.draft_status}"
        assert player3.draft_order == 2, f"Wrong draft order: {player3.draft_order}"
        assert player3.fantasy_team == "Team C", f"Wrong fantasy team: {player3.fantasy_team}"

    def test_auto_projection_after_draft(self, test_client, sample_players, test_db):
        """Test that rookie projections are automatically generated after draft."""
        # Draft a rookie with projection creation enabled
        response = test_client.post(
            "/api/draft/draft-status",
            json={
                "player_id": "player4",
                "draft_status": "drafted",
                "fantasy_team": "Team D",
                "draft_order": 10,
                "create_projection": True,  # Request projection creation
            },
        )

        if response.status_code != 200:
            logger.debug(
                f"Draft with projection response: {response.status_code} - {response.text}"
            )

        assert response.status_code == 200, f"Draft with projection failed: {response.text}"

        # Verify projection was created
        projection = test_db.query(Projection).filter(Projection.player_id == "player4").first()

        if projection is None:
            # Log debug info
            player = test_db.query(Player).filter(Player.player_id == "player4").first()
            logger.debug(f"Player in DB: {player.name if player else None}")
            logger.debug(f"Player rookie status: {player.is_rookie if player else None}")
            logger.debug(f"Player draft status: {player.draft_status if player else None}")

            # Check all projections
            all_projections = test_db.query(Projection).all()
            logger.debug(f"All projections: {len(all_projections)}")
            for p in all_projections:
                logger.debug(f"Projection: {p.projection_id} - Player: {p.player_id}")

        assert projection is not None, "No projection was created"
        assert projection.player_id == "player4", f"Wrong player ID: {projection.player_id}"
        assert projection.season is not None, "Season not set in projection"

    def test_get_draft_board(self, test_client, sample_players):
        """Test retrieving the draft board with player statuses."""
        response = test_client.get("/api/draft/draft-board")

        if response.status_code != 200:
            logger.debug(f"Draft board response: {response.status_code} - {response.text}")

        assert response.status_code == 200, f"Getting draft board failed: {response.text}"
        data = response.json()

        assert "players" in data, "Response missing 'players' key"
        assert len(data["players"]) == 4, f"Expected 4 players, got {len(data['players'])}"

        # Verify structure and content
        for player in data["players"]:
            assert "player_id" in player, f"Player missing player_id: {player}"
            assert "name" in player, f"Player missing name: {player}"
            assert "position" in player, f"Player missing position: {player}"
            assert "draft_status" in player, f"Player missing draft_status: {player}"
            assert (
                player["draft_status"] == "available"
            ), f"Player should be available, got {player['draft_status']}"

    def test_get_draft_board_filtered(self, test_client, sample_players, test_db):
        """Test retrieving filtered draft board."""
        # Mark player as drafted first
        player = test_db.query(Player).filter(Player.player_id == "player1").first()
        assert player is not None, "Player not found"
        player.draft_status = "drafted"
        player.fantasy_team = "Team A"
        test_db.commit()

        # Get only available players
        response = test_client.get("/api/draft/draft-board?status=available")

        if response.status_code != 200:
            logger.debug(f"Filtered draft board response: {response.status_code} - {response.text}")

        assert response.status_code == 200, f"Getting filtered draft board failed: {response.text}"
        data = response.json()

        assert "players" in data, "Response missing 'players' key"
        assert (
            len(data["players"]) == 3
        ), f"Expected 3 available players, got {len(data['players'])}"

        # Verify drafted player is not included
        player_ids = [p["player_id"] for p in data["players"]]
        assert "player1" not in player_ids, "Drafted player should not be included"

    def test_tracking_draft_progress(self, test_client, sample_players, test_db):
        """Test tracking overall draft progress."""
        # First, draft multiple players
        player1 = test_db.query(Player).filter(Player.player_id == "player1").first()
        player1.draft_status = "drafted"
        player1.draft_order = 1

        player2 = test_db.query(Player).filter(Player.player_id == "player2").first()
        player2.draft_status = "drafted"
        player2.draft_order = 2

        test_db.commit()

        # Get draft progress
        response = test_client.get("/api/draft/draft-progress")

        if response.status_code != 200:
            logger.debug(f"Draft progress response: {response.status_code} - {response.text}")

        assert response.status_code == 200, f"Getting draft progress failed: {response.text}"
        data = response.json()

        # Verify response structure
        assert "total_players" in data, "Response missing 'total_players'"
        assert "drafted_players" in data, "Response missing 'drafted_players'"
        assert "available_players" in data, "Response missing 'available_players'"
        assert "draft_positions_filled" in data, "Response missing 'draft_positions_filled'"

        # Verify counts
        assert data["total_players"] == 4, f"Expected 4 total players, got {data['total_players']}"
        assert (
            data["drafted_players"] == 2
        ), f"Expected 2 drafted players, got {data['drafted_players']}"
        assert (
            data["available_players"] == 2
        ), f"Expected 2 available players, got {data['available_players']}"

    def test_reset_draft_status(self, test_client, sample_players, test_db):
        """Test resetting draft status for all players."""
        # First, draft a player
        player = test_db.query(Player).filter(Player.player_id == "player1").first()
        player.draft_status = "drafted"
        player.fantasy_team = "Team A"
        test_db.commit()

        # Reset all draft statuses
        response = test_client.post("/api/draft/reset-draft")

        if response.status_code != 200:
            logger.debug(f"Reset draft response: {response.status_code} - {response.text}")

        assert response.status_code == 200, f"Resetting draft status failed: {response.text}"

        # Verify all players are reset to available
        players = test_db.query(Player).all()
        for player in players:
            assert (
                player.draft_status == "available"
            ), f"Player should be available, got {player.draft_status}"
            assert (
                player.fantasy_team is None or player.fantasy_team == ""
            ), f"Fantasy team should be empty, got {player.fantasy_team}"

    def test_undo_last_draft_pick(self, test_client, sample_players, test_db):
        """Test undoing the last draft pick."""
        # Draft players in sequence
        for i, player_id in enumerate(["player1", "player2", "player3"]):
            player = test_db.query(Player).filter(Player.player_id == player_id).first()
            assert player is not None, f"Player {player_id} not found"
            player.draft_status = "drafted"
            player.draft_order = i + 1
            player.fantasy_team = f"Team {i+1}"
        test_db.commit()

        # Undo last pick
        response = test_client.post("/api/draft/undo-draft")

        if response.status_code != 200:
            logger.debug(f"Undo draft response: {response.status_code} - {response.text}")

        assert response.status_code == 200, f"Undoing last draft pick failed: {response.text}"

        # Verify the last drafted player is now available
        player3 = test_db.query(Player).filter(Player.player_id == "player3").first()
        assert (
            player3.draft_status == "available"
        ), f"Player 3 should be available, got {player3.draft_status}"

        # But earlier picks remain drafted
        player1 = test_db.query(Player).filter(Player.player_id == "player1").first()
        player2 = test_db.query(Player).filter(Player.player_id == "player2").first()
        assert (
            player1.draft_status == "drafted"
        ), f"Player 1 should be drafted, got {player1.draft_status}"
        assert (
            player2.draft_status == "drafted"
        ), f"Player 2 should be drafted, got {player2.draft_status}"
