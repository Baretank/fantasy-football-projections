#!/usr/bin/env python3
"""
Script to manage the active_players.csv file for player filtering.

This script provides utilities to:
1. Create a new active_players.csv file from current player data
2. Update the existing active_players.csv file with new player data
3. Validate the format and content of the active_players.csv file
"""

import sys
import os
from pathlib import Path
import pandas as pd
import argparse
import logging
from datetime import datetime

# Add project root to path for imports
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.services.adapters.nfl_data_py_adapter import NFLDataPyAdapter
from backend.database.database import SessionLocal
from backend.database.models import Player

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_active_players_from_api(season: int):
    """
    Get active players from the NFL Data API.
    
    Args:
        season: The NFL season year
        
    Returns:
        DataFrame with active player data
    """
    adapter = NFLDataPyAdapter()
    
    try:
        # Get player data from API
        logger.info(f"Fetching player data from NFL API for season {season}")
        player_data = adapter.get_players_sync(season)
        
        if player_data is None or player_data.empty:
            logger.error("Failed to retrieve player data from API")
            return None
        
        logger.info(f"Retrieved {len(player_data)} players from API")
        
        # Filter to only include players with status 'Active' or similar
        status_filter = player_data["status"].str.lower().str.contains("active|roster")
        position_filter = player_data["position"].isin(["QB", "RB", "WR", "TE"])
        
        active_players = player_data[status_filter & position_filter].copy()
        logger.info(f"Filtered to {len(active_players)} active fantasy-relevant players")
        
        # Select and rename columns for the active_players.csv format
        if "display_name" in active_players.columns:
            active_players["name"] = active_players["display_name"]
        
        if "team_abbr" in active_players.columns:
            active_players["team"] = active_players["team_abbr"]
        
        # Select only the columns we need
        required_columns = ["name", "team", "position", "player_id"]
        optional_columns = ["status", "height", "weight", "date_of_birth"]
        
        columns_to_keep = []
        for col in required_columns + optional_columns:
            if col in active_players.columns:
                columns_to_keep.append(col)
        
        # Check if we have all required columns
        missing_required = [col for col in required_columns if col not in columns_to_keep]
        if missing_required:
            logger.error(f"Missing required columns in API data: {missing_required}")
            return None
        
        result = active_players[columns_to_keep].copy()
        
        # Add an Active status column if not present
        if "status" not in result.columns:
            result["status"] = "Active"
        
        # Filter out any rows with missing team or name
        result = result.dropna(subset=["name", "team"])
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching player data from API: {str(e)}")
        return None


def get_active_players_from_db():
    """
    Get active players from the database.
    
    Returns:
        DataFrame with active player data
    """
    db = SessionLocal()
    try:
        # Query active players from database
        players = (
            db.query(Player)
            .filter(Player.status == "Active")
            .filter(Player.position.in_(["QB", "RB", "WR", "TE"]))
            .all()
        )
        
        if not players:
            logger.error("No active players found in database")
            return None
        
        logger.info(f"Retrieved {len(players)} active players from database")
        
        # Convert to DataFrame
        player_data = []
        for player in players:
            player_dict = {
                "name": player.name,
                "team": player.team,
                "position": player.position,
                "player_id": player.player_id,
                "status": player.status
            }
            
            # Add optional fields if available
            if player.height is not None:
                player_dict["height"] = player.height
            if player.weight is not None:
                player_dict["weight"] = player.weight
            if player.date_of_birth is not None:
                player_dict["date_of_birth"] = player.date_of_birth
                
            player_data.append(player_dict)
        
        df = pd.DataFrame(player_data)
        return df
        
    except Exception as e:
        logger.error(f"Error fetching player data from database: {str(e)}")
        return None
    finally:
        db.close()


def create_active_players_csv(output_path: str, season: int = None, use_db: bool = False):
    """
    Create a new active_players.csv file.
    
    Args:
        output_path: Path to save the CSV file
        season: NFL season to get player data from (if using API)
        use_db: Whether to use the database as the data source
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get player data from the appropriate source
        if use_db:
            logger.info("Getting active players from database")
            player_data = get_active_players_from_db()
        else:
            if season is None:
                # Default to current year
                season = datetime.now().year
            logger.info(f"Getting active players from API for season {season}")
            player_data = get_active_players_from_api(season)
        
        if player_data is None or player_data.empty:
            logger.error("Failed to get player data")
            return False
        
        # Save to CSV
        player_data.to_csv(output_path, index=False)
        logger.info(f"Created active_players.csv with {len(player_data)} players at {output_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating active_players.csv: {str(e)}")
        return False


def update_active_players_csv(csv_path: str, season: int = None, use_db: bool = False):
    """
    Update an existing active_players.csv file with new player data.
    
    Args:
        csv_path: Path to the existing CSV file
        season: NFL season to get player data from (if using API)
        use_db: Whether to use the database as the data source
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Check if file exists
        if not os.path.exists(csv_path):
            logger.error(f"File not found: {csv_path}")
            return False
        
        # Read existing CSV
        existing_data = pd.read_csv(csv_path)
        logger.info(f"Read {len(existing_data)} players from existing CSV")
        
        # Get new player data
        if use_db:
            logger.info("Getting active players from database")
            new_data = get_active_players_from_db()
        else:
            if season is None:
                season = datetime.now().year
            logger.info(f"Getting active players from API for season {season}")
            new_data = get_active_players_from_api(season)
        
        if new_data is None or new_data.empty:
            logger.error("Failed to get new player data")
            return False
        
        # Create backup of existing file
        backup_path = f"{csv_path}.bak"
        existing_data.to_csv(backup_path, index=False)
        logger.info(f"Created backup at {backup_path}")
        
        # Merge data - prioritize new data but keep players from old data
        # that aren't in the new data
        
        # First, identify key columns for merging
        if "player_id" in existing_data.columns and "player_id" in new_data.columns:
            # If both have player_id, use that as the key
            merge_key = "player_id"
        else:
            # Otherwise use name and team
            merge_key = ["name", "team"]
        
        # Perform outer merge to get all players
        if isinstance(merge_key, list):
            merged_data = pd.merge(
                new_data, existing_data, on=merge_key, how="outer", suffixes=("", "_old")
            )
        else:
            merged_data = pd.merge(
                new_data, existing_data, on=merge_key, how="outer", suffixes=("", "_old")
            )
        
        # For each column, prefer the new data
        for col in existing_data.columns:
            if col in new_data.columns and f"{col}_old" in merged_data.columns:
                # Fill NaN values in the new column with values from the old column
                mask = merged_data[col].isna()
                merged_data.loc[mask, col] = merged_data.loc[mask, f"{col}_old"]
                # Drop the old column
                merged_data = merged_data.drop(columns=[f"{col}_old"])
        
        # Save merged data
        merged_data.to_csv(csv_path, index=False)
        logger.info(f"Updated active_players.csv with {len(merged_data)} players")
        
        # Log changes
        added = len(merged_data) - len(existing_data)
        if added > 0:
            logger.info(f"Added {added} new players")
        elif added < 0:
            logger.info(f"Removed {abs(added)} players")
        
        return True
        
    except Exception as e:
        logger.error(f"Error updating active_players.csv: {str(e)}")
        return False


def validate_active_players_csv(csv_path: str):
    """
    Validate the format and content of an active_players.csv file.
    
    Args:
        csv_path: Path to the CSV file
        
    Returns:
        True if valid, False otherwise
    """
    try:
        # Check if file exists
        if not os.path.exists(csv_path):
            logger.error(f"File not found: {csv_path}")
            return False
        
        # Read CSV
        df = pd.read_csv(csv_path)
        logger.info(f"Read {len(df)} players from {csv_path}")
        
        # Check required columns
        required_columns = ["name", "team", "position"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"Missing required columns: {missing_columns}")
            return False
        
        # Check for missing values in required columns
        for col in required_columns:
            null_count = df[col].isna().sum()
            if null_count > 0:
                logger.warning(f"Found {null_count} null values in '{col}' column")
        
        # Check position values
        valid_positions = ["QB", "RB", "WR", "TE"]
        invalid_positions = df[~df["position"].isin(valid_positions)]["position"].unique()
        if len(invalid_positions) > 0:
            logger.warning(f"Found invalid positions: {invalid_positions}")
        
        # Check for duplicates
        if "player_id" in df.columns:
            # Check for duplicate player_ids
            duplicate_ids = df[df.duplicated("player_id", keep=False)]
            if not duplicate_ids.empty:
                logger.warning(f"Found {len(duplicate_ids)} duplicate player_ids")
                logger.debug(f"Duplicate player_ids: {duplicate_ids['player_id'].unique()}")
        
        # Check for duplicate name+team combinations
        duplicate_players = df[df.duplicated(["name", "team"], keep=False)]
        if not duplicate_players.empty:
            logger.warning(f"Found {len(duplicate_players)} duplicate name+team combinations")
            for _, group in duplicate_players.groupby(["name", "team"]):
                logger.debug(f"Duplicate: {group['name'].iloc[0]} ({group['team'].iloc[0]})")
        
        logger.info("Validation completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error validating active_players.csv: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Manage the active_players.csv file")
    parser.add_argument(
        "--season", type=int, help="NFL season year (defaults to current year)"
    )
    parser.add_argument(
        "--use-db", action="store_true", help="Use database as data source instead of API"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new active_players.csv file")
    create_parser.add_argument(
        "--output",
        type=str,
        default=os.path.join(project_root, "data", "active_players.csv"),
        help="Path to save the CSV file",
    )
    
    # Update command
    update_parser = subparsers.add_parser("update", help="Update an existing active_players.csv file")
    update_parser.add_argument(
        "--csv-path",
        type=str,
        default=os.path.join(project_root, "data", "active_players.csv"),
        help="Path to the existing CSV file",
    )
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate an active_players.csv file")
    validate_parser.add_argument(
        "--csv-path",
        type=str,
        default=os.path.join(project_root, "data", "active_players.csv"),
        help="Path to the CSV file",
    )
    
    args = parser.parse_args()
    
    # Set default command if none provided
    if args.command is None:
        parser.print_help()
        return False
    
    # Set default season if none provided
    if args.season is None:
        args.season = datetime.now().year
    
    # Execute command
    if args.command == "create":
        return create_active_players_csv(args.output, args.season, args.use_db)
    elif args.command == "update":
        return update_active_players_csv(args.csv_path, args.season, args.use_db)
    elif args.command == "validate":
        return validate_active_players_csv(args.csv_path)
    else:
        parser.print_help()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)