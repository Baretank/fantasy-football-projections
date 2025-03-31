from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
import pandas as pd
import logging
import uuid
from datetime import datetime, date
from dateutil.parser import parse as parse_date
import json
from pathlib import Path

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
                        if 'date_of_birth' in df.columns and pd.notna(row['date_of_birth']):
                            existing.date_of_birth = parse_date(row['date_of_birth']).date()
                        
                        # Draft information
                        if 'draft_team' in df.columns and pd.notna(row['draft_team']):
                            existing.draft_team = row['draft_team']
                        if 'draft_round' in df.columns and pd.notna(row['draft_round']):
                            existing.draft_round = int(row['draft_round'])
                        if 'draft_pick' in df.columns and pd.notna(row['draft_pick']):
                            existing.draft_pick = int(row['draft_pick'])
                        
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
                            date_of_birth=parse_date(row['date_of_birth']).date() if 'date_of_birth' in df.columns and pd.notna(row['date_of_birth']) else None,
                            depth_chart_position="Reserve",
                            draft_team=row['draft_team'] if 'draft_team' in df.columns and pd.notna(row['draft_team']) else None,
                            draft_round=int(row['draft_round']) if 'draft_round' in df.columns and pd.notna(row['draft_round']) else None,
                            draft_pick=int(row['draft_pick']) if 'draft_pick' in df.columns and pd.notna(row['draft_pick']) else None
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
    
    async def import_rookies_from_excel(self, excel_file_path: str) -> Tuple[int, List[str]]:
        """
        Import rookies from an Excel file.
        Returns (success_count, error_messages)
        """
        success_count = 0
        error_messages = []
        
        try:
            # Read Excel file
            df = pd.read_excel(excel_file_path)
            required_columns = ['Name', 'Pos']
            
            # Validate Excel has required columns
            if not all(col in df.columns for col in required_columns):
                missing = [col for col in required_columns if col not in df.columns]
                return 0, [f"Excel missing required columns: {', '.join(missing)}"]
            
            # Process each rookie
            for _, row in df.iterrows():
                try:
                    # Check if player already exists
                    existing = self.db.query(Player).filter(
                        Player.name == row['Name'],
                        Player.position == row['Pos']
                    ).first()
                    
                    if existing:
                        # Update existing player
                        existing.status = "Rookie"
                        if 'Team' in df.columns and pd.notna(row['Team']):
                            existing.team = row['Team']
                        else:
                            existing.team = "FA"  # Free agent until drafted
                        
                        if 'Height' in df.columns and pd.notna(row['Height']):
                            # Handle height conversion if needed
                            if isinstance(row['Height'], str) and "-" in row['Height']:
                                try:
                                    feet, inches = row['Height'].split("-")
                                    existing.height = int(feet) * 12 + int(inches)
                                except (ValueError, TypeError):
                                    logger.warning(f"Invalid height format for {row['Name']}: {row['Height']}")
                            else:
                                existing.height = int(row['Height'])
                                
                        if 'Weight' in df.columns and pd.notna(row['Weight']):
                            existing.weight = int(row['Weight'])
                            
                        if 'DOB' in df.columns and pd.notna(row['DOB']):
                            try:
                                existing.date_of_birth = pd.to_datetime(row['DOB']).date()
                            except:
                                logger.warning(f"Invalid date of birth for {row['Name']}: {row['DOB']}")
                        
                        success_count += 1
                        
                    else:
                        # Create new rookie
                        height = None
                        if 'Height' in df.columns and pd.notna(row['Height']):
                            # Handle height conversion if needed
                            if isinstance(row['Height'], str) and "-" in row['Height']:
                                try:
                                    feet, inches = row['Height'].split("-")
                                    height = int(feet) * 12 + int(inches)
                                except (ValueError, TypeError):
                                    logger.warning(f"Invalid height format for {row['Name']}: {row['Height']}")
                            else:
                                height = int(row['Height'])
                        
                        dob = None
                        if 'DOB' in df.columns and pd.notna(row['DOB']):
                            try:
                                dob = pd.to_datetime(row['DOB']).date()
                            except:
                                logger.warning(f"Invalid date of birth for {row['Name']}: {row['DOB']}")
                        
                        new_rookie = Player(
                            player_id=str(uuid.uuid4()),
                            name=row['Name'],
                            position=row['Pos'],
                            team="FA" if 'Team' not in df.columns or pd.isna(row['Team']) else row['Team'],
                            status="Rookie",
                            height=height,
                            weight=int(row['Weight']) if 'Weight' in df.columns and pd.notna(row['Weight']) else None,
                            date_of_birth=dob,
                            depth_chart_position="Reserve"
                        )
                        self.db.add(new_rookie)
                        success_count += 1
                    
                except Exception as e:
                    error_message = f"Error processing rookie {row['Name']}: {str(e)}"
                    logger.error(error_message)
                    error_messages.append(error_message)
            
            # Commit changes
            self.db.commit()
            return success_count, error_messages
            
        except Exception as e:
            logger.error(f"Error importing rookies from Excel: {str(e)}")
            self.db.rollback()
            return 0, [str(e)]
    
    async def import_rookies_from_json(self, json_file_path: str) -> Tuple[int, List[str]]:
        """
        Import rookies from a JSON file created by convert_rookies.py.
        Returns (success_count, error_messages)
        """
        success_count = 0
        error_messages = []
        
        try:
            # Read JSON file
            with open(json_file_path, 'r') as f:
                data = json.load(f)
            
            if 'rookies' not in data:
                return 0, ["Invalid JSON format: 'rookies' key not found"]
            
            # Process each rookie
            for rookie in data['rookies']:
                try:
                    # Check if player already exists
                    existing = self.db.query(Player).filter(
                        Player.name == rookie['name'],
                        Player.position == rookie['position']
                    ).first()
                    
                    if existing:
                        # Update existing player
                        existing.status = "Rookie"
                        existing.team = rookie.get('team', "FA")
                        
                        if 'height' in rookie:
                            existing.height = rookie['height']
                        if 'weight' in rookie:
                            existing.weight = rookie['weight']
                        if 'date_of_birth' in rookie:
                            existing.date_of_birth = parse_date(rookie['date_of_birth']).date()
                        
                        # Draft information
                        if 'draft_team' in rookie:
                            existing.draft_team = rookie['draft_team']
                        if 'draft_round' in rookie:
                            existing.draft_round = rookie['draft_round']
                        if 'draft_pick' in rookie:
                            existing.draft_pick = rookie['draft_pick']
                        if 'draft_position' in rookie:
                            existing.draft_position = rookie['draft_position']
                        
                        success_count += 1
                        
                    else:
                        # Create new rookie
                        new_rookie = Player(
                            player_id=str(uuid.uuid4()),
                            name=rookie['name'],
                            position=rookie['position'],
                            team=rookie.get('team', "FA"),
                            status="Rookie",
                            height=rookie.get('height'),
                            weight=rookie.get('weight'),
                            date_of_birth=parse_date(rookie['date_of_birth']).date() if 'date_of_birth' in rookie else None,
                            depth_chart_position="Reserve",
                            draft_team=rookie.get('draft_team'),
                            draft_round=rookie.get('draft_round'),
                            draft_pick=rookie.get('draft_pick'),
                            draft_position=rookie.get('draft_position')
                        )
                        self.db.add(new_rookie)
                        success_count += 1
                    
                except Exception as e:
                    error_message = f"Error processing rookie {rookie['name']}: {str(e)}"
                    logger.error(error_message)
                    error_messages.append(error_message)
            
            # Commit changes
            self.db.commit()
            return success_count, error_messages
            
        except Exception as e:
            logger.error(f"Error importing rookies from JSON: {str(e)}")
            self.db.rollback()
            return 0, [str(e)]
    
    async def import_rookies(self, file_path: str) -> Tuple[int, List[str]]:
        """
        Import rookies from a file, automatically detecting the file format.
        Supports CSV, Excel (.xlsx), and JSON formats.
        Returns (success_count, error_messages)
        """
        path = Path(file_path)
        if not path.exists():
            return 0, [f"File not found: {file_path}"]
        
        file_extension = path.suffix.lower()
        
        if file_extension == '.csv':
            return await self.import_rookies_from_csv(file_path)
        elif file_extension == '.xlsx':
            return await self.import_rookies_from_excel(file_path)
        elif file_extension == '.json':
            return await self.import_rookies_from_json(file_path)
        else:
            return 0, [f"Unsupported file format: {file_extension}. Must be .csv, .xlsx, or .json"]
