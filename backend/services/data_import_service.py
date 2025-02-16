from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pro_football_reference_web_scraper import player_stats as pfs
import pandas as pd
import logging
from datetime import datetime
import uuid
import json
from pathlib import Path
from backend.database.models import Player, BaseStat, TeamStat

logger = logging.getLogger(__name__)

class DataImportService:
    def __init__(self, db: Session):
        self.db = db
        self.positions = ['QB', 'RB', 'WR', 'TE']
        
        # Stat mappings from PFR to our database
        self.pfr_stat_mappings = {
            'QB': {
                'Pass_Cmp': 'completions',
                'Pass_Att': 'pass_attempts',
                'Pass_Yds': 'pass_yards',
                'Pass_TD': 'pass_td',
                'Pass_Int': 'interceptions',
                'Rush_Att': 'rush_attempts',
                'Rush_Yds': 'rush_yards',
                'Rush_TD': 'rush_td'
            },
            'RB': {
                'Rush_Att': 'rush_attempts',
                'Rush_Yds': 'rush_yards',
                'Rush_TD': 'rush_td',
                'Rec_Tgt': 'targets',
                'Rec': 'receptions',
                'Rec_Yds': 'rec_yards',
                'Rec_TD': 'rec_td'
            },
            'WR': {
                'Rec_Tgt': 'targets',
                'Rec': 'receptions',
                'Rec_Yds': 'rec_yards',
                'Rec_TD': 'rec_td',
                'Rush_Att': 'rush_attempts',
                'Rush_Yds': 'rush_yards',
                'Rush_TD': 'rush_td'
            },
            'TE': {
                'Rec_Tgt': 'targets',
                'Rec': 'receptions',
                'Rec_Yds': 'rec_yards',
                'Rec_TD': 'rec_td'
            }
        }

    async def import_season_data(self, season: int = 2024) -> Tuple[int, List[str]]:
        """
        Import season total data from both PFR (veterans) and local JSON (rookies).
        Returns: (success_count, error_messages)
        """
        success_count = 0
        error_messages = []

        try:
            # Import veterans from Pro Football Reference
            logger.info("Importing veteran data from Pro Football Reference")
            veteran_stats = await self._get_veteran_season_stats(season - 1)
            for player_data in veteran_stats:
                try:
                    await self._create_or_update_player(player_data, season)
                    success_count += 1
                except Exception as e:
                    error_messages.append(f"Error importing veteran {player_data['name']}: {str(e)}")

            # Import rookies from local JSON
            logger.info("Importing rookie data from local JSON")
            rookie_stats = await self._get_rookie_data()
            for rookie_data in rookie_stats:
                try:
                    await self._create_or_update_player(rookie_data, season)
                    success_count += 1
                except Exception as e:
                    error_messages.append(f"Error importing rookie {rookie_data['name']}: {str(e)}")

            self.db.commit()
            return success_count, error_messages

        except Exception as e:
            logger.error(f"Major error during import: {str(e)}")
            self.db.rollback()
            raise

    async def _get_veteran_season_stats(self, season: int) -> List[Dict]:
        """
        Get season totals for veterans from Pro Football Reference.
        """
        players = []
        for position in self.positions:
            try:
                # Get season stats for position using PFR API
                stats_df = pfs.get_season_stats(season=season, position=position)
                
                if stats_df is None or stats_df.empty:
                    logger.warning(f"No data found for {position} in season {season}")
                    continue
                
                # Convert PFR stats to our format
                for _, row in stats_df.iterrows():
                    player_dict = {
                        'name': row['Player'],
                        'team': row['Tm'],
                        'position': position,
                        'stats': {}
                    }
                    
                    # Map stats using position-specific mappings
                    for pfr_stat, our_stat in self.pfr_stat_mappings[position].items():
                        if pfr_stat in row and pd.notna(row[pfr_stat]):
                            player_dict['stats'][our_stat] = float(row[pfr_stat])
                    
                    players.append(player_dict)
                    
            except Exception as e:
                logger.error(f"Error fetching {position} stats from PFR: {str(e)}")

        return players

    async def _get_rookie_data(self) -> List[Dict]:
        """
        Get rookie data from local JSON file.
        """
        try:
            # Construct path to rookies.json
            data_dir = Path(__file__).parent.parent.parent / "data"
            rookie_file = data_dir / "rookies.json"
            
            if not rookie_file.exists():
                logger.error(f"Rookie data file not found: {rookie_file}")
                return []
            
            with open(rookie_file, 'r') as f:
                rookie_data = json.load(f)
            
            rookies = []
            for rookie in rookie_data.get('rookies', []):
                # Convert rookie JSON format to our standard format
                rookie_dict = {
                    'name': rookie['name'],
                    'team': rookie['team'],
                    'position': rookie['position'],
                    'stats': {}
                }
                
                # Map projected stats to our format
                projected_stats = rookie.get('projected_stats', {})
                stat_mapping = self.pfr_stat_mappings[rookie['position']]
                
                for our_stat in stat_mapping.values():
                    if our_stat in projected_stats:
                        rookie_dict['stats'][our_stat] = float(projected_stats[our_stat])
                
                rookies.append(rookie_dict)
                
            return rookies
            
        except Exception as e:
            logger.error(f"Error reading rookie data: {str(e)}")
            return []

    async def _create_or_update_player(self, player_data: Dict, season: int) -> None:
        """Create or update player and their stats."""
        try:
            player = self.db.query(Player).filter(
                Player.name == player_data['name'],
                Player.position == player_data['position']
            ).first()

            if not player:
                player = Player(
                    player_id=str(uuid.uuid4()),
                    name=player_data['name'],
                    team=player_data['team'],
                    position=player_data['position']
                )
                self.db.add(player)
                self.db.flush()

            # Create base stats
            for stat_type, value in player_data.get('stats', {}).items():
                stat = BaseStat(
                    stat_id=str(uuid.uuid4()),
                    player_id=player.player_id,
                    season=season,
                    stat_type=stat_type,
                    value=value
                )
                self.db.add(stat)
                
        except SQLAlchemyError as e:
            logger.error(f"Database error for player {player_data['name']}: {str(e)}")
            raise