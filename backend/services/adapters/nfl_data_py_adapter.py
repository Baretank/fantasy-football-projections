from typing import Dict, List, Any, Optional
import pandas as pd
import logging
import nfl_data_py as nfl

logger = logging.getLogger(__name__)

class NFLDataPyAdapter:
    """
    Adapter for the nfl-data-py package to retrieve NFL statistics.
    
    This adapter provides methods to fetch player data, weekly stats,
    and team stats from the nfl-data-py package.
    """
    
    async def get_players(self, season: int) -> pd.DataFrame:
        """
        Get player data for the specified season.
        
        Args:
            season: The NFL season year (e.g., 2023)
            
        Returns:
            DataFrame containing player information
        """
        logger.info(f"Fetching player data for season {season} from nfl-data-py")
        try:
            # Import player data
            player_data = nfl.import_players([season])
            logger.info(f"Retrieved {len(player_data)} players for season {season}")
            return player_data
        except Exception as e:
            logger.error(f"Error fetching player data: {str(e)}")
            raise
        
    async def get_weekly_stats(self, season: int) -> pd.DataFrame:
        """
        Get weekly statistics for the specified season.
        
        Args:
            season: The NFL season year (e.g., 2023)
            
        Returns:
            DataFrame containing weekly player statistics
        """
        logger.info(f"Fetching weekly stats for season {season} from nfl-data-py")
        try:
            # Import weekly data
            weekly_data = nfl.import_weekly_data([season])
            logger.info(f"Retrieved {len(weekly_data)} weekly stat entries for season {season}")
            return weekly_data
        except Exception as e:
            logger.error(f"Error fetching weekly stats: {str(e)}")
            raise
        
    async def get_team_stats(self, season: int) -> pd.DataFrame:
        """
        Get team statistics for the specified season.
        
        Args:
            season: The NFL season year (e.g., 2023)
            
        Returns:
            DataFrame containing team statistics
        """
        logger.info(f"Fetching team stats for season {season} from nfl-data-py")
        try:
            # Import team stats
            team_data = nfl.import_team_stats([season])
            logger.info(f"Retrieved {len(team_data)} team stat entries for season {season}")
            return team_data
        except Exception as e:
            logger.error(f"Error fetching team stats: {str(e)}")
            raise
            
    async def get_schedules(self, season: int) -> pd.DataFrame:
        """
        Get NFL game schedules for the specified season.
        
        Args:
            season: The NFL season year (e.g., 2023)
            
        Returns:
            DataFrame containing game schedule information
        """
        logger.info(f"Fetching game schedules for season {season} from nfl-data-py")
        try:
            # Import schedules
            schedule_data = nfl.import_schedules([season])
            logger.info(f"Retrieved {len(schedule_data)} schedule entries for season {season}")
            return schedule_data
        except Exception as e:
            logger.error(f"Error fetching schedules: {str(e)}")
            raise
            
    async def get_rosters(self, season: int) -> pd.DataFrame:
        """
        Get team rosters for the specified season.
        
        Args:
            season: The NFL season year (e.g., 2023)
            
        Returns:
            DataFrame containing roster information
        """
        logger.info(f"Fetching team rosters for season {season} from nfl-data-py")
        try:
            # Import rosters
            roster_data = nfl.import_rosters([season])
            logger.info(f"Retrieved {len(roster_data)} roster entries for season {season}")
            return roster_data
        except Exception as e:
            logger.error(f"Error fetching rosters: {str(e)}")
            raise