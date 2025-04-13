# backend/tests/conftest.py
import os
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import uuid
import pandas as pd
from fastapi.testclient import TestClient
import json
import logging
from typing import Generator

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from backend.database.database import Base, get_db
from backend.database.models import Player, BaseStat, TeamStat, Projection
from backend.services.team_stat_service import TeamStatService
from backend.main import app as main_app

@pytest.fixture(scope="function")
def mock_stats_provider():
    """Provide the mock stats function."""
    return get_mock_team_stats

@pytest.fixture(scope="function")
def team_stats_service(test_db, mock_stats_provider):
    """Create TeamStatService with mock provider."""
    service = TeamStatService(test_db)
    # No need to set stats_provider directly now, as the service will use NFLDataPyAdapter
    return service

# Create in-memory test database
TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="function")
def test_engine():
    """Create a test database engine."""
    engine = create_engine(
        TEST_SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def test_db(test_engine):
    """Create a test database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="function")
def test_app(test_db):
    """Create a test app with database dependency overridden."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    # Override the dependency for testing
    main_app.dependency_overrides[get_db] = override_get_db
    
    # Log out all the routes for debugging
    routes = []
    for route in main_app.routes:
        routes.append(f"{route.methods} {route.path}")
    logger.debug(f"Test app routes: {routes}")
    
    return main_app

@pytest.fixture(scope="function")
def client(test_app) -> TestClient:
    """Create a test client using the test app."""
    with TestClient(test_app) as client:
        yield client

@pytest.fixture(scope="function")
def log_route_endpoints(test_app):
    """Debug tool to log detailed information about route endpoints."""
    routes_info = []
    
    for route in test_app.routes:
        route_info = {
            "path": route.path,
            "methods": list(route.methods) if route.methods else None,
            "name": route.name,
            "dependency_names": [],
        }
        
        # Try to get handler info
        if hasattr(route, "endpoint"):
            try:
                route_info["endpoint_name"] = route.endpoint.__name__
                route_info["endpoint_module"] = route.endpoint.__module__
            except AttributeError:
                route_info["endpoint_name"] = "unknown"
                route_info["endpoint_module"] = "unknown"
        
        routes_info.append(route_info)
    
    # Log detailed route information
    logger.debug("Detailed route handlers:")
    for route in routes_info:
        logger.debug(json.dumps(route, indent=2))
    
    # Specifically check for player routes
    player_routes = [r for r in routes_info if r["path"].startswith("/api/players")]
    logger.debug(f"Found {len(player_routes)} player routes")
    
    return routes_info

@pytest.fixture(scope="function")
def sample_players(test_db):
    """Create sample players for testing."""
    players = [
        Player(
            player_id=str(uuid.uuid4()),
            name="Patrick Mahomes",
            team="KC",
            position="QB"
        ),
        Player(
            player_id=str(uuid.uuid4()),
            name="Travis Kelce",
            team="KC",
            position="TE"
        ),
        Player(
            player_id=str(uuid.uuid4()),
            name="Brock Purdy",
            team="SF",
            position="QB"
        ),
        Player(
            player_id=str(uuid.uuid4()),
            name="Christian McCaffrey",
            team="SF",
            position="RB"
        )
    ]
    
    for player in players:
        test_db.add(player)
    test_db.commit()
    
    player_ids = {player.name: player.player_id for player in players}
    return {"players": players, "ids": player_ids}

def get_mock_team_stats(season: int) -> pd.DataFrame:
    """Mock implementation for team stats."""
    mock_data = {
        'Tm': ['KC', 'SF', 'BAL', 'BUF'],
        'Plays': [1000, 1000, 1000, 1000],  # Total plays should match pass + rush
        'Pass%': [0.60, 0.55, 0.58, 0.61],  # Percentage should match pass_attempts/plays
        'PassAtt': [600, 550, 580, 610],    # 60% of 1000 plays = 600 attempts, etc.
        'PassYds': [4250, 4200, 4100, 4150],
        'PassTD': [30, 34, 28, 32],
        'TD%': [0.05, 0.0618, 0.0483, 0.0525],  # PassTD/PassAtt
        'RushAtt': [400, 450, 420, 390],    # Remaining plays (1000 - PassAtt)
        'RushYds': [1600, 2250, 2100, 1560],
        'RushTD': [19, 28, 22, 18],
        'Y/A': [4.0, 5.0, 5.0, 4.0],        # RushYds/RushAtt
        'Tgt': [600, 550, 580, 610],        # Same as PassAtt
        'Rec': [390, 360, 375, 397],
        'RecYds': [4250, 4200, 4100, 4150], # Same as PassYds
        'RecTD': [30, 34, 28, 32],          # Same as PassTD
        'Rank': [1, 2, 3, 4]
    }
    return pd.DataFrame(mock_data)

@pytest.fixture(scope="function")
def team_stats_2024(test_db):
    """Create 2024 team stats for testing."""
    stats = TeamStat(
        team_stat_id=str(uuid.uuid4()),
        team="KC",
        season=2024,
        plays=1000,                  # Changed to match total
        pass_percentage=0.60,        # Changed to match ratio
        pass_attempts=600,           # Changed to match ratio
        pass_yards=4250,
        pass_td=30,
        pass_td_rate=0.05,          # 30/600
        rush_attempts=400,           # Changed to match total
        rush_yards=1600,
        rush_td=19,
        rush_yards_per_carry=4.0,    # 1600/400
        targets=600,                 # Same as pass_attempts
        receptions=390,
        rec_yards=4250,             # Same as pass_yards
        rec_td=30,                  # Same as pass_td
        rank=1
    )
    test_db.add(stats)
    test_db.commit()
    return stats

@pytest.fixture(scope="function")
def sample_stats(test_db, sample_players):
    """Create sample player statistics for testing."""
    # Get player IDs
    mahomes_id = sample_players["ids"]["Patrick Mahomes"]
    kelce_id = sample_players["ids"]["Travis Kelce"]
    purdy_id = sample_players["ids"]["Brock Purdy"]
    mccaffrey_id = sample_players["ids"]["Christian McCaffrey"]
    
    # Create QB stats for Mahomes
    mahomes_stats = [
        BaseStat(player_id=mahomes_id, season=2023, stat_type="pass_attempts", value=584),
        BaseStat(player_id=mahomes_id, season=2023, stat_type="completions", value=401),
        BaseStat(player_id=mahomes_id, season=2023, stat_type="pass_yards", value=4183),
        BaseStat(player_id=mahomes_id, season=2023, stat_type="pass_td", value=27),
        BaseStat(player_id=mahomes_id, season=2023, stat_type="interceptions", value=14),
        BaseStat(player_id=mahomes_id, season=2023, stat_type="rush_attempts", value=75),
        BaseStat(player_id=mahomes_id, season=2023, stat_type="rush_yards", value=389)
    ]
    
    # Create QB stats for Purdy
    purdy_stats = [
        BaseStat(player_id=purdy_id, season=2023, stat_type="pass_attempts", value=444),
        BaseStat(player_id=purdy_id, season=2023, stat_type="completions", value=308),
        BaseStat(player_id=purdy_id, season=2023, stat_type="pass_yards", value=4280),
        BaseStat(player_id=purdy_id, season=2023, stat_type="pass_td", value=31),
        BaseStat(player_id=purdy_id, season=2023, stat_type="interceptions", value=11),
        BaseStat(player_id=purdy_id, season=2023, stat_type="rush_attempts", value=36),
        BaseStat(player_id=purdy_id, season=2023, stat_type="rush_yards", value=144)
    ]
    
    # Create TE stats for Kelce
    kelce_stats = [
        BaseStat(player_id=kelce_id, season=2023, stat_type="targets", value=121),
        BaseStat(player_id=kelce_id, season=2023, stat_type="receptions", value=93),
        BaseStat(player_id=kelce_id, season=2023, stat_type="rec_yards", value=984),
        BaseStat(player_id=kelce_id, season=2023, stat_type="rec_td", value=5),
        BaseStat(player_id=kelce_id, season=2023, stat_type="rush_attempts", value=2),
        BaseStat(player_id=kelce_id, season=2023, stat_type="rush_yards", value=5),
        BaseStat(player_id=kelce_id, season=2023, stat_type="rush_td", value=0)
    ]
    
    # Create RB stats for McCaffrey
    mccaffrey_stats = [
        BaseStat(player_id=mccaffrey_id, season=2023, stat_type="rush_attempts", value=272),
        BaseStat(player_id=mccaffrey_id, season=2023, stat_type="rush_yards", value=1459),
        BaseStat(player_id=mccaffrey_id, season=2023, stat_type="rush_td", value=14),
        BaseStat(player_id=mccaffrey_id, season=2023, stat_type="targets", value=83),
        BaseStat(player_id=mccaffrey_id, season=2023, stat_type="receptions", value=67),
        BaseStat(player_id=mccaffrey_id, season=2023, stat_type="rec_yards", value=564),
        BaseStat(player_id=mccaffrey_id, season=2023, stat_type="rec_td", value=7)
    ]
    
    # Add all stats to the database
    all_stats = mahomes_stats + purdy_stats + kelce_stats + mccaffrey_stats
    for stat in all_stats:
        test_db.add(stat)
    test_db.commit()
    
    return all_stats