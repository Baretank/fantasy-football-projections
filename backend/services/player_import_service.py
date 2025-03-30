from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
import pandas as pd
import logging
import uuid
from datetime import datetime, date
from dateutil.parser import parse as parse_date

from backend.database.models import Player

logger = logging.getLogger(__name__)

class PlayerImportService:
    def __init__(self, db: Session):
        self.db = db
    
    async def import_players_from_csv(self, csv_file_path: str) -> Tuple[int, List[str]]:
        """
        Import or update players from a CSV file containing player details.
        Returns (success_count, error_messages)
        """
        success_count = 0
        error_messages = []
        
        try:
            # Read CSV file
            df = pd.read_csv(csv_file_path)
            required_columns = ['name', 'team', 'position']
            
            # Validate CSV has required columns
            if not all(col in df.columns for col in required_columns):
                missing = [col for col in required_columns if col not in df.columns]
                return 0, [f"CSV missing required columns: {', '.join(missing)}"]
            
            # Process each player
            for _, row in df.iterrows():
                try:
                    # Check if player exists (by ID or name+position)
                    player = None
                    if 'player_id' in df.columns and pd.notna(row['player_id']):
                        player = self.db.query(Player).filter(Player.player_id == row['player_id']).first()
                    
                    if not player:
                        # Try to find by name and position
                        player = self.db.query(Player).filter(
                            Player.name == row['name'],
                            Player.position == row['position']
                        ).first()
                    
                    # Update existing or create new player
                    if player:
                        # Update existing player
                        player.team = row['team']
                        if 'date_of_birth' in df.columns and pd.notna(row['date_of_birth']):
                            player.date_of_birth = parse_date(row['date_of_birth']).date()
                        if 'height' in df.columns and pd.notna(row['height']):
                            player.height = int(row['height'])  # Now stored as integer inches
                        if 'weight' in df.columns and pd.notna(row['weight']):
                            player.weight = int(row['weight'])
                        if 'status' in df.columns and pd.notna(row['status']):
                            player.status = row['status']
                        if 'depth_chart_position' in df.columns and pd.notna(row['depth_chart_position']):
                            player.depth_chart_position = row['depth_chart_position']
                        if 'draft_position' in df.columns and pd.notna(row['draft_position']):
                            player.draft_position = int(row['draft_position'])
                        if 'draft_team' in df.columns and pd.notna(row['draft_team']):
                            player.draft_team = row['draft_team']
                        if 'draft_round' in df.columns and pd.notna(row['draft_round']):
                            player.draft_round = int(row['draft_round'])
                        if 'draft_pick' in df.columns and pd.notna(row['draft_pick']):
                            player.draft_pick = int(row['draft_pick'])
                        
                        player.updated_at = datetime.utcnow()
                        
                    else:
                        # Create new player
                        new_player = Player(
                            player_id=str(uuid.uuid4()),
                            name=row['name'],
                            team=row['team'],
                            position=row['position'],
                            date_of_birth=parse_date(row['date_of_birth']).date() if 'date_of_birth' in df.columns and pd.notna(row['date_of_birth']) else None,
                            height=int(row['height']) if 'height' in df.columns and pd.notna(row['height']) else None,
                            weight=int(row['weight']) if 'weight' in df.columns and pd.notna(row['weight']) else None,
                            status=row['status'] if 'status' in df.columns and pd.notna(row['status']) else "Active",
                            depth_chart_position=row['depth_chart_position'] if 'depth_chart_position' in df.columns and pd.notna(row['depth_chart_position']) else "Backup",
                            draft_position=int(row['draft_position']) if 'draft_position' in df.columns and pd.notna(row['draft_position']) else None,
                            draft_team=row['draft_team'] if 'draft_team' in df.columns and pd.notna(row['draft_team']) else None,
                            draft_round=int(row['draft_round']) if 'draft_round' in df.columns and pd.notna(row['draft_round']) else None,
                            draft_pick=int(row['draft_pick']) if 'draft_pick' in df.columns and pd.notna(row['draft_pick']) else None
                        )
                        self.db.add(new_player)
                    
                    success_count += 1
                    
                except Exception as e:
                    error_message = f"Error processing player {row['name']}: {str(e)}"
                    logger.error(error_message)
                    error_messages.append(error_message)
                    
            # Commit changes
            self.db.commit()
            return success_count, error_messages
            
        except Exception as e:
            logger.error(f"Error importing players: {str(e)}")
            self.db.rollback()
            return 0, [str(e)]