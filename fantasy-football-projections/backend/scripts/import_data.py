import asyncio
import argparse
import logging
from pathlib import Path
import sys

# Add the project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)

from backend.services.data_import_service import import_season_data

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    parser = argparse.ArgumentParser(description='Import NFL player data')
    parser.add_argument(
        '--season',
        type=int,
        required=True,
        help='Season year to import (e.g., 2023)'
    )
    
    args = parser.parse_args()
    
    try:
        await import_season_data(args.season)
    except Exception as e:
        logging.error(f"Failed to import season data: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())