#!/usr/bin/env python3
"""
Script to import NFL data using the new NFL data import service.

This script provides a command-line interface to import NFL data
from nfl-data-py and NFL API sources for specific seasons.
"""

import asyncio
import argparse
import logging
import os
import sys
import traceback
from typing import List, Optional

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database.database import get_db
from backend.services.nfl_data_import_service import NFLDataImportService

# Configure logging
import os

# Ensure logs directory exists
logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(logs_dir, exist_ok=True)

log_file = os.path.join(logs_dir, "nfl_data_import.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("nfl_data_import")

async def import_season(season: int) -> None:
    """
    Import a full season of NFL data.
    
    Args:
        season: NFL season year (e.g., 2023)
    """
    logger.info(f"Starting import for season {season}")
    
    # Get database session
    db = next(get_db())
    
    try:
        # Initialize service
        service = NFLDataImportService(db)
        
        # Import full season
        results = await service.import_season(season)
        
        # Log results
        logger.info(f"Import complete for season {season}")
        logger.info(f"Results: {results}")
        
    except Exception as e:
        logger.error(f"Error importing season {season}: {str(e)}")
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        raise
    finally:
        db.close()

async def import_specific_data(seasons: List[int], data_type: str, limit: Optional[int] = None, player_limit: Optional[int] = None) -> None:
    """
    Import specific data type for multiple seasons.
    
    Args:
        seasons: List of NFL season years
        data_type: Type of data to import (players, weekly, team, totals, validate)
        limit: Optional limit to apply to imported data (for testing purposes)
        player_limit: Optional limit on number of players for weekly stats
    """
    logger.info(f"Starting import of {data_type} data for seasons {seasons}")
    if limit:
        logger.info(f"Test mode enabled with limit of {limit} records")
    if player_limit and data_type == "weekly":
        logger.info(f"Player limit enabled with limit of {player_limit} players")
    
    # Get database session
    db = next(get_db())
    
    try:
        # Initialize service
        service = NFLDataImportService(db)
        
        for season in seasons:
            logger.info(f"Importing {data_type} data for season {season}")
            
            try:
                if data_type == "players":
                    # Modified to accept limit parameter
                    if hasattr(service.import_players, "__code__") and "limit" in service.import_players.__code__.co_varnames:
                        results = await service.import_players(season, limit)
                    else:
                        # For backward compatibility with NFLDataImportService that doesn't have the limit parameter
                        logger.warning("The service doesn't support the limit parameter. Importing all data.")
                        results = await service.import_players(season)
                elif data_type == "weekly":
                    # For weekly stats, apply player limit if provided
                    if player_limit:
                        # This is a theoretical implementation - would require modification to service
                        results = await service.import_weekly_stats(season, player_limit=player_limit)
                    else:
                        results = await service.import_weekly_stats(season)
                elif data_type == "team":
                    results = await service.import_team_stats(season)
                elif data_type == "totals":
                    results = await service.calculate_season_totals(season)
                elif data_type == "validate":
                    results = await service.validate_data(season)
                else:
                    logger.error(f"Unknown data type: {data_type}")
                    return
                
                logger.info(f"Import of {data_type} data complete for season {season}")
                logger.info(f"Results: {results}")
                
            except Exception as e:
                logger.error(f"Error importing {data_type} data for season {season}: {str(e)}")
                logger.debug(f"Stack trace: {traceback.format_exc()}")
    finally:
        db.close()

async def main():
    """Main entry point for the import script."""
    parser = argparse.ArgumentParser(description='Import NFL data using the NFL data import service')
    parser.add_argument('--seasons', type=int, nargs='+', required=True, help='Seasons to import (e.g., 2022 2023)')
    parser.add_argument('--type', choices=['full', 'players', 'weekly', 'team', 'totals', 'validate'], 
                      default='full', help='Type of data to import')
    parser.add_argument('--limit', type=int, help='Limit number of records for testing (only applicable for players)')
    parser.add_argument('--player_limit', type=int, help='Limit number of players for weekly stats import')
    
    args = parser.parse_args()
    
    if args.type == 'full':
        # Import full seasons one by one
        for season in args.seasons:
            await import_season(season)
    else:
        # Import specific data type for all seasons
        await import_specific_data(args.seasons, args.type, args.limit, args.player_limit)

if __name__ == "__main__":
    asyncio.run(main())