import asyncio
import argparse
import logging
from pathlib import Path
import sys

# Add the project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)

from backend.database import SessionLocal
from backend.services import DataImportService, TeamStatsService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def import_season_data(season: int):
    """Import season data and calculate team stats."""
    db = SessionLocal()
    try:
        # Import player data
        import_service = DataImportService(db)
        success_count, error_messages = await import_service.import_season_data(season)
        
        if error_messages:
            logger.warning("Errors during import:")
            for error in error_messages:
                logger.warning(error)
        
        # Calculate team stats
        team_stats_service = TeamStatsService(db)
        teams = {player.team for player in db.query(Player).all()}
        
        for team in teams:
            logger.info(f"Calculating team stats for {team}")
            await team_stats_service.calculate_team_stats(team, season)
            
        logger.info(f"Successfully imported {success_count} players and calculated team stats")
        
    except Exception as e:
        logger.error(f"Failed to import season data: {str(e)}")
        raise
    finally:
        db.close()

async def main():
    parser = argparse.ArgumentParser(description='Import NFL player data')
    parser.add_argument(
        '--season',
        type=int,
        required=True,
        help='Season year to import (e.g., 2024)'
    )
    
    args = parser.parse_args()
    
    try:
        await import_season_data(args.season)
    except Exception as e:
        logger.error(f"Failed to import season data: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())