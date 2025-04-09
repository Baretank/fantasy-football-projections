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
            season: The NFL season year (e.g., 2023) - used for logging only
            
        Returns:
            DataFrame containing player information
        """
        logger.info(f"Fetching player data (focusing on season {season}) from nfl-data-py")
        try:
            # Import player data - nfl_data_py import_players() doesn't accept a season parameter
            player_data = nfl.import_players()
            
            # We'll return all player data and filter by season in the service layer if needed
            # This will allow us to focus on 2024 players when we process the data
            logger.info(f"Retrieved {len(player_data)} players total")
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
            DataFrame containing team metadata and basic team stats
        """
        logger.info(f"Fetching team stats for season {season} from nfl-data-py")
        try:
            # Import team descriptions for metadata
            team_desc = nfl.import_team_desc()
            
            # Get real team stats from nfl_data_py API
            # First import team level season stats
            team_stats = nfl.import_team_season_stats([season])
            if team_stats is None or len(team_stats) == 0:
                logger.warning(f"No team stats found for season {season}, falling back to weekly aggregation")
                # If no team stats, we can try to aggregate from weekly data
                weekly_data = nfl.import_weekly_data([season])
                if weekly_data is not None and len(weekly_data) > 0:
                    # Group by team and calculate aggregate stats
                    team_stats = weekly_data.groupby('recent_team').agg({
                        'passing_yards': 'sum',
                        'passing_tds': 'sum',
                        'passing_att': 'sum',
                        'rushing_yards': 'sum',
                        'rushing_tds': 'sum',
                        'rushing_att': 'sum',
                        'receptions': 'sum',
                        'targets': 'sum',
                        'receiving_yards': 'sum',
                        'receiving_tds': 'sum'
                    }).reset_index()
                    team_stats = team_stats.rename(columns={'recent_team': 'team'})
                
            # Process the data and match our required format
            teams_data = []
            team_abbrs = team_desc['team_abbr'].tolist()
            
            # For each team in our team descriptions
            for _, team in team_desc.iterrows():
                team_abbr = team['team_abbr']
                
                # Find this team in the stats dataframe
                team_row = None
                if team_stats is not None and len(team_stats) > 0:
                    team_matches = team_stats[team_stats['team'] == team_abbr]
                    if len(team_matches) > 0:
                        team_row = team_matches.iloc[0]
                
                # Create the team data entry - using real data if available, placeholders if not
                if team_row is not None:
                    # Get actual values with fallbacks
                    pass_att = team_row.get('passing_att', 0) if pd.notna(team_row.get('passing_att', 0)) else 550
                    rush_att = team_row.get('rushing_att', 0) if pd.notna(team_row.get('rushing_att', 0)) else 450
                    total_plays = pass_att + rush_att
                    pass_percentage = (pass_att / total_plays * 100) if total_plays > 0 else 55.0
                    
                    pass_yards = team_row.get('passing_yards', 0) if pd.notna(team_row.get('passing_yards', 0)) else 4000
                    pass_td = team_row.get('passing_tds', 0) if pd.notna(team_row.get('passing_tds', 0)) else 25
                    pass_td_rate = (pass_td / pass_att * 100) if pass_att > 0 else 4.5
                    
                    rush_yards = team_row.get('rushing_yards', 0) if pd.notna(team_row.get('rushing_yards', 0)) else 1800
                    rush_td = team_row.get('rushing_tds', 0) if pd.notna(team_row.get('rushing_tds', 0)) else 15
                    rush_ypc = (rush_yards / rush_att) if rush_att > 0 else 4.0
                    
                    targets = team_row.get('targets', 0) if pd.notna(team_row.get('targets', 0)) else pass_att
                    receptions = team_row.get('receptions', 0) if pd.notna(team_row.get('receptions', 0)) else 350
                    rec_yards = team_row.get('receiving_yards', 0) if pd.notna(team_row.get('receiving_yards', 0)) else pass_yards
                    rec_td = team_row.get('receiving_tds', 0) if pd.notna(team_row.get('receiving_tds', 0)) else pass_td
                    
                    # Team rank is estimated (could be refined with more data)
                    rank = team_row.get('rank', 16) if pd.notna(team_row.get('rank', 16)) else 16
                    
                    team_data = {
                        'team': team_abbr,
                        'season': season,
                        'plays': total_plays,
                        'pass_percentage': pass_percentage,
                        'pass_attempts': pass_att,
                        'pass_yards': pass_yards,
                        'pass_td': pass_td,
                        'pass_td_rate': pass_td_rate,
                        'rush_attempts': rush_att,
                        'rush_yards': rush_yards,
                        'rush_td': rush_td,
                        'rush_yards_per_carry': rush_ypc,
                        'targets': targets,
                        'receptions': receptions,
                        'rec_yards': rec_yards,
                        'rec_td': rec_td,
                        'rank': rank
                    }
                else:
                    # Use placeholder data if no stats found
                    team_data = {
                        'team': team_abbr,
                        'season': season,
                        'plays': 1000,  # Placeholder values
                        'pass_percentage': 55.0,
                        'pass_attempts': 550,
                        'pass_yards': 4000,
                        'pass_td': 25,
                        'pass_td_rate': 4.5,
                        'rush_attempts': 450,
                        'rush_yards': 1800,
                        'rush_td': 15,
                        'rush_yards_per_carry': 4.0,
                        'targets': 550,
                        'receptions': 350,
                        'rec_yards': 4000,
                        'rec_td': 25,
                        'rank': 16  # Middle rank as default
                    }
                    logger.warning(f"Using placeholder data for team {team_abbr} - no stats found")
                
                teams_data.append(team_data)
            
            # Convert to DataFrame
            team_data_df = pd.DataFrame(teams_data)
            
            if team_stats is not None and len(team_stats) > 0:
                logger.info(f"Created team stats with real data for {len(team_data_df)} teams")
            else:
                logger.info(f"Created placeholder team stats for {len(team_data_df)} teams")
            
            return team_data_df
            
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
            
    async def get_player_weekly_stats(self, player_id: str, season: int) -> pd.DataFrame:
        """
        Get weekly statistics for a specific player.
        
        Args:
            player_id: The player ID to get stats for
            season: The NFL season year (e.g., 2023)
            
        Returns:
            DataFrame containing player's weekly statistics
        """
        logger.info(f"Fetching weekly stats for player {player_id} in season {season}")
        try:
            # Get all weekly data for the season
            weekly_data = await self.get_weekly_stats(season)
            
            # Filter for the specific player
            player_data = weekly_data[weekly_data['player_id'] == player_id].copy()
            
            logger.info(f"Found {len(player_data)} weekly stat entries for player {player_id}")
            return player_data
        except Exception as e:
            logger.error(f"Error fetching player weekly stats: {str(e)}")
            raise