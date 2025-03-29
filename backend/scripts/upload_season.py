import asyncio
import argparse
import logging
from pathlib import Path
import sys
import time
from typing import Optional

# Add the project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)

from backend.database import SessionLocal
from backend.services.data_import_service import DataImportService
from backend.services.data_validation import DataValidationService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path(project_root) / "data" / "import_log.txt")
    ]
)
logger = logging.getLogger(__name__)

async def import_position(
    service: DataImportService,
    position: str,
    season: int
) -> tuple[int, list[str]]:
    """Import data for a specific position."""
    start_time = time.time()
    logger.info(f"\nStarting {position} imports for {season} season...")
    
    success_count, failed = await service.import_position_group(
        position=position,
        season=season
    )
    
    duration = time.time() - start_time
    logger.info(f"\n{position} Import Complete:")
    logger.info(f"Duration: {duration:.1f} seconds")
    logger.info(f"Successfully imported: {success_count} players")
    
    if failed:
        logger.warning(f"\nFailed {position} imports:")
        for error in failed:
            logger.warning(f"- {error}")
            
        # Write failures to file
        failures_file = Path(project_root) / "data" / f"failed_{position.lower()}_imports.txt"
        with open(failures_file, 'w') as f:
            f.write('\n'.join(failed))
            
    return success_count, failed

async def verify_imports(
    service: DataImportService,
    position: str,
    season: int
) -> None:
    """Verify imported data for consistency."""
    logger.info(f"\nVerifying {position} imports...")
    
    db = service.db
    validation_service = DataValidationService(db)
    verification_issues = []
    
    # Get all players of the specified position
    from backend.database.models import Player
    players = db.query(Player).filter(Player.position == position).all()
    logger.info(f"Found {len(players)} {position} players to verify")
    
    # Process each player
    for player in players:
        # Run validation checks
        player_issues = validation_service.validate_player_data(player, season)
        
        if player_issues:
            verification_issues.extend(player_issues)
    
    # Report verification results
    if verification_issues:
        logger.warning(f"\nFound {len(verification_issues)} verification issues for {position} players:")
        for issue in verification_issues:
            logger.warning(f"- {issue}")
            
        # Write issues to file
        issues_file = Path(project_root) / "data" / f"{position.lower()}_verification_issues.txt"
        with open(issues_file, 'w') as f:
            f.write('\n'.join(verification_issues))
    else:
        logger.info(f"All {position} data verified successfully!")
    
    # Commit changes
    db.commit()

async def main():
    parser = argparse.ArgumentParser(description='Import NFL player data')
    parser.add_argument(
        '--season',
        type=int,
        required=True,
        help='Season year to import (e.g., 2024)'
    )
    parser.add_argument(
        '--position',
        choices=['QB', 'RB', 'WR', 'TE'],
        help='Optional: Import only specific position'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify data consistency after import'
    )
    
    args = parser.parse_args()
    
    # Initialize database session and service
    db = SessionLocal()
    service = DataImportService(db)
    
    try:
        # Ensure data directory exists
        data_dir = Path(project_root) / "data"
        data_dir.mkdir(exist_ok=True)
        
        # Track overall results
        total_success = 0
        total_failures: list[str] = []
        
        # Determine positions to import
        positions = [args.position] if args.position else ['QB', 'RB', 'WR', 'TE']
        
        # Process each position
        for position in positions:
            success_count, failures = await import_position(
                service=service,
                position=position,
                season=args.season
            )
            
            total_success += success_count
            total_failures.extend(failures)
            
            if args.verify:
                await verify_imports(service, position, args.season)
                
            # Small delay between positions
            if position != positions[-1]:
                await asyncio.sleep(1)
        
        # Print final summary
        logger.info("\nImport Summary:")
        logger.info(f"Total successful imports: {total_success}")
        logger.info(f"Total failed imports: {len(total_failures)}")
        
        if total_failures:
            logger.info("\nAll failures have been logged to position-specific files in the data directory")
            
    except Exception as e:
        logger.error(f"Critical error during import: {str(e)}")
        sys.exit(1)
        
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())