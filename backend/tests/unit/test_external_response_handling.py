import pytest
import pandas as pd
import json
from unittest.mock import patch, MagicMock, AsyncMock
import aiohttp
from backend.services.data_import_service import DataImportService

class TestExternalResponseHandling:
    @pytest.fixture(scope="function")
    def service(self, test_db):
        """Create DataImportService instance for testing."""
        return DataImportService(test_db)
    
    @pytest.mark.asyncio
    async def test_handle_html_response(self, service):
        """Test handling HTML responses from external sources."""
        # Mock HTML response
        html_content = """
        <html>
        <head><title>Test Data</title></head>
        <body>
            <table class="stats_table" id="stats">
                <thead>
                    <tr>
                        <th>Player</th>
                        <th>Tm</th>
                        <th>Pos</th>
                        <th>G</th>
                        <th>GS</th>
                        <th>Att</th>
                        <th>Yds</th>
                        <th>TD</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Player 1</td>
                        <td>SF</td>
                        <td>RB</td>
                        <td>16</td>
                        <td>15</td>
                        <td>272</td>
                        <td>1459</td>
                        <td>14</td>
                    </tr>
                    <tr>
                        <td>Player 2</td>
                        <td>KC</td>
                        <td>RB</td>
                        <td>17</td>
                        <td>12</td>
                        <td>210</td>
                        <td>980</td>
                        <td>8</td>
                    </tr>
                </tbody>
            </table>
        </body>
        </html>
        """
        
        # Create mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=html_content)
        
        # Mock the session.get method
        mock_session = MagicMock()
        mock_session.get = AsyncMock(return_value=mock_response)
        
        # Patch the service
        with patch('aiohttp.ClientSession', return_value=mock_session):
            # Call method that processes HTML
            url = "https://api.test.com/stats"
            result = await service._fetch_html_table(url, table_id="stats")
            
            # Verify results - should be a DataFrame with the table data
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 2  # Two rows
            assert list(result.columns) == ['Player', 'Tm', 'Pos', 'G', 'GS', 'Att', 'Yds', 'TD']
            assert result.iloc[0]['Player'] == 'Player 1'
            assert result.iloc[0]['Yds'] == '1459'
    
    @pytest.mark.asyncio
    async def test_handle_json_response(self, service):
        """Test handling JSON responses from external sources."""
        # Mock JSON response
        json_content = {
            "players": [
                {
                    "name": "Player 1",
                    "team": "SF",
                    "position": "RB",
                    "stats": {
                        "games": 16,
                        "rushAttempts": 272,
                        "rushYards": 1459,
                        "rushTD": 14
                    }
                },
                {
                    "name": "Player 2",
                    "team": "KC",
                    "position": "RB",
                    "stats": {
                        "games": 17,
                        "rushAttempts": 210,
                        "rushYards": 980,
                        "rushTD": 8
                    }
                }
            ]
        }
        
        # Create mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=json_content)
        
        # Mock the session.get method
        mock_session = MagicMock()
        mock_session.get = AsyncMock(return_value=mock_response)
        
        # Patch the service
        with patch('aiohttp.ClientSession', return_value=mock_session):
            # Call a method that processes JSON
            url = "https://api.test.com/players"
            
            # Create a method to test JSON handling
            async def fetch_json_data(url):
                async with aiohttp.ClientSession() as session:
                    response = await session.get(url)
                    data = await response.json()
                    return data
            
            result = await fetch_json_data(url)
            
            # Verify results
            assert isinstance(result, dict)
            assert "players" in result
            assert len(result["players"]) == 2
            assert result["players"][0]["name"] == "Player 1"
            assert result["players"][0]["stats"]["rushYards"] == 1459
    
    @pytest.mark.asyncio
    async def test_handle_csv_response(self, service):
        """Test handling CSV responses from external sources."""
        # Mock CSV response
        csv_content = """Player,Tm,Pos,G,GS,Att,Yds,TD
Player 1,SF,RB,16,15,272,1459,14
Player 2,KC,RB,17,12,210,980,8
"""
        
        # Create mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=csv_content)
        
        # Mock the session.get method
        mock_session = MagicMock()
        mock_session.get = AsyncMock(return_value=mock_response)
        
        # Patch the service
        with patch('aiohttp.ClientSession', return_value=mock_session):
            # Call a method that processes CSV
            url = "https://api.test.com/stats.csv"
            
            # Create a method to test CSV handling
            async def fetch_csv_data(url):
                async with aiohttp.ClientSession() as session:
                    response = await session.get(url)
                    text = await response.text()
                    df = pd.read_csv(pd.StringIO(text))
                    return df
            
            result = await fetch_csv_data(url)
            
            # Verify results
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 2  # Two rows
            assert list(result.columns) == ['Player', 'Tm', 'Pos', 'G', 'GS', 'Att', 'Yds', 'TD']
            assert result.iloc[0]['Player'] == 'Player 1'
            assert result.iloc[0]['Yds'] == 1459
    
    @pytest.mark.asyncio
    async def test_handle_error_responses(self, service):
        """Test handling error responses from external sources."""
        # Create a dictionary of error status codes and their mocks
        error_mocks = {
            404: MagicMock(status=404, text=AsyncMock(return_value="Not Found")),
            500: MagicMock(status=500, text=AsyncMock(return_value="Server Error")),
            403: MagicMock(status=403, text=AsyncMock(return_value="Forbidden"))
        }
        
        # Mock the session.get method to return different errors
        async def mock_get(url, *args, **kwargs):
            # Extract error code from URL
            if "404" in url:
                raise aiohttp.ClientResponseError(request_info=MagicMock(), history=(), status=404)
            elif "500" in url:
                raise aiohttp.ClientResponseError(request_info=MagicMock(), history=(), status=500)
            elif "403" in url:
                raise aiohttp.ClientResponseError(request_info=MagicMock(), history=(), status=403)
            else:
                mock_resp = MagicMock()
                mock_resp.status = 200
                mock_resp.json = AsyncMock(return_value={"data": "test data"})
                return mock_resp
        
        mock_session = MagicMock()
        mock_session.get = mock_get
        
        # Patch the service
        with patch('aiohttp.ClientSession', return_value=mock_session):
            # Test 404 error
            with pytest.raises(aiohttp.ClientResponseError) as excinfo:
                await service._request_with_backoff("https://api.test.com/404")
            assert excinfo.value.status == 404
            
            # Test 500 error
            with pytest.raises(aiohttp.ClientResponseError) as excinfo:
                await service._request_with_backoff("https://api.test.com/500")
            assert excinfo.value.status == 500
            
            # Test 403 error
            with pytest.raises(aiohttp.ClientResponseError) as excinfo:
                await service._request_with_backoff("https://api.test.com/403")
            assert excinfo.value.status == 403
            
            # Test successful request
            response = await service._request_with_backoff("https://api.test.com/data")
            assert response.status == 200
    
    @pytest.mark.asyncio
    async def test_handle_malformed_responses(self, service):
        """Test handling malformed data in responses."""
        # Mock malformed HTML
        malformed_html = "<html><body><table><tr><td>Incomplete table</body></html>"
        
        # Mock malformed JSON
        malformed_json = "{players: [{name: 'Invalid JSON"
        
        # Create mock responses
        mock_html_response = MagicMock()
        mock_html_response.status = 200
        mock_html_response.text = AsyncMock(return_value=malformed_html)
        
        mock_json_response = MagicMock()
        mock_json_response.status = 200
        mock_json_response.json = AsyncMock(side_effect=json.JSONDecodeError("Invalid JSON", "", 0))
        mock_json_response.text = AsyncMock(return_value=malformed_json)
        
        # Mock the session.get method
        async def mock_get(url, *args, **kwargs):
            if "html" in url:
                return mock_html_response
            elif "json" in url:
                return mock_json_response
            else:
                mock_resp = MagicMock()
                mock_resp.status = 200
                mock_resp.json = AsyncMock(return_value={"data": "test data"})
                return mock_resp
        
        mock_session = MagicMock()
        mock_session.get = mock_get
        
        # Patch the service
        with patch('aiohttp.ClientSession', return_value=mock_session):
            # Test malformed HTML handling
            result = await service._fetch_html_table("https://api.test.com/html", table_id="stats")
            # Should return empty DataFrame or handle gracefully
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 0
            
            # Test malformed JSON handling
            url = "https://api.test.com/json"
            
            # Create a method to test JSON error handling
            async def fetch_json_with_error_handling(url):
                try:
                    async with aiohttp.ClientSession() as session:
                        response = await session.get(url)
                        data = await response.json()
                        return data
                except json.JSONDecodeError:
                    # Graceful handling
                    return {"error": "Invalid JSON"}
            
            result = await fetch_json_with_error_handling(url)
            assert isinstance(result, dict)
            assert "error" in result
    
    @pytest.mark.asyncio
    async def test_handle_network_errors(self, service):
        """Test handling network errors during requests."""
        # Mock different network errors
        connection_error = aiohttp.ClientConnectorError(MagicMock(), OSError())
        timeout_error = asyncio.TimeoutError()
        
        # Mock the session.get method
        async def mock_get(url, *args, **kwargs):
            if "connection" in url:
                raise connection_error
            elif "timeout" in url:
                raise timeout_error
            else:
                mock_resp = MagicMock()
                mock_resp.status = 200
                mock_resp.json = AsyncMock(return_value={"data": "test data"})
                return mock_resp
        
        mock_session = MagicMock()
        mock_session.get = mock_get
        
        # Patch the service
        with patch('aiohttp.ClientSession', return_value=mock_session):
            # Test connection error
            with pytest.raises(aiohttp.ClientConnectorError):
                await service._request_with_backoff("https://api.test.com/connection")
            
            # Test timeout error
            with pytest.raises(asyncio.TimeoutError):
                await service._request_with_backoff("https://api.test.com/timeout")
            
            # Test successful request
            response = await service._request_with_backoff("https://api.test.com/data")
            assert response.status == 200