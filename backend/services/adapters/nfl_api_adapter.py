from typing import Dict, List, Any, Optional
import aiohttp
import asyncio
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class NFLApiAdapter:
    """
    Adapter for the NFL API to retrieve NFL statistics.
    
    This adapter provides methods to fetch player data, weekly stats,
    and other information from the official NFL API with proper rate limiting
    and error handling.
    """
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        """
        Initialize the NFL API adapter.
        
        Args:
            max_retries: Maximum number of retries for failed requests
            retry_delay: Initial delay between retries (will use exponential backoff)
        """
        self.base_url = "https://api.nfl.com/v3"
        self.headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json'
        }
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.session = None
        
    async def initialize(self):
        """
        Initialize the aiohttp session.
        """
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
            
    async def close(self):
        """
        Close the aiohttp session.
        """
        if self.session and not self.session.closed:
            await self.session.close()
            
    async def get_players(self, season: int) -> Dict[str, Any]:
        """
        Get player data from NFL API.
        
        Args:
            season: The NFL season year (e.g., 2023)
            
        Returns:
            Dictionary containing player information
        """
        await self.initialize()
        endpoint = "players"
        params = {"season": str(season)}
        logger.info(f"Fetching player data for season {season} from NFL API")
        return await self._make_api_request(endpoint, params)
    
    async def get_player_stats(self, season: int, week: Optional[int] = None) -> Dict[str, Any]:
        """
        Get player statistics from NFL API.
        
        Args:
            season: The NFL season year (e.g., 2023)
            week: Optional week number (None for season stats)
            
        Returns:
            Dictionary containing player statistics
        """
        await self.initialize()
        endpoint = "players/stats"
        params = {"season": str(season)}
        if week is not None:
            params["week"] = str(week)
        logger.info(f"Fetching player stats for season {season}, week {week or 'all'} from NFL API")
        return await self._make_api_request(endpoint, params)
    
    async def get_teams(self, season: int) -> Dict[str, Any]:
        """
        Get team information from NFL API.
        
        Args:
            season: The NFL season year (e.g., 2023)
            
        Returns:
            Dictionary containing team information
        """
        await self.initialize()
        endpoint = "teams"
        params = {"season": str(season)}
        logger.info(f"Fetching team data for season {season} from NFL API")
        return await self._make_api_request(endpoint, params)
    
    async def get_games(self, season: int, week: Optional[int] = None) -> Dict[str, Any]:
        """
        Get game information from NFL API.
        
        Args:
            season: The NFL season year (e.g., 2023)
            week: Optional week number (None for all games)
            
        Returns:
            Dictionary containing game information
        """
        await self.initialize()
        endpoint = "games"
        params = {"season": str(season)}
        if week is not None:
            params["week"] = str(week)
        logger.info(f"Fetching game data for season {season}, week {week or 'all'} from NFL API")
        return await self._make_api_request(endpoint, params)
    
    async def get_draft_data(self, season: int) -> Dict[str, Any]:
        """
        Get draft information from NFL API.
        
        Args:
            season: The NFL season year (e.g., 2023)
            
        Returns:
            Dictionary containing draft information
        """
        await self.initialize()
        endpoint = "draft"
        params = {"season": str(season)}
        logger.info(f"Fetching draft data for season {season} from NFL API")
        return await self._make_api_request(endpoint, params)
            
    async def _make_api_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Make request to NFL API with retry logic and rate limiting.
        
        Args:
            endpoint: API endpoint to call
            params: Query parameters
            
        Returns:
            API response as dictionary
            
        Raises:
            Exception: If the request fails after all retries
        """
        url = f"{self.base_url}/{endpoint}"
        retry_count = 0
        
        while retry_count < self.max_retries:
            try:
                async with self.session.get(url, headers=self.headers, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:  # Rate limit
                        retry_count += 1
                        wait_time = self.retry_delay * (2 ** retry_count)
                        logger.warning(f"Rate limited, retrying in {wait_time}s (attempt {retry_count}/{self.max_retries})")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"API error: {response.status}, {await response.text()}")
                        raise Exception(f"API error: {response.status}")
            except Exception as e:
                retry_count += 1
                if retry_count >= self.max_retries:
                    logger.error(f"Failed after {self.max_retries} attempts: {str(e)}")
                    raise
                wait_time = self.retry_delay * (2 ** retry_count)
                logger.warning(f"Request error, retrying in {wait_time}s (attempt {retry_count}/{self.max_retries}): {str(e)}")
                await asyncio.sleep(wait_time)
        
        raise Exception(f"Maximum retries ({self.max_retries}) exceeded")