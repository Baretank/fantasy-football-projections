# backend/tests/conftest.py
import os
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import uuid
import pandas as pd

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from backend.database.database import Base
from backend.database.models import Player, BaseStat, TeamStat, Projection
from backend.services.team_stat_service import TeamStatsService

@pytest.fixture(scope="function")
def mock_stats_provider():
    """Provide the mock stats function."""
    return get_mock_team_stats

@pytest.fixture(scope="function")
def team_stats_service(test_db, mock_stats_provider):
    """Create TeamStatsService with mock provider."""
    service = TeamStatsService(test_db)
    service.set_stats_provider(mock_stats_provider)
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
        carries=400,                 # Same as rush_attempts
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