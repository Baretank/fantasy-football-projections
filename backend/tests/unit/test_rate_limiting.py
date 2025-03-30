import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock, AsyncMock
import aiohttp
from backend.services.data_import_service import DataImportService

class TestRateLimiting:
    @pytest.fixture(scope="function")
    def service(self, test_db):
        """Create DataImportService instance for testing."""
        return DataImportService(test_db)
    
    @pytest.mark.asyncio
    async def test_backoff_on_rate_limit(self, service):
        """Test that the service backs off when rate limited."""
        # Mock response for rate limiting (429)
        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 429
        
        # Mock successful response
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {"data": "test data"}
        
        # Track calls and time between retries
        call_times = []
        
        # Create a mock aiohttp ClientSession.get that returns rate limit then success
        async def mock_get(*args, **kwargs):
            call_times.append(time.time())
            
            # First call gets rate limited
            if len(call_times) == 1:
                raise aiohttp.ClientResponseError(
                    request_info=MagicMock(),
                    history=(),
                    status=429
                )
            # Second call succeeds
            else:
                mock_resp = MagicMock()
                mock_resp.status = 200
                mock_resp.json = AsyncMock(return_value={"data": "test data"})
                return mock_resp
        
        # Create a mock session
        mock_session = MagicMock()
        mock_session.get = mock_get
        
        # Patch the service to use our mock session
        with patch('aiohttp.ClientSession', return_value=mock_session):
            # Call the service with backoff
            response = await service._request_with_backoff("https://api.test.com/data")
            
            # Verify response
            assert response.status == 200
            response_data = await response.json()
            assert response_data == {"data": "test data"}
            
            # Verify we had at least one retry
            assert len(call_times) == 2
            
            # Verify backoff delay
            delay = call_times[1] - call_times[0]
            assert delay >= 2.0, f"Backoff delay too short: {delay}"
    
    @pytest.mark.asyncio
    async def test_exponential_backoff(self, service):
        """Test that backoff delay increases exponentially with retries."""
        # Track calls and time between retries
        call_times = []
        call_count = 0
        
        # Create a mock aiohttp ClientSession.get that fails multiple times
        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_times.append(time.time())
            call_count += 1
            
            # First three calls get rate limited
            if call_count <= 3:
                raise aiohttp.ClientResponseError(
                    request_info=MagicMock(),
                    history=(),
                    status=429
                )
            # Fourth call succeeds
            else:
                mock_resp = MagicMock()
                mock_resp.status = 200
                mock_resp.json = AsyncMock(return_value={"data": "test data"})
                return mock_resp
        
        # Create a mock session
        mock_session = MagicMock()
        mock_session.get = mock_get
        
        # Patch the service to use our mock session
        with patch('aiohttp.ClientSession', return_value=mock_session):
            # Call the service with backoff
            response = await service._request_with_backoff("https://api.test.com/data")
            
            # Verify response
            assert response.status == 200
            
            # Verify we had multiple retries
            assert len(call_times) == 4
            
            # Calculate delays between retries
            delays = [call_times[i+1] - call_times[i] for i in range(len(call_times)-1)]
            
            # First delay should be around 2 seconds (delay_factor=1 * 2)
            assert 1.8 <= delays[0] <= 2.5
            
            # Second delay should be around 4 seconds (delay_factor=2 * 2)
            assert 3.5 <= delays[1] <= 4.5
            
            # Third delay should be around 8 seconds (delay_factor=4 * 2)
            assert 7.0 <= delays[2] <= 9.0
            
            # Each delay should be approximately double the previous
            assert delays[1] >= delays[0] * 1.8
            assert delays[2] >= delays[1] * 1.8
    
    @pytest.mark.asyncio
    async def test_max_retries(self, service):
        """Test that the service gives up after maximum retries."""
        # Create a mock aiohttp ClientSession.get that always fails with rate limit
        async def mock_get(*args, **kwargs):
            raise aiohttp.ClientResponseError(
                request_info=MagicMock(),
                history=(),
                status=429
            )
        
        # Create a mock session
        mock_session = MagicMock()
        mock_session.get = mock_get
        
        # Patch the service to use our mock session and set max_retries to 3
        with patch('aiohttp.ClientSession', return_value=mock_session), \
             patch.object(service, 'max_retries', 3):
            
            # Call the service with backoff - should fail after 3 retries
            with pytest.raises(aiohttp.ClientResponseError) as excinfo:
                await service._request_with_backoff("https://api.test.com/data")
            
            # Verify it was a rate limit error
            assert excinfo.value.status == 429
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_circuit_breaker_pattern(self, mock_session, service):
        """Test that the circuit breaker prevents excessive requests during rate limiting."""
        # Create counter to track calls
        call_count = 0
        
        # Mock the circuit breaker method
        original_is_circuit_open = service._is_circuit_open
        
        # Create a counter of circuit checks
        circuit_check_count = 0
        
        def mock_is_circuit_open(*args, **kwargs):
            nonlocal circuit_check_count
            circuit_check_count += 1
            # After 5 checks, start reporting circuit open
            return circuit_check_count > 5
            
        service._is_circuit_open = mock_is_circuit_open
        
        # Create a mock session get that always rate limits
        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise aiohttp.ClientResponseError(
                request_info=MagicMock(),
                history=(),
                status=429
            )
        
        mock_session_instance = MagicMock()
        mock_session_instance.get = mock_get
        mock_session.return_value = mock_session_instance
        
        # Create a list of URLs to request
        urls = [f"https://api.test.com/data/{i}" for i in range(20)]
        
        # Execute multiple requests
        results = []
        for url in urls:
            try:
                result = await service._request_with_backoff(url)
                results.append(result)
            except Exception as e:
                results.append(e)
                
        # Restore original circuit breaker method
        service._is_circuit_open = original_is_circuit_open
        
        # Verify circuit breaker prevented excessive requests
        # We should have fewer actual requests than URLs due to circuit breaking
        assert call_count < len(urls)
        
        # All results should be exceptions
        assert all(isinstance(r, Exception) for r in results)
        
        # Some exceptions should be circuit breaker exceptions
        circuit_breaker_exceptions = [r for r in results if isinstance(r, Exception) and "circuit breaker" in str(r).lower()]
        assert len(circuit_breaker_exceptions) > 0
    
    @pytest.mark.asyncio
    async def test_concurrent_request_management(self, service):
        """Test that requests are properly managed for concurrency."""
        # Track concurrent requests
        concurrent_count = 0
        max_concurrent = 0
        request_lock = asyncio.Lock()
        
        # Mock response
        async def mock_get(*args, **kwargs):
            nonlocal concurrent_count, max_concurrent
            
            # Increment concurrent count
            async with request_lock:
                concurrent_count += 1
                max_concurrent = max(max_concurrent, concurrent_count)
            
            # Simulate work
            await asyncio.sleep(0.1)
            
            # Decrement concurrent count
            async with request_lock:
                concurrent_count -= 1
            
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value={"data": "test data"})
            return mock_resp
        
        # Create a mock session
        mock_session = MagicMock()
        mock_session.get = mock_get
        
        # Patch the service to use our mock session
        with patch('aiohttp.ClientSession', return_value=mock_session):
            # Make multiple concurrent requests
            tasks = []
            for i in range(10):
                task = asyncio.create_task(
                    service._request_with_backoff(f"https://api.test.com/data/{i}")
                )
                tasks.append(task)
            
            # Wait for all tasks to complete
            await asyncio.gather(*tasks)
            
            # Verify concurrency was managed
            # This check assumes the service has a concurrency limit
            # If your service doesn't limit concurrency, this test needs modification
            assert max_concurrent > 1, "Requests should run concurrently"
            
            # If the service has a specific concurrency limit, check that
            if hasattr(service, 'max_concurrent_requests'):
                assert max_concurrent <= service.max_concurrent_requests, \
                    f"Concurrent requests {max_concurrent} exceeded limit {service.max_concurrent_requests}"
    
    @pytest.mark.asyncio
    async def test_request_throttling(self, service):
        """Test that requests are properly throttled to respect rate limits."""
        # Track request timestamps
        timestamps = []
        
        # Mock successful response
        async def mock_get(*args, **kwargs):
            timestamps.append(time.time())
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value={"data": "test data"})
            return mock_resp
        
        # Create a mock session
        mock_session = MagicMock()
        mock_session.get = mock_get
        
        # Patch the service to use our mock session
        # Set a throttle delay for testing
        with patch('aiohttp.ClientSession', return_value=mock_session), \
             patch.object(service, 'throttle_delay', 0.1):  # 100ms throttle
            
            # Make sequential requests
            for i in range(5):
                await service._request_with_backoff(f"https://api.test.com/data/{i}")
            
            # Verify throttling - should have delays between requests
            delays = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
            avg_delay = sum(delays) / len(delays)
            
            # Average delay should be at least the throttle delay
            assert avg_delay >= 0.1, f"Average delay {avg_delay} too short"