from typing import Dict, List, Optional, Tuple
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pro_football_reference_web_scraper import player_game_log as pgl
from pro_football_reference_web_scraper import team_game_log as tgl
from backend.database.models import Player, BaseStat
from backend.database.database import get_db
import uuid
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'data_import_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom exception for data validation errors."""
    pass

class DataImportService:
    def __init__(self, db: Session):
        self.db = db
        self.positions = ['QB', 'RB', 'WR', 'TE']
        self.stat_mappings = {
            'QB': {
                'Cmp': 'completions',
                'Att': 'attempts',
                'Yds': 'passing_yards',
                'TD': 'passing_touchdowns',
                'Int': 'interceptions',
                'Rush_Att': 'rushing_attempts',
                'Rush_Yds': 'rushing_yards',
                'Rush_TD': 'rushing_touchdowns'
            },
            'RB': {
                'Rush_Att': 'rushing_attempts',
                'Rush_Yds': 'rushing_yards',
                'Rush_TD': 'rushing_touchdowns',
                'Tgt': 'targets',
                'Rec': 'receptions',
                'Rec_Yds': 'receiving_yards',
                'Rec_TD': 'receiving_touchdowns'
            },
            'WR': {
                'Tgt': 'targets',
                'Rec': 'receptions',
                'Rec_Yds': 'receiving_yards',
                'Rec_TD': 'receiving_touchdowns'
            },
            'TE': {
                'Tgt': 'targets',
                'Rec': 'receptions',
                'Rec_Yds': 'receiving_yards',
                'Rec_TD': 'receiving_touchdowns'
            }
        }
        
        # Statistical validation rules
        self.validation_rules = {
            'completions': lambda x: 0 <= x <= 50,  # Max completions in a game
            'attempts': lambda x: 0 <= x <= 70,     # Max attempts in a game
            'passing_yards': lambda x: -30 <= x <= 600,  # Allow for losses
            'rushing_yards': lambda x: -20 <= x <= 300,
            'receiving_yards': lambda x: -10 <= x <= 300,
            'touchdowns': lambda x: 0 <= x <= 6,
        }

    async def import_player_data(self, season: int) -> Tuple[int, int, List[str]]:
        """
        Import player game logs for all relevant positions.
        Returns: (success_count, error_count, error_messages)
        """
        success_count = 0
        error_count = 0
        error_messages = []

        logger.info(f"Starting data import for {season} season")
        
        try:
            # First, get all teams for the season
            teams = await self._get_teams_for_season(season)
            
            for position in self.positions:
                logger.info(f"Importing {position} data for {season} season")
                players = await self._get_active_players(position, season, teams)
                
                for player_name in players:
                    try:
                        await self._import_player_games(player_name, position, season)
                        success_count += 1
                    except Exception as e:
                        error_msg = f"Error importing {player_name} ({position}): {str(e)}"
                        logger.error(error_msg)
                        error_messages.append(error_msg)
                        error_count += 1
                        
                    # Commit after each player to avoid large transactions
                    self.db.commit()
                    
        except Exception as e:
            logger.error(f"Major error during import: {str(e)}")
            self.db.rollback()
            raise

        logger.info(f"Import completed. Successes: {success_count}, Errors: {error_count}")
        return success_count, error_count, error_messages

    async def _get_teams_for_season(self, season: int) -> List[str]:
        """Get all NFL teams active in the given season."""
        try:
            # Use team_game_log to get all teams
            teams = set()
            # You might need to adjust this based on the actual API
            team_data = tgl.get_team_game_log(team="Kansas City Chiefs", season=season)
            if team_data is not None:
                teams.update(team_data['Tm'].unique())
            return list(teams)
        except Exception as e:
            logger.error(f"Error getting teams: {str(e)}")
            return []

    async def _get_active_players(self, position: str, season: int, teams: List[str]) -> List[str]:
        """
        Get list of active players for position by checking team rosters.
        """
        players = set()
        
        for team in teams:
            try:
                # This would need to be adjusted based on the actual API capabilities
                # You might need to scrape team roster pages
                roster = await self._get_team_roster(team, season)
                position_players = [p for p in roster if p['position'] == position]
                players.update(p['name'] for p in position_players)
            except Exception as e:
                logger.error(f"Error getting roster for {team}: {str(e)}")
                continue
                
        return list(players)

    async def _get_team_roster(self, team: str, season: int) -> List[Dict]:
        """
        Get team roster for the given season.
        This is a placeholder - implement based on available data sources.
        """
        # Implement roster retrieval logic here
        # Could scrape team pages or use another API
        return []

    def _validate_stat_value(self, stat_type: str, value: float) -> bool:
        """Validate a statistical value against defined rules."""
        if stat_type in self.validation_rules:
            return self.validation_rules[stat_type](value)
        return True  # No specific rule for this stat type

    async def _import_player_games(self, player_name: str, position: str, season: int) -> None:
        """Import and validate all games for a player."""
        logger.info(f"Importing games for {player_name} ({position})")
        
        # Get game log from Pro Football Reference
        game_log = pgl.get_player_game_log(
            player=player_name,
            position=position,
            season=season
        )
        
        if game_log is None or game_log.empty:
            logger.warning(f"No game log found for {player_name}")
            return
            
        # Create or update player record
        player = await self._get_or_create_player(player_name, position, game_log)
        
        # Process each game
        for _, game in game_log.iterrows():
            await self._process_game(game, player, position, season)

    async def _process_game(self, game, player, position: str, season: int) -> None:
        """Process and validate a single game's statistics."""
        week = self._extract_week(game)
        
        for pfr_stat, our_stat in self.stat_mappings[position].items():
            if pfr_stat in game:
                stat_value = game[pfr_stat]
                
                if pd.notna(stat_value):
                    # Validate the stat value
                    if not self._validate_stat_value(our_stat, float(stat_value)):
                        logger.warning(
                            f"Invalid stat value for {player.name}: {our_stat}={stat_value}"
                        )
                        continue
                        
                    # Create the stat record
                    base_stat = BaseStat(
                        stat_id=str(uuid.uuid4()),
                        player_id=player.player_id,
                        season=season,
                        week=week,
                        stat_type=our_stat,
                        value=float(stat_value)
                    )
                    self.db.add(base_stat)

    async def _get_or_create_player(self, player_name: str, position: str, game_log: pd.DataFrame) -> Player:
        """Get existing player record or create new one with proper error handling."""
        try:
            team = self._extract_team(game_log)
            
            player = self.db.query(Player).filter(
                Player.name == player_name,
                Player.position == position
            ).first()
            
            if not player:
                player = Player(
                    player_id=str(uuid.uuid4()),
                    name=player_name,
                    team=team,
                    position=position
                )
                self.db.add(player)
                self.db.flush()  # Get the ID without committing
                
            return player
            
        except SQLAlchemyError as e:
            logger.error(f"Database error for {player_name}: {str(e)}")
            raise

    def _extract_team(self, game_log: pd.DataFrame) -> str:
        """Extract team from game log with validation."""
        if 'Tm' in game_log.columns:
            # Get the most recent team
            team = game_log['Tm'].iloc[-1]
            if pd.notna(team) and isinstance(team, str):
                return team
                
        logger.warning("Could not extract team from game log")
        return 'UNK'

    def _extract_week(self, game) -> Optional[int]:
        """Extract and validate week number from game data."""
        try:
            if 'Week' in game:
                week = int(game['Week'])
                if 1 <= week <= 18:  # Valid NFL week numbers
                    return week
                    
            logger.warning(f"Invalid week number in game data: {game.get('Week')}")
            return None
            
        except (ValueError, TypeError) as e:
            logger.error(f"Error extracting week number: {str(e)}")
            return None

# Helper function to run the import
async def import_season_data(season: int) -> Tuple[int, int, List[str]]:
    """
    Import data for a complete season.
    Returns (success_count, error_count, error_messages)
    """
    db = next(get_db())
    try:
        importer = DataImportService(db)
        return await importer.import_player_data(season)
    finally:
        db.close()