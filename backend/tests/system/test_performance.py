import pytest
import time
import json
import logging
import uuid
from typing import List
from pathlib import Path
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine, and_, or_
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from backend.main import app
from backend.database.models import Player, Projection, BaseStat, Scenario
from backend.database.database import Base, get_db
from backend.services.cache_service import get_cache, CacheService

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TestPerformance:
    """System tests for performance benchmarking and optimization."""
    
    @pytest.fixture(scope="function")
    def test_db_engine(self):
        """Create a test database engine using a unique file-based DB for each test."""
        # Create a file-based database that will be deleted after the test
        test_db_file = f"/tmp/test_db_{uuid.uuid4()}.sqlite"
        db_url = f"sqlite:///{test_db_file}"
        logger.debug(f"Creating test database at: {db_url}")
        
        engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
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
        from backend.api.routes import players_router, projections_router, overrides_router, scenarios_router
        from backend.api.routes.batch import router as batch_router
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
    def large_player_dataset(self, test_db) -> List[Player]:
        """Create a large dataset of players for performance testing."""
        fixture_id = str(uuid.uuid4())[:8]
        logger.debug(f"Setting up large_player_dataset fixture for performance tests (ID: {fixture_id})")
        
        teams = ["ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE", "DAL", "DEN", 
                "DET", "GB", "HOU", "IND", "JAX", "KC", "LV", "LAC", "LAR", "MIA", 
                "MIN", "NE", "NO", "NYG", "NYJ", "PHI", "PIT", "SEA", "SF", "TB", 
                "TEN", "WAS"]
        positions = ["QB", "RB", "WR", "TE"]
        
        players = []
        # Create 500 players (much larger than typical load)
        for i in range(500):
            player = Player(
                player_id=f"player{i}",
                name=f"Player {i}",
                team=teams[i % len(teams)],
                position=positions[i % len(positions)]
            )
            players.append(player)
            test_db.add(player)
        
        test_db.commit()
        logger.debug(f"Created {len(players)} players for performance testing")
        
        # Verify players were created
        db_players = test_db.query(Player).all()
        logger.debug(f"Players in DB: {len(db_players)}")
        assert len(db_players) == 500, "Not all test players were saved"
        
        return players
    
    @pytest.fixture(scope="function")
    def large_projection_dataset(self, test_db, large_player_dataset):
        """Create a large dataset of projections for performance testing."""
        fixture_id = str(uuid.uuid4())[:8]
        logger.debug(f"Setting up large_projection_dataset fixture for performance tests (ID: {fixture_id})")
        
        # Create a base scenario
        base_scenario = Scenario(
            scenario_id="base_scenario",
            name="Base Scenario", 
            description="Base projections",
            is_baseline=True
        )
        test_db.add(base_scenario)
        test_db.flush()
        
        # Create projections for all players
        projections = []
        season = 2025
        
        for i, player in enumerate(large_player_dataset):
            projection = Projection(
                projection_id=f"proj{i}",
                player_id=player.player_id,
                scenario_id="base_scenario",
                season=season,
                games=17,
                half_ppr=100 + (i % 50),  # Varied fantasy points
            )
            
            # Add position-specific stats
            if player.position == "QB":
                projection.pass_attempts = 500 + (i % 100)
                projection.completions = 300 + (i % 100)
                projection.pass_yards = 4000 + (i % 1000)
                projection.pass_td = 30 + (i % 20)
                projection.interceptions = 10 + (i % 10)
                projection.rush_attempts = 30 + (i % 20)
                projection.rush_yards = 200 + (i % 100)
                projection.rush_td = 2 + (i % 3)
            elif player.position == "RB":
                projection.rush_attempts = 200 + (i % 100)
                projection.rush_yards = 900 + (i % 400)
                projection.rush_td = 6 + (i % 8)
                projection.receptions = 30 + (i % 30)
                projection.targets = 40 + (i % 40)
                projection.receiving_yards = 250 + (i % 200)
                projection.receiving_td = 1 + (i % 3)
            elif player.position in ["WR", "TE"]:
                projection.receptions = 60 + (i % 40)
                projection.targets = 90 + (i % 60)
                projection.receiving_yards = 800 + (i % 400)
                projection.receiving_td = 5 + (i % 7)
                projection.rush_attempts = 5 + (i % 10)
                projection.rush_yards = 30 + (i % 40)
                projection.rush_td = 0 + (i % 2)
            
            projections.append(projection)
            test_db.add(projection)
            
            # Commit in batches to avoid SQLite issues with large transactions
            if i % 100 == 0:
                test_db.commit()
        
        test_db.commit()
        logger.debug(f"Created {len(projections)} projections for performance testing")
        
        return {
            "scenario": base_scenario,
            "projections": projections,
            "season": season
        }
    
    def test_player_list_response_time(self, test_client, large_player_dataset):
        """Test response time for player listing endpoint with a large dataset."""
        # Clear cache to ensure fresh test
        cache = get_cache()
        cache.clear()
        
        # Measure response time
        start_time = time.time()
        response = test_client.get("/api/players/players/")
        end_time = time.time()
        
        # Verify response is correct
        assert response.status_code == 200, f"Response failed: {response.text}"
        data = response.json()
        
        assert "players" in data, "Response missing 'players' key"
        assert len(data["players"]) > 0, "No players returned"
        
        # Check response time is acceptable (adjust threshold as needed)
        response_time = end_time - start_time
        logger.info(f"Player list response time: {response_time:.4f} seconds")
        
        # Use a threshold that's reasonable for the test environment
        assert response_time < 1.0, f"Response time too slow: {response_time:.4f} seconds"
    
    def test_projection_list_response_time(self, test_client, large_projection_dataset):
        """Test response time for projection listing endpoint with a large dataset."""
        # Clear cache to ensure fresh test
        cache = get_cache()
        cache.clear()
        
        # Measure response time
        start_time = time.time()
        response = test_client.get(f"/api/projections/projections/?scenario_id={large_projection_dataset['scenario'].scenario_id}")
        end_time = time.time()
        
        # Verify response is correct
        assert response.status_code == 200, f"Response failed: {response.text}"
        data = response.json()
        
        assert len(data) > 0, "No projections returned"
        
        # Check response time is acceptable
        response_time = end_time - start_time
        logger.info(f"Projection list response time: {response_time:.4f} seconds")
        
        # Use a threshold that's reasonable for the test environment
        assert response_time < 2.0, f"Response time too slow: {response_time:.4f} seconds"
    
    def test_caching_effectiveness(self, test_client, large_projection_dataset):
        """Test that caching improves response times for repeated queries."""
        # Clear cache to ensure fresh test
        cache = get_cache()
        cache.clear()
        
        # First request (uncached)
        scenario_id = large_projection_dataset["scenario"].scenario_id
        
        start_time = time.time()
        response1 = test_client.get(f"/api/projections/projections/?scenario_id={scenario_id}&position=QB")
        end_time = time.time()
        uncached_time = end_time - start_time
        
        # Second request (should be cached)
        start_time = time.time()
        response2 = test_client.get(f"/api/projections/projections/?scenario_id={scenario_id}&position=QB")
        end_time = time.time()
        cached_time = end_time - start_time
        
        # Verify both responses are correct
        assert response1.status_code == 200, f"First response failed: {response1.text}"
        assert response2.status_code == 200, f"Second response failed: {response2.text}"
        
        # Check that cached response is significantly faster
        logger.info(f"Uncached response time: {uncached_time:.4f} seconds")
        logger.info(f"Cached response time: {cached_time:.4f} seconds")
        logger.info(f"Cache speedup factor: {uncached_time/cached_time:.2f}x")
        
        # The cached response should be at least 40% faster
        assert cached_time < uncached_time * 0.6, f"Caching not effective enough: {cached_time:.4f} vs {uncached_time:.4f}"
    
    def test_filtered_query_performance(self, test_client, large_projection_dataset):
        """Test performance of filtered queries with different parameters."""
        # Clear cache to ensure fresh test
        cache = get_cache()
        cache.clear()
        
        scenario_id = large_projection_dataset["scenario"].scenario_id
        
        # Test various filter combinations
        test_filters = [
            f"scenario_id={scenario_id}&position=QB",
            f"scenario_id={scenario_id}&position=RB",
            f"scenario_id={scenario_id}&team=KC",
            f"scenario_id={scenario_id}&half_ppr_min=120",
            f"scenario_id={scenario_id}&position=WR&team=DAL",
            f"scenario_id={scenario_id}&position=TE&half_ppr_min=100&half_ppr_max=150"
        ]
        
        for filter_str in test_filters:
            # Measure response time
            start_time = time.time()
            response = test_client.get(f"/api/projections/projections/?{filter_str}")
            end_time = time.time()
            
            # Verify response is correct
            assert response.status_code == 200, f"Response failed for filter '{filter_str}': {response.text}"
            
            # Check response time is acceptable
            response_time = end_time - start_time
            logger.info(f"Filter '{filter_str}' response time: {response_time:.4f} seconds")
            
            # Use a threshold that's reasonable for the test environment
            assert response_time < 1.0, f"Filtered query too slow: {response_time:.4f} seconds for {filter_str}"
    
    def test_memory_usage_with_large_dataset(self, test_client, large_projection_dataset):
        """Test memory usage monitoring with large dataset operations."""
        # Clear cache to ensure fresh test
        cache = get_cache()
        cache.clear()
        
        # Make a request that loads a large dataset
        scenario_id = large_projection_dataset["scenario"].scenario_id
        response = test_client.get(f"/api/projections/projections/?scenario_id={scenario_id}")
        assert response.status_code == 200, f"Response failed: {response.text}"
        
        # Check cache stats after large data load
        cache_stats = cache.get_stats()
        logger.info(f"Cache stats after loading large dataset: {json.dumps(cache_stats, indent=2)}")
        
        # Memory usage should be reasonable
        assert cache_stats["size_mb"] < 10, f"Cache using too much memory: {cache_stats['size_mb']} MB"
        
        # Check active entries
        assert cache_stats["active_entries"] > 0, "No active cache entries"
        assert cache_stats["expired_entries"] == 0, "Should have no expired entries"
    
    def test_batch_operation_performance(self, test_client, large_player_dataset, test_db):
        """Test performance of batch operations."""
        # Prepare a batch of updates (smaller batch for SQLite performance)
        updates = []
        for i in range(50):  # Update 50 players
            updates.append({
                "player_id": f"player{i}",
                "status": "active",
                "depth_chart_position": i % 4 + 1
            })
        
        # Measure batch update performance
        start_time = time.time()
        response = test_client.post(
            "/api/players/players/batch-update",
            json={"updates": updates}
        )
        end_time = time.time()
        
        # Log the response for debugging
        if response.status_code != 200:
            logger.debug(f"Batch update response: {response.status_code} - {response.text}")
        
        # Verify response is correct
        assert response.status_code == 200, f"Batch update failed: {response.text}"
        
        # Check operation time is acceptable
        operation_time = end_time - start_time
        logger.info(f"Batch update operation time: {operation_time:.4f} seconds")
        
        # Use a threshold that's reasonable for the test environment
        assert operation_time < 3.0, f"Batch operation too slow: {operation_time:.4f} seconds"
    
    def test_cache_cleanup_performance(self, test_db):
        """Test performance of cache cleanup operations."""
        # Create a test cache with short TTL
        cache = CacheService(ttl_seconds=1)
        
        # Add many cache entries
        for i in range(1000):
            cache.set(f"test_key_{i}", f"test_value_{i}")
        
        # Sleep to expire some entries
        time.sleep(1.1)
        
        # Add more entries that won't expire
        for i in range(1000, 2000):
            cache.set(f"test_key_{i}", f"test_value_{i}", ttl_seconds=60)
        
        # Measure cleanup performance
        start_time = time.time()
        removed = cache.cleanup()
        end_time = time.time()
        
        # Verify cleanup was successful
        assert removed == 1000, f"Expected 1000 removals, got {removed}"
        
        # Check cleanup time is acceptable
        cleanup_time = end_time - start_time
        logger.info(f"Cache cleanup time for 1000 entries: {cleanup_time:.4f} seconds")
        
        # Use a threshold that's reasonable for the test environment
        assert cleanup_time < 0.5, f"Cache cleanup too slow: {cleanup_time:.4f} seconds"
    
    def test_concurrent_request_performance(self, test_client, large_projection_dataset):
        """Test handling multiple concurrent requests efficiently."""
        import threading
        from queue import Queue
        
        # Clear cache to ensure fresh test
        cache = get_cache()
        cache.clear()
        
        scenario_id = large_projection_dataset["scenario"].scenario_id
        
        # Different queries to test concurrently
        urls = [
            f"/api/projections/projections/?scenario_id={scenario_id}&position=QB",
            f"/api/projections/projections/?scenario_id={scenario_id}&position=RB",
            f"/api/projections/projections/?scenario_id={scenario_id}&position=WR",
            f"/api/projections/projections/?scenario_id={scenario_id}&position=TE",
            f"/api/players/players/",
            f"/api/players/players/?position=QB",
            f"/api/players/players/?position=RB",
            f"/api/players/players/?team=DAL"
        ]
        
        # Queue for storing results
        results = Queue()
        
        # Thread function
        def make_request(url, idx):
            start_time = time.time()
            response = test_client.get(url)
            end_time = time.time()
            
            results.put({
                "url": url,
                "status": response.status_code,
                "time": end_time - start_time,
                "idx": idx
            })
        
        # Create and start threads
        threads = []
        for i, url in enumerate(urls):
            thread = threading.Thread(target=make_request, args=(url, i))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to finish
        for thread in threads:
            thread.join()
        
        # Process results
        all_results = []
        while not results.empty():
            all_results.append(results.qget())
        
        # Sort by original order
        all_results.sort(key=lambda x: x["idx"])
        
        # Check all responses were successful
        for result in all_results:
            assert result["status"] == 200, f"Request failed: {result['url']}"
            logger.info(f"Request {result['url']} time: {result['time']:.4f} seconds")
            
            # Each individual request should be reasonably fast
            assert result["time"] < 2.0, f"Request too slow: {result['time']:.4f} seconds for {result['url']}"
        
        # Calculate total parallel execution time
        total_time = max(result["time"] for result in all_results)
        serial_time = sum(result["time"] for result in all_results)
        
        logger.info(f"Total concurrent execution time: {total_time:.4f} seconds")
        logger.info(f"Equivalent serial execution time: {serial_time:.4f} seconds")
        logger.info(f"Parallelization speedup: {serial_time/total_time:.2f}x")
        
        # The speedup should be significant (though less than perfect linear scaling)
        assert total_time < serial_time * 0.5, "Insufficient parallelization performance"