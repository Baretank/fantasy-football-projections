import pytest
import pandas as pd
import json
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import aiohttp
from backend.services.adapters.web_data_adapter import WebDataAdapter


class TestExternalResponseHandling:
    @pytest.fixture(scope="function")
    def adapter(self):
        """Create WebDataAdapter instance for testing."""
        return WebDataAdapter()

    @pytest.mark.asyncio
    async def test_handle_html_response(self, adapter):
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

        # Mock the session object
        mock_session = MagicMock()
        mock_session.get = AsyncMock(return_value=mock_response)

        # Set up context manager mock
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        # Patch the service
        with patch("aiohttp.ClientSession", return_value=mock_cm):
            # Call method that processes HTML
            url = "https://api.test.com/stats"
            result = await adapter._fetch_html_table(url, table_id="stats")

            # Verify results - should be a DataFrame with the table data
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 2  # Two rows
            assert list(result.columns) == ["Player", "Tm", "Pos", "G", "GS", "Att", "Yds", "TD"]
            assert result.iloc[0]["Player"] == "Player 1"
            assert result.iloc[0]["Yds"] == "1459"

    @pytest.mark.asyncio
    async def test_handle_json_response(self, adapter):
        """Test handling JSON responses from external sources."""
        # Mock JSON response
        json_content = {
            "players": [
                {
                    "name": "Player 1",
                    "team": "SF",
                    "position": "RB",
                    "stats": {"games": 16, "rushAttempts": 272, "rushYards": 1459, "rushTD": 14},
                },
                {
                    "name": "Player 2",
                    "team": "KC",
                    "position": "RB",
                    "stats": {"games": 17, "rushAttempts": 210, "rushYards": 980, "rushTD": 8},
                },
            ]
        }

        # Create mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=json_content)

        # Mock the session object
        mock_session = MagicMock()
        mock_session.get = AsyncMock(return_value=mock_response)

        # Set up context manager mock
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        # Patch the service
        with patch("aiohttp.ClientSession", return_value=mock_cm):
            # Call the method that processes JSON
            url = "https://api.test.com/players"
            result = await adapter.fetch_json_data(url)

            # Verify results
            assert isinstance(result, dict)
            assert "players" in result
            assert len(result["players"]) == 2
            assert result["players"][0]["name"] == "Player 1"
            assert result["players"][0]["stats"]["rushYards"] == 1459

    @pytest.mark.asyncio
    async def test_handle_csv_response(self, adapter):
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

        # Mock the session object
        mock_session = MagicMock()
        mock_session.get = AsyncMock(return_value=mock_response)

        # Set up context manager mock
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        # Patch the service
        with patch("aiohttp.ClientSession", return_value=mock_cm):
            # Call the method that processes CSV
            url = "https://api.test.com/stats.csv"
            result = await adapter.fetch_csv_data(url)

            # Verify results
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 2  # Two rows
            assert list(result.columns) == ["Player", "Tm", "Pos", "G", "GS", "Att", "Yds", "TD"]
            assert result.iloc[0]["Player"] == "Player 1"
            assert result.iloc[0]["Yds"] == 1459

    @pytest.mark.asyncio
    async def test_handle_error_responses(self, adapter):
        """Test handling error responses from external sources."""
        # Mock responses for different error codes
        mock_session = MagicMock()

        # Create mock get method that raises exceptions based on URL
        async def mock_get(url, *args, **kwargs):
            if "404" in url:
                mock_resp = MagicMock()
                mock_resp.status = 404
                return mock_resp
            elif "500" in url:
                mock_resp = MagicMock()
                mock_resp.status = 500
                return mock_resp
            elif "403" in url:
                mock_resp = MagicMock()
                mock_resp.status = 403
                return mock_resp
            else:
                mock_resp = MagicMock()
                mock_resp.status = 200
                mock_resp.json = AsyncMock(return_value={"data": "test data"})
                return mock_resp

        mock_session.get = mock_get

        # Set up context manager mock for ClientSession
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        # Patch ClientSession to return our mock context manager
        with patch("aiohttp.ClientSession", return_value=mock_cm):
            # Test 404 error
            with pytest.raises(aiohttp.ClientResponseError):
                await adapter._request_with_backoff("https://api.test.com/404")

            # Test 500 error
            with pytest.raises(aiohttp.ClientResponseError):
                await adapter._request_with_backoff("https://api.test.com/500")

            # Test 403 error
            with pytest.raises(aiohttp.ClientResponseError):
                await adapter._request_with_backoff("https://api.test.com/403")

            # Test successful request
            response = await adapter._request_with_backoff("https://api.test.com/data")
            assert response.status == 200

    @pytest.mark.asyncio
    async def test_handle_malformed_responses(self, adapter):
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

        # Mock the session.get method for different urls
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

        # Create the session mock
        mock_session = MagicMock()
        mock_session.get = mock_get

        # Set up context manager mock
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        # Patch the service
        with patch("aiohttp.ClientSession", return_value=mock_cm):
            # Test malformed HTML handling
            result = await adapter._fetch_html_table("https://api.test.com/html", table_id="stats")
            # Should return empty DataFrame or handle gracefully
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 0

            # Test malformed JSON handling
            url = "https://api.test.com/json"

            # Test JSON error handling
            with pytest.raises(json.JSONDecodeError):
                await adapter.fetch_json_data(url)

    @pytest.mark.asyncio
    async def test_handle_network_errors(self, adapter):
        """Test handling network errors during requests."""
        # Mock different network errors
        connection_error = aiohttp.ClientConnectorError(MagicMock(), OSError())
        timeout_error = asyncio.TimeoutError()

        # Mock session for different error scenarios
        mock_session = MagicMock()

        # Create mock get method that raises exceptions based on URL
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

        mock_session.get = mock_get

        # Set up context manager mock for ClientSession
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        # Patch ClientSession to return our mock context manager
        with patch("aiohttp.ClientSession", return_value=mock_cm):
            # Test connection error
            with pytest.raises(aiohttp.ClientConnectorError):
                await adapter._request_with_backoff("https://api.test.com/connection")

            # Test timeout error
            with pytest.raises(asyncio.TimeoutError):
                await adapter._request_with_backoff("https://api.test.com/timeout")

            # Test successful request
            response = await adapter._request_with_backoff("https://api.test.com/data")
            assert response.status == 200
