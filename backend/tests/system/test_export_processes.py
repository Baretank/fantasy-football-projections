import pytest
import os
import json
import logging
import uuid
import pandas as pd
from io import StringIO
from pathlib import Path
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine, and_, or_
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from backend.main import app
from backend.database.models import Player, Projection, BaseStat, Scenario
from backend.database.database import Base, get_db

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestExportProcesses:
    """System tests for export functionality"""

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

        # Include all routers as in the main app
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
            # Print available routes for debugging
            route_paths = [str(route.path) for route in test_app.routes if hasattr(route, "path")]
            batch_routes = [r for r in route_paths if "/api/batch" in r]
            logger.debug(f"Batch routes: {batch_routes}")
            yield client

        logger.debug("Test client fixture cleanup complete")

    @pytest.fixture(scope="function")
    def sample_data(self, test_db):
        """Create sample projection data for testing exports."""
        fixture_id = str(uuid.uuid4())[:8]
        logger.debug(f"Setting up sample_data fixture for export tests (ID: {fixture_id})")

        # Create a base scenario
        base_scenario = Scenario(
            scenario_id="base_scenario",
            name="Base Scenario",
            description="Base projections",
            is_baseline=True,
        )
        test_db.add(base_scenario)
        test_db.flush()

        # Create sample players
        players = [
            Player(player_id="player1", name="Patrick Mahomes", team="KC", position="QB"),
            Player(player_id="player2", name="Travis Kelce", team="KC", position="TE"),
            Player(player_id="player3", name="Christian McCaffrey", team="SF", position="RB"),
        ]

        for player in players:
            test_db.add(player)
        test_db.flush()

        # Create projections
        projections = [
            Projection(
                projection_id="proj1",
                player_id="player1",
                scenario_id="base_scenario",
                season=2025,
                games=17,
                half_ppr=350.5,
                pass_attempts=580,
                completions=380,
                pass_yards=4800,
                pass_td=38,
                interceptions=10,
                rush_attempts=60,
                rush_yards=350,
                rush_td=3,
                receptions=0,
                targets=0,
                rec_yards=0,
                rec_td=0,
                fumbles=2,
            ),
            Projection(
                projection_id="proj2",
                player_id="player2",
                scenario_id="base_scenario",
                season=2025,
                games=16,
                half_ppr=205.3,
                pass_attempts=0,
                completions=0,
                pass_yards=0,
                pass_td=0,
                interceptions=0,
                rush_attempts=0,
                rush_yards=0,
                rush_td=0,
                receptions=90,
                targets=120,
                rec_yards=950,
                rec_td=10,
                fumbles=1,
            ),
            Projection(
                projection_id="proj3",
                player_id="player3",
                scenario_id="base_scenario",
                season=2025,
                games=16,
                half_ppr=310.4,
                pass_attempts=0,
                completions=0,
                pass_yards=0,
                pass_td=0,
                interceptions=0,
                rush_attempts=280,
                rush_yards=1400,
                rush_td=14,
                receptions=60,
                targets=75,
                rec_yards=550,
                rec_td=4,
                fumbles=2,
            ),
        ]

        for projection in projections:
            test_db.add(projection)

        test_db.commit()
        logger.debug(
            f"Created sample data with {len(players)} players and {len(projections)} projections"
        )

        return {"scenario": base_scenario, "players": players, "projections": projections}

    def test_export_csv_format(self, test_client, sample_data, test_db):
        """Test projections export to CSV format."""
        # Verify data exists in the database
        scenario_id = sample_data["scenario"].scenario_id
        projections = test_db.query(Projection).filter(Projection.scenario_id == scenario_id).all()
        logger.debug(f"Projections in DB: {len(projections)}")
        assert len(projections) == 3, "Test data not properly set up"

        # Call export endpoint with correct path (note the duplicate 'batch' is intentional)
        response = test_client.post(
            "/api/batch/batch/export",
            json={"filters": {"scenario_id": scenario_id, "season": 2025}},
            params={"format": "csv"},
        )

        if response.status_code != 200:
            logger.debug(f"Export response: {response.status_code} - {response.text}")

        assert response.status_code == 200, f"Export failed: {response.text}"
        assert "text/csv" in response.headers.get("Content-Type", ""), "Wrong content type"
        assert "Content-Disposition" in response.headers, "No Content-Disposition header"

        # Parse the CSV content
        csv_data = response.content.decode("utf-8")

        # Save CSV to a file for debugging
        with open("/tmp/export_test.csv", "w") as f:
            f.write(csv_data)

        # Read the CSV
        df = pd.read_csv(StringIO(csv_data))

        # Verify content
        assert len(df) == 3, f"Expected 3 rows, got {len(df)}"
        assert "name" in df.columns, "Missing 'name' column"
        assert "position" in df.columns, "Missing 'position' column"
        assert "half_ppr" in df.columns, "Missing 'half_ppr' column"

        # Check data for Mahomes
        mahomes_rows = df[df["name"] == "Patrick Mahomes"]
        assert len(mahomes_rows) > 0, "Mahomes not found in export"
        mahomes_row = mahomes_rows.iloc[0]
        assert mahomes_row["position"] == "QB", f"Wrong position: {mahomes_row['position']}"
        assert (
            abs(float(mahomes_row["half_ppr"]) - 350.5) < 0.1
        ), f"Wrong fantasy points: {mahomes_row['half_ppr']}"
        assert (
            int(mahomes_row["pass_attempts"]) == 580
        ), f"Wrong pass attempts: {mahomes_row['pass_attempts']}"

    def test_export_json_format(self, test_client, sample_data):
        """Test projections export to JSON format."""
        # Call export endpoint with correct path (note the duplicate 'batch' is intentional)
        scenario_id = sample_data["scenario"].scenario_id
        response = test_client.post(
            "/api/batch/batch/export",
            json={"filters": {"scenario_id": scenario_id, "season": 2025}},
            params={"format": "json"},
        )

        if response.status_code != 200:
            logger.debug(f"Export response: {response.status_code} - {response.text}")

        assert response.status_code == 200, f"Export failed: {response.text}"
        assert "application/json" in response.headers.get("Content-Type", ""), "Wrong content type"

        # Parse the JSON content
        data = response.json()

        # Save JSON to a file for debugging
        with open("/tmp/export_test.json", "w") as f:
            json.dump(data, f, indent=2)

        # Verify content based on the actual implementation
        # The API returns a list of projections directly, not wrapped in a "projections" key
        assert isinstance(data, list), "Expected a list of projections"
        assert len(data) == 3, f"Expected 3 projections, got {len(data)}"

        # Check data for McCaffrey
        mccaffrey = None
        for p in data:
            if p["name"] == "Christian McCaffrey":
                mccaffrey = p
                break

        assert mccaffrey is not None, "McCaffrey not found in export"
        assert mccaffrey["position"] == "RB", f"Wrong position: {mccaffrey['position']}"
        assert (
            abs(mccaffrey["half_ppr"] - 310.4) < 0.1
        ), f"Wrong fantasy points: {mccaffrey['half_ppr']}"

        # Confirm we have either rush_attempts or carries (depending on how the export formats it)
        # First check for rush_attempts
        rush_attempts = mccaffrey.get("rush_attempts")
        if rush_attempts is None:
            # If not available, check for carries which might be used instead
            rush_attempts = mccaffrey.get("carries")

        assert rush_attempts == 280, f"Wrong rush attempts: {rush_attempts}"
        assert mccaffrey["rec_td"] == 4, f"Wrong receiving TDs: {mccaffrey['rec_td']}"

    def test_export_filtered_by_position(self, test_client, sample_data):
        """Test exporting projections filtered by position."""
        # Call export endpoint with position filter using correct path (note the duplicate 'batch' is intentional)
        scenario_id = sample_data["scenario"].scenario_id
        response = test_client.post(
            "/api/batch/batch/export",
            json={"filters": {"scenario_id": scenario_id, "position": "QB"}},
            params={"format": "json"},
        )

        if response.status_code != 200:
            logger.debug(f"Export response: {response.status_code} - {response.text}")

        assert response.status_code == 200, f"Export failed: {response.text}"

        # Parse the JSON content
        data = response.json()

        # Verify content
        assert isinstance(data, list), "Expected a list of projections"
        assert len(data) == 1, f"Expected 1 QB, got {len(data)}"
        assert data[0]["name"] == "Patrick Mahomes", f"Wrong player: {data[0]['name']}"
        assert data[0]["position"] == "QB", f"Wrong position: {data[0]['position']}"

    def test_export_completeness(self, test_client, sample_data):
        """Test that all relevant fields are included in exports."""
        # Call export endpoint to test completeness with correct path (note the duplicate 'batch' is intentional)
        scenario_id = sample_data["scenario"].scenario_id
        response = test_client.post(
            "/api/batch/batch/export",
            json={"filters": {"scenario_id": scenario_id, "season": 2025}},
            params={"format": "json"},
        )

        if response.status_code != 200:
            logger.debug(f"Export response: {response.status_code} - {response.text}")

        assert response.status_code == 200, f"Export failed: {response.text}"

        # Parse the JSON content
        data = response.json()

        # Get first projection
        assert len(data) > 0, "No projections in export"
        projection = data[0]

        # Check that all important fields are included
        essential_fields = ["player_id", "name", "team", "position", "half_ppr", "games"]

        # Check for all essential fields
        for field in essential_fields:
            assert field in projection, f"Field {field} missing from export"

        # Check for position-specific fields based on the position of the first projection
        if projection["position"] == "QB":
            qb_fields = ["pass_yards", "pass_td", "interceptions"]
            for field in qb_fields:
                assert field in projection, f"QB field {field} missing from export"

        if projection["position"] in ["RB", "WR"]:
            skill_fields = ["rec_yards", "rec_td"]
            for field in skill_fields:
                assert field in projection, f"Skill position field {field} missing from export"
