import sys
from pathlib import Path
import pandas as pd
import argparse
import logging
from datetime import datetime
import uuid

# Add the project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)

from backend.database.database import engine, Base, SessionLocal
from backend.database.models import Player

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def seed_players_from_csv(csv_file_path: str):
    """
    Seed the database with players from a CSV file.
    """
    db = SessionLocal()
    try:
        # Check if file exists
        file_path = Path(csv_file_path)
        if not file_path.exists():
            logger.error(f"File not found: {csv_file_path}")
            return False
            
        # Read CSV file
        df = pd.read_csv(csv_file_path)
        logger.info(f"Found {len(df)} players in CSV file")
        
        # Check required columns
        required_columns = ['name', 'team', 'position']
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            logger.error(f"CSV missing required columns: {', '.join(missing)}")
            return False
        
        # Track counts
        added_count = 0
        updated_count = 0
        error_count = 0
        
        # Process each player
        for _, row in df.iterrows():
            try:
                # Check if player exists
                existing_player = None
                
                # Check by ID if provided
                if 'player_id' in df.columns and pd.notna(row['player_id']):
                    existing_player = db.query(Player).filter(
                        Player.player_id == row['player_id']
                    ).first()
                
                # If not found by ID, try by name and position
                if not existing_player:
                    existing_player = db.query(Player).filter(
                        Player.name == row['name'],
                        Player.position == row['position']
                    ).first()
                
                if existing_player:
                    # Update existing player
                    existing_player.team = row['team']
                    
                    # Update additional fields if available
                    if 'date_of_birth' in df.columns and pd.notna(row['date_of_birth']):
                        try:
                            existing_player.date_of_birth = pd.to_datetime(row['date_of_birth']).date()
                        except:
                            logger.warning(f"Invalid date of birth for {row['name']}: {row['date_of_birth']}")
                    
                    if 'height' in df.columns and pd.notna(row['height']):
                        existing_player.height = int(row['height'])
                    
                    if 'weight' in df.columns and pd.notna(row['weight']):
                        existing_player.weight = int(row['weight'])
                    
                    if 'status' in df.columns and pd.notna(row['status']):
                        existing_player.status = row['status']
                    
                    if 'depth_chart_position' in df.columns and pd.notna(row['depth_chart_position']):
                        existing_player.depth_chart_position = row['depth_chart_position']
                    
                    if 'draft_team' in df.columns and pd.notna(row['draft_team']):
                        existing_player.draft_team = row['draft_team']
                    
                    if 'draft_round' in df.columns and pd.notna(row['draft_round']):
                        existing_player.draft_round = int(row['draft_round'])
                    
                    if 'draft_pick' in df.columns and pd.notna(row['draft_pick']):
                        existing_player.draft_pick = int(row['draft_pick'])
                    
                    existing_player.updated_at = datetime.utcnow()
                    updated_count += 1
                    
                else:
                    # Create new player
                    new_player = Player(
                        player_id=str(uuid.uuid4()),
                        name=row['name'],
                        team=row['team'],
                        position=row['position'],
                        date_of_birth=pd.to_datetime(row['date_of_birth']).date() if 'date_of_birth' in df.columns and pd.notna(row['date_of_birth']) else None,
                        height=int(row['height']) if 'height' in df.columns and pd.notna(row['height']) else None,
                        weight=int(row['weight']) if 'weight' in df.columns and pd.notna(row['weight']) else None,
                        status=row['status'] if 'status' in df.columns and pd.notna(row['status']) else "Active",
                        depth_chart_position=row['depth_chart_position'] if 'depth_chart_position' in df.columns and pd.notna(row['depth_chart_position']) else "Backup",
                        draft_team=row['draft_team'] if 'draft_team' in df.columns and pd.notna(row['draft_team']) else None,
                        draft_round=int(row['draft_round']) if 'draft_round' in df.columns and pd.notna(row['draft_round']) else None,
                        draft_pick=int(row['draft_pick']) if 'draft_pick' in df.columns and pd.notna(row['draft_pick']) else None
                    )
                    db.add(new_player)
                    added_count += 1
                
            except Exception as e:
                logger.error(f"Error processing player {row['name']}: {str(e)}")
                error_count += 1
        
        # Commit changes
        db.commit()
        logger.info(f"Database seeding complete:")
        logger.info(f"  Added: {added_count} players")
        logger.info(f"  Updated: {updated_count} players")
        logger.info(f"  Errors: {error_count} players")
        
        return True
        
    except Exception as e:
        logger.error(f"Error seeding database: {str(e)}")
        db.rollback()
        return False
    finally:
        db.close()

def main():
    parser = argparse.ArgumentParser(description='Seed the database with initial data')
    parser.add_argument(
        '--players',
        type=str,
        help='Path to players CSV file',
        default=str(Path(project_root) / "data" / "active_players.csv")
    )
    parser.add_argument(
        '--init-db',
        action='store_true',
        help='Initialize the database schema'
    )
    
    args = parser.parse_args()
    
    # Initialize database if requested
    if args.init_db:
        logger.info("Initializing database schema...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema initialized successfully.")
    
    # Seed players
    if args.players:
        logger.info(f"Seeding players from {args.players}...")
        success = seed_players_from_csv(args.players)
        if success:
            logger.info("Player seeding completed successfully.")
        else:
            logger.error("Player seeding failed!")

if __name__ == "__main__":
    main()