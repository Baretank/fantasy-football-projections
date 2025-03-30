import pytest
import asyncio
import uuid
import pandas as pd
from sqlalchemy.orm import Session
from unittest.mock import patch, MagicMock
from backend.services.data_import_service import DataImportService
from backend.services.batch_service import BatchService
from backend.database.models import Player, BaseStat, ImportLog

class TestBatchImportFunctionality:
    @pytest.fixture(scope="function")
    def data_service(self, test_db):
        """Create DataImportService instance for testing."""
        return DataImportService(test_db)
    
    @pytest.fixture(scope="function")
    def batch_service(self, test_db):
        """Create BatchService instance for testing."""
        return BatchService(test_db)
    
    @pytest.fixture(scope="function")
    def sample_players(self, test_db):
        """Create sample players for testing batch import."""
        qbs = [
            Player(player_id=str(uuid.uuid4()), name="P. Mahomes", team="KC", position="QB"),
            Player(player_id=str(uuid.uuid4()), name="J. Allen", team="BUF", position="QB"),
            Player(player_id=str(uuid.uuid4()), name="J. Burrow", team="CIN", position="QB"),
            Player(player_id=str(uuid.uuid4()), name="L. Jackson", team="BAL", position="QB"),
            Player(player_id=str(uuid.uuid4()), name="T. Lawrence", team="JAX", position="QB")
        ]
        
        for player in qbs:
            test_db.add(player)
        
        test_db.commit()
        return qbs
    
    @pytest.mark.asyncio
    @patch.object(DataImportService, '_import_player_data')
    async def test_batch_import_position(self, mock_import, data_service, batch_service, sample_players):
        """Test importing a batch of players by position."""
        # Set up mock for _import_player_data
        async def mock_import_player(player_id, season):
            # Simulate successful import
            return True
        
        mock_import.side_effect = mock_import_player
        
        # Get QBs for batch import
        qb_ids = [player.player_id for player in sample_players]
        
        # Test batch import
        results = await batch_service.process_batch(
            service=data_service,
            method_name="_import_player_data",
            items=qb_ids,
            season=2023,
            batch_size=2,  # Small batch size for testing
            delay=0.1       # Small delay for testing
        )
        
        # Verify results
        assert len(results) == len(qb_ids)
        assert all(results.values())  # All imports should succeed
        
        # Verify mock was called for each player
        assert mock_import.call_count == len(qb_ids)
    
    @pytest.mark.asyncio
    @patch.object(DataImportService, '_import_player_data')
    async def test_batch_size_and_delay(self, mock_import, data_service, batch_service, sample_players):
        """Test that batch size and delay parameters are respected."""
        # Create a tracking mechanism to measure timing
        timestamps = []
        
        async def mock_import_with_timing(player_id, season):
            # Record timestamp
            timestamps.append(asyncio.get_event_loop().time())
            return True
        
        mock_import.side_effect = mock_import_with_timing
        
        # Get player IDs
        player_ids = [player.player_id for player in sample_players]
        
        # Process with specific batch size and delay
        batch_size = 2
        delay = 0.5  # Half second delay
        
        start_time = asyncio.get_event_loop().time()
        
        await batch_service.process_batch(
            service=data_service,
            method_name="_import_player_data",
            items=player_ids,
            season=2023,
            batch_size=batch_size,
            delay=delay
        )
        
        end_time = asyncio.get_event_loop().time()
        
        # Calculate expected timing
        # With 5 players and batch size 2, we should have 3 batches
        # Each batch except the last should have a delay
        # So total delay should be (3-1) * delay = 1.0 seconds
        expected_min_time = (len(player_ids) // batch_size) * delay
        if len(player_ids) % batch_size == 0:
            expected_min_time -= delay  # Last batch doesn't add delay
            
        actual_time = end_time - start_time
        
        # Verify timing is at least what we expect
        assert actual_time >= expected_min_time
        
        # Verify first batch ran concurrently (timestamps should be close)
        if len(timestamps) >= batch_size:
            assert timestamps[1] - timestamps[0] < 0.1  # First batch should run concurrently
        
        # Verify there was delay between batches
        if len(timestamps) >= batch_size + 1:
            assert timestamps[batch_size] - timestamps[batch_size-1] >= delay * 0.9  # Allow for slight timing variance
    
    @pytest.mark.asyncio
    @patch.object(DataImportService, '_import_player_data')
    async def test_partial_batch_failures(self, mock_import, data_service, batch_service, sample_players):
        """Test behavior when some items in the batch fail."""
        # Set up mock to succeed for some players and fail for others
        async def mock_import_with_failures(player_id, season):
            # Fail for every second player
            return player_ids.index(player_id) % 2 == 0
        
        mock_import.side_effect = mock_import_with_failures
        
        # Get player IDs
        player_ids = [player.player_id for player in sample_players]
        
        # Process batch
        results = await batch_service.process_batch(
            service=data_service,
            method_name="_import_player_data",
            items=player_ids,
            season=2023,
            batch_size=2,
            delay=0.1
        )
        
        # Verify results match expected pattern
        for i, player_id in enumerate(player_ids):
            expected_result = i % 2 == 0
            assert results[player_id] == expected_result
        
        # Verify success and failure counts
        success_count = sum(1 for result in results.values() if result)
        failure_count = sum(1 for result in results.values() if not result)
        
        assert success_count == (len(player_ids) + 1) // 2  # Ceiling division
        assert failure_count == len(player_ids) // 2  # Floor division
    
    @pytest.mark.asyncio
    @patch.object(DataImportService, '_import_player_data')
    async def test_error_handling(self, mock_import, data_service, batch_service, sample_players):
        """Test handling of errors during batch processing."""
        # Set up mock to raise exceptions for some players
        async def mock_import_with_errors(player_id, season):
            index = player_ids.index(player_id)
            if index == 1:
                raise ValueError("Test error for player 1")
            elif index == 3:
                raise RuntimeError("Test error for player 3")
            return True
        
        mock_import.side_effect = mock_import_with_errors
        
        # Get player IDs
        player_ids = [player.player_id for player in sample_players]
        
        # Process batch
        results = await batch_service.process_batch(
            service=data_service,
            method_name="_import_player_data",
            items=player_ids,
            season=2023,
            batch_size=2,
            delay=0.1
        )
        
        # Verify results
        assert results[player_ids[0]] is True
        assert results[player_ids[1]] is False  # Should fail with ValueError
        assert results[player_ids[2]] is True
        assert results[player_ids[3]] is False  # Should fail with RuntimeError
        assert results[player_ids[4]] is True
        
        # Verify errors are logged
        logs = batch_service.db.query(ImportLog).all()
        
        # There should be at least 2 error logs
        assert len(logs) >= 2
        
        # Verify error messages are captured
        error_messages = [log.message for log in logs]
        assert any("Test error for player 1" in msg for msg in error_messages)
        assert any("Test error for player 3" in msg for msg in error_messages)
    
    @pytest.mark.asyncio
    @patch.object(DataImportService, '_request_with_backoff')
    async def test_rate_limiting_behavior(self, mock_request, data_service, test_db):
        """Test the rate limiting and backoff behavior."""
        # Set up a mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test data"}
        
        # Track request timestamps
        timestamps = []
        
        # Mock the request function to simulate rate limiting
        async def mock_request_with_rate_limit(url, delay_factor=1):
            timestamps.append(asyncio.get_event_loop().time())
            
            # Simulate rate limit on every 3rd request
            if len(timestamps) % 3 == 0:
                # Create a response that indicates rate limiting
                rate_limit_response = MagicMock()
                rate_limit_response.status_code = 429
                
                # On first rate limit, return 429 once, then succeed
                if len(timestamps) == 3:
                    mock_request.side_effect = mock_request_success
                    return rate_limit_response
                
                # On second rate limit, return 429 three times, then succeed
                if len(timestamps) == 6:
                    mock_request.side_effect = mock_request_multiple_failures
                    return rate_limit_response
            
            return mock_response
        
        # Helper mock functions for different retry scenarios
        async def mock_request_success(url, delay_factor=1):
            timestamps.append(asyncio.get_event_loop().time())
            return mock_response
        
        retries_count = 0
        async def mock_request_multiple_failures(url, delay_factor=1):
            nonlocal retries_count
            timestamps.append(asyncio.get_event_loop().time())
            retries_count += 1
            
            if retries_count < 3:
                rate_limit_response = MagicMock()
                rate_limit_response.status_code = 429
                return rate_limit_response
            
            # After 3 retries, succeed
            mock_request.side_effect = mock_request_success
            return mock_response
        
        # Initial mock
        mock_request.side_effect = mock_request_with_rate_limit
        
        # Test URL
        test_url = "https://api.test.com/players/1"
        
        # First attempt (should succeed)
        response1 = await data_service._request_with_backoff(test_url)
        assert response1.status_code == 200
        
        # Second attempt (should succeed)
        response2 = await data_service._request_with_backoff(test_url)
        assert response2.status_code == 200
        
        # Third attempt (should hit rate limit once, then succeed after backoff)
        response3 = await data_service._request_with_backoff(test_url)
        assert response3.status_code == 200
        
        # Should be at least 4 timestamps (3 initial requests + 1 retry after backoff)
        assert len(timestamps) >= 4
        
        # Verify backoff timing
        # First retry should wait at least delay_factor * 2 seconds
        if len(timestamps) >= 4:
            backoff_time = timestamps[3] - timestamps[2]
            assert backoff_time >= 2.0  # Default delay_factor is 1, so wait should be at least 2s
        
        # Additional requests
        response4 = await data_service._request_with_backoff(test_url)
        assert response4.status_code == 200
        
        response5 = await data_service._request_with_backoff(test_url)
        assert response5.status_code == 200
        
        # Sixth attempt (should hit rate limit multiple times)
        response6 = await data_service._request_with_backoff(test_url)
        assert response6.status_code == 200
        
        # Verify exponential backoff
        # With 3 retries, we should have delays of ~2s, ~4s, ~8s
        final_timestamps = timestamps[-4:]  # Last 4 timestamps
        if len(final_timestamps) >= 4:
            backoff1 = final_timestamps[1] - final_timestamps[0]
            backoff2 = final_timestamps[2] - final_timestamps[1]
            backoff3 = final_timestamps[3] - final_timestamps[2]
            
            # Verify exponential pattern (allowing for some timing variance)
            assert backoff2 > backoff1 * 1.5
            assert backoff3 > backoff2 * 1.5
    
    @pytest.mark.asyncio
    @patch.object(DataImportService, '_import_player_data')
    async def test_circuit_breaker_pattern(self, mock_import, data_service, batch_service, sample_players):
        """Test the circuit breaker pattern for preventing excessive failures."""
        # Set up mock to consistently fail
        failure_count = 0
        
        async def mock_import_with_consistent_failure(player_id, season):
            nonlocal failure_count
            failure_count += 1
            raise ValueError(f"Consistent failure {failure_count}")
        
        mock_import.side_effect = mock_import_with_consistent_failure
        
        # Get player IDs
        player_ids = [player.player_id for player in sample_players]
        
        # Configure batch service with low failure threshold
        batch_service.failure_threshold = 3  # Circuit breaks after 3 failures
        
        # Process batch
        results = await batch_service.process_batch(
            service=data_service,
            method_name="_import_player_data",
            items=player_ids,
            season=2023,
            batch_size=2,
            delay=0.1
        )
        
        # Verify circuit breaker activated
        # Should stop processing after hitting failure threshold
        assert 1 <= failure_count <= 3  # At least 1, but should stop after threshold (3)
        
        # All results should be False
        assert all(not result for result in results.values())
        
        # Verify error logs
        logs = batch_service.db.query(ImportLog).all()
        
        # Should have logs for failures up to threshold, plus circuit breaker notification
        assert len(logs) >= failure_count
        
        # Check for circuit breaker message
        circuit_breaker_logs = [log for log in logs if "circuit breaker" in log.message.lower()]
        assert len(circuit_breaker_logs) > 0