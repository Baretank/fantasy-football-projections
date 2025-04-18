"""
Web Data Adapter for testing purposes.

This adapter provides methods for handling web requests with
backoff and rate limiting, used for testing the NFL data import system.
"""

import logging
import asyncio
import random
import time
from typing import Dict, Any, List, cast

import aiohttp
import pandas as pd
from bs4 import BeautifulSoup

from backend.services.typing_pandas import TypedDataFrame

logger = logging.getLogger(__name__)


class WebDataAdapter:
    """
    Adapter for handling web requests with proper backoff and rate limiting.
    This adapter is primarily used for testing and provides functionality
    previously in the DataImportService.
    """

    def __init__(self):
        """Initialize the web data adapter."""
        self.max_retries = 5
        self.base_delay = 2.0
        self.max_delay = 60.0
        self.throttle_delay = 0.5  # Time between requests
        self.jitter_factor = 0.25
        self.last_request_time = 0
        self.circuit_breaker_failures = 0
        self.circuit_breaker_threshold = 5
        self.circuit_reset_time = 0
        self.circuit_cooldown = 60  # seconds

    async def _request_with_backoff(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """
        Make an HTTP request with exponential backoff for rate limiting.

        Args:
            url: The URL to request
            **kwargs: Additional arguments to pass to the request

        Returns:
            aiohttp.ClientResponse: The response object

        Raises:
            aiohttp.ClientResponseError: If the request fails after max retries
        """
        # Check if circuit breaker is open
        if self._is_circuit_open():
            raise Exception(f"Circuit breaker open - too many failures for {url}")

        retry_count = 0
        delay_factor = 1

        # Throttle requests to prevent rate limiting
        now = time.time()
        time_since_last = now - self.last_request_time
        if time_since_last < self.throttle_delay:
            await asyncio.sleep(self.throttle_delay - time_since_last)

        while True:
            try:
                # Update last request time
                self.last_request_time = time.time()

                # Create session to make the request
                async with aiohttp.ClientSession() as session:
                    # Make the request
                    response = await session.get(url, **kwargs)

                    # Check for rate limiting
                    if response.status == 429:
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info, history=response.history, status=429
                        )

                    # Check for other errors
                    if response.status >= 400:
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                        )

                    # Reset circuit breaker on success
                    self.circuit_breaker_failures = 0

                    # Return the response
                    return response

            except aiohttp.ClientResponseError as e:
                # Handle rate limiting specifically
                if e.status == 429:
                    # Record rate limit hit
                    logger.warning(
                        f"Rate limited on {url} (retry {retry_count+1}/{self.max_retries})"
                    )

                    # Check if we've hit max retries
                    if retry_count >= self.max_retries:
                        # Increment circuit breaker counter
                        self.circuit_breaker_failures += 1
                        raise

                    # Calculate delay with jitter
                    delay = self.base_delay * delay_factor
                    delay = min(delay, self.max_delay)
                    jitter = random.uniform(-self.jitter_factor, self.jitter_factor) * delay
                    delay = delay + jitter

                    # Wait before retrying
                    await asyncio.sleep(delay)

                    # Increase delay factor for next retry
                    retry_count += 1
                    delay_factor *= 2
                    continue

                else:
                    # For other errors, increment circuit breaker and raise
                    self.circuit_breaker_failures += 1
                    raise

            except Exception:
                # For other exceptions, increment circuit breaker and raise
                self.circuit_breaker_failures += 1
                raise

    def _is_circuit_open(self) -> bool:
        """
        Check if the circuit breaker is open (too many failures).

        Returns:
            bool: True if the circuit is open (should not make requests)
        """
        # If we're above the failure threshold
        if self.circuit_breaker_failures >= self.circuit_breaker_threshold:
            now = time.time()

            # If this is the first time hitting the threshold, set the reset time
            if self.circuit_reset_time == 0:
                self.circuit_reset_time = now + self.circuit_cooldown
                return True

            # If we're still in the cooldown period
            if now < self.circuit_reset_time:
                return True

            # Cooldown period is over, reset the circuit breaker
            self.circuit_breaker_failures = 0
            self.circuit_reset_time = 0

        return False

    async def _fetch_html_table(self, url: str, table_id: str = None) -> TypedDataFrame:
        """
        Fetch HTML from a URL and extract a table.

        Args:
            url: The URL to fetch
            table_id: The ID of the table to extract (optional)

        Returns:
            TypedDataFrame: The extracted table as a typed DataFrame
        """
        try:
            # Make the request - simplified for test compatibility
            response = await self._request_with_backoff(url)
            html = await response.text()

            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            # Find the target table
            if table_id:
                table = soup.find("table", id=table_id)
            else:
                table = soup.find("table")

            if not table:
                logger.warning(f"No table found at {url}")
                return TypedDataFrame(pd.DataFrame())

            # Extract table headers
            headers: List[str] = []
            header_row = table.find("thead").find("tr") if table.find("thead") else table.find("tr")
            if header_row:
                for th in header_row.find_all("th"):
                    headers.append(th.text.strip())

            # Extract table rows
            rows: List[List[str]] = []
            body = table.find("tbody") or table
            for tr in body.find_all("tr"):
                # Skip header row if we're looking at the whole table
                if tr == header_row:
                    continue

                row: List[str] = []
                for td in tr.find_all("td"):
                    row.append(td.text.strip())
                if row and len(row) == len(headers):  # Skip empty rows or mismatched rows
                    rows.append(row)

            # Create DataFrame
            if not rows or not headers:
                return TypedDataFrame(pd.DataFrame())

            df = pd.DataFrame(rows, columns=headers)
            return TypedDataFrame(df)

        except Exception as e:
            logger.error(f"Error fetching HTML table from {url}: {str(e)}")
            return TypedDataFrame(pd.DataFrame())

    async def fetch_json_data(self, url: str) -> Dict[str, Any]:
        """
        Fetch JSON data from a URL.

        Args:
            url: The URL to fetch

        Returns:
            Dict[str, Any]: The JSON response as a dictionary

        Raises:
            aiohttp.ClientResponseError: If the request fails
            json.JSONDecodeError: If the response is not valid JSON
        """
        try:
            # Make the request
            response = await self._request_with_backoff(url)
            # Parse JSON response
            data = await response.json()
            return cast(Dict[str, Any], data)
        except Exception as e:
            logger.error(f"Error fetching JSON from {url}: {str(e)}")
            raise

    async def fetch_csv_data(self, url: str) -> TypedDataFrame:
        """
        Fetch CSV data from a URL and convert to TypedDataFrame.

        Args:
            url: The URL to fetch

        Returns:
            TypedDataFrame: The CSV data as a typed DataFrame

        Raises:
            aiohttp.ClientResponseError: If the request fails
        """
        try:
            # Make the request
            response = await self._request_with_backoff(url)
            # Get text content
            text = await response.text()
            # Parse CSV into DataFrame
            from io import StringIO

            df = pd.read_csv(StringIO(text))
            return TypedDataFrame(df)
        except Exception as e:
            logger.error(f"Error fetching CSV from {url}: {str(e)}")
            raise
