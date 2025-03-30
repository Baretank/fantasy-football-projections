from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
import pandas as pd
import logging
import uuid
from datetime import datetime

from backend.database.models import Player

logger = logging.getLogger(__name__)

class RookieImportService:
    def __init__(self, db: Session):
        self.db = db
    
    async def import_rookies_from_csv(self, csv_file_path: str) -> Tuple[int, List[str]]:
        """
        Import rookies from a CSV file.
        Returns (success_count, error_messages)
        """
        success_count = 0
        error_messages = []
        
        try:
            # Read CSV file
            df = pd.read_csv(csv_file_path)
            required_columns = ['name', 'position']
            
            # Validate CSV has required columns
            if not all(col in df.columns for col in required_columns):
                missing = [col for col in required_columns if col not in df.columns]
                return 0, [f"CSV missing required columns: {', '.join(missing)}"]
            
            # Process each rookie
            for _, row in df.iterrows():
                try:
                    # Check if player already exists
                    existing = self.db.query(Player).filter(
                        Player.name == row['name'],
                        Player.position == row['position']
                    ).first()
                    
                    if existing:
                        # Update existing player
                        existing.status = "Rookie"
                        if 'team' in df.columns and pd.notna(row['team']):
                            existing.team = row['team']
                        else:
                            existing.team = "FA"  # Free agent until drafted
                        
                        if 'height' in df.columns and pd.notna(row['height']):
                            existing.height = row['height']
                        if 'weight' in df.columns and pd.notna(row['weight']):
                            existing.weight = int(row['weight'])
                        if 'age' in df.columns and pd.notna(row['age']):
                            existing.age = int(row['age'])
                        
                        success_count += 1
                        
                    else:
                        # Create new rookie
                        new_rookie = Player(
                            player_id=str(uuid.uuid4()),
                            name=row['name'],
                            position=row['position'],
                            team="FA" if 'team' not in df.columns or pd.isna(row['team']) else row['team'],
                            status="Rookie",
                            height=row['height'] if 'height' in df.columns and pd.notna(row['height']) else None,
                            weight=int(row['weight']) if 'weight' in df.columns and pd.notna(row['weight']) else None,
                            age=int(row['age']) if 'age' in df.columns and pd.notna(row['age']) else None,
                            depth_chart_position="Reserve"
                        )
                        self.db.add(new_rookie)
                        success_count += 1
                    
                except Exception as e:
                    error_message = f"Error processing rookie {row['name']}: {str(e)}"
                    logger.error(error_message)
                    error_messages.append(error_message)
            
            # Commit changes
            self.db.commit()
            return success_count, error_messages
            
        except Exception as e:
            logger.error(f"Error importing rookies: {str(e)}")
            self.db.rollback()
            return 0, [str(e)]