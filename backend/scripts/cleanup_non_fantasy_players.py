"""
Script to clean up non-fantasy relevant players from the database.

This script:
1. Identifies players with positions that aren't relevant to fantasy football (not QB, RB, WR, TE)
2. Removes them and any associated data from the database
3. Reports on how many records were cleaned up

Usage:
    python cleanup_non_fantasy_players.py

Note: Be sure to back up your database before running this script.
"""

import logging
import sys
import os
from typing import Dict, Any, List
import pandas as pd
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker

# Add parent directory to path so we can import the backend modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from database.database import engine, SessionLocal
from database.models import Player, GameStats, BaseStat, Projection, TeamStat

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def cleanup_non_fantasy_players():
    """
    Remove non-fantasy players from the database.

    This function removes players who have positions other than QB, RB, WR, TE,
    along with all their associated data including game stats, base stats,
    and projections.

    Returns:
        Dict containing cleanup results
    """
    db = SessionLocal()
    try:
        logger.info("Starting cleanup of non-fantasy players")

        # Get all non-fantasy players (not QB, RB, WR, TE)
        fantasy_positions = ["QB", "RB", "WR", "TE"]
        non_fantasy_players = db.query(Player).filter(~Player.position.in_(fantasy_positions)).all()

        if not non_fantasy_players:
            logger.info("No non-fantasy players found in database. No cleanup needed.")
            return {
                "players_removed": 0,
                "game_stats_removed": 0,
                "base_stats_removed": 0,
                "projections_removed": 0,
            }

        logger.info(f"Found {len(non_fantasy_players)} non-fantasy players to remove")

        # Collect player IDs for bulk deletion
        player_ids = [p.player_id for p in non_fantasy_players]

        # Count and delete associated data
        game_stats_count = db.query(GameStats).filter(GameStats.player_id.in_(player_ids)).count()
        base_stats_count = db.query(BaseStat).filter(BaseStat.player_id.in_(player_ids)).count()
        projections_count = (
            db.query(Projection).filter(Projection.player_id.in_(player_ids)).count()
        )

        logger.info(f"Found {game_stats_count} game stats to remove")
        logger.info(f"Found {base_stats_count} base stats to remove")
        logger.info(f"Found {projections_count} projections to remove")

        # Delete associated data first (due to foreign key constraints)
        if game_stats_count > 0:
            db.query(GameStats).filter(GameStats.player_id.in_(player_ids)).delete(
                synchronize_session=False
            )

        if base_stats_count > 0:
            db.query(BaseStat).filter(BaseStat.player_id.in_(player_ids)).delete(
                synchronize_session=False
            )

        if projections_count > 0:
            db.query(Projection).filter(Projection.player_id.in_(player_ids)).delete(
                synchronize_session=False
            )

        # Finally, delete the players
        for player in non_fantasy_players:
            db.delete(player)

        # Commit the deletions
        db.commit()
        logger.info(
            f"Successfully removed {len(non_fantasy_players)} non-fantasy players and associated data"
        )

        return {
            "players_removed": len(non_fantasy_players),
            "game_stats_removed": game_stats_count,
            "base_stats_removed": base_stats_count,
            "projections_removed": projections_count,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error cleaning up non-fantasy players: {str(e)}")
        raise
    finally:
        db.close()


def main():
    """Main function to run cleanup script."""
    try:
        results = cleanup_non_fantasy_players()

        # Display a summary
        logger.info("=== Cleanup Summary ===")
        logger.info(f"Players removed: {results['players_removed']}")
        logger.info(f"Game stats removed: {results['game_stats_removed']}")
        logger.info(f"Base stats removed: {results['base_stats_removed']}")
        logger.info(f"Projections removed: {results['projections_removed']}")
        logger.info("======================")

        if results["players_removed"] > 0:
            logger.info(
                "Cleanup completed successfully. The database now contains only fantasy-relevant players."
            )
        else:
            logger.info(
                "No cleanup was necessary. The database already contains only fantasy-relevant players."
            )

    except Exception as e:
        logger.error(f"Script failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
