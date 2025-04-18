from typing import List
from sqlalchemy.orm import Session
import pandas as pd
import logging
import uuid
from datetime import datetime
from dateutil.parser import parse as parse_date

from backend.database.models import Player
from backend.services.typing import PlayerImportResultDict
from backend.services.typing_pandas import (
    TypedDataFrame,
    safe_series_get,
    series_to_str,
    series_to_int,
)

logger = logging.getLogger(__name__)


class PlayerImportService:
    def __init__(self, db: Session):
        self.db = db

    async def import_players_from_csv(self, csv_file_path: str) -> PlayerImportResultDict:
        """
        Import or update players from a CSV file containing player details.

        Args:
            csv_file_path: Path to the CSV file with player data

        Returns:
            PlayerImportResultDict with success count and error messages
        """
        success_count = 0
        error_messages: List[str] = []

        try:
            # Read CSV file into TypedDataFrame
            try:
                raw_df = pd.read_csv(csv_file_path)
                df: TypedDataFrame = TypedDataFrame(raw_df)
            except Exception as e:
                error_msg = f"Failed to read CSV file: {str(e)}"
                logger.error(error_msg)
                return {"success_count": 0, "error_messages": [error_msg]}

            required_columns = ["name", "team", "position"]

            # Validate CSV has required columns
            if not all(col in df.df.columns for col in required_columns):
                missing = [col for col in required_columns if col not in df.df.columns]
                return {
                    "success_count": 0,
                    "error_messages": [f"CSV missing required columns: {', '.join(missing)}"],
                }

            # Process each player
            for idx in range(df.row_count()):
                try:
                    # Create Series for safer access
                    row = df.df.iloc[idx]

                    # Get required fields with type safety
                    name = series_to_str(row, "name")
                    team = series_to_str(row, "team")
                    position = series_to_str(row, "position")

                    # Skip if any required field is missing
                    if not name or not team or not position:
                        error_message = f"Missing required field at row {idx+1}: name={name}, team={team}, position={position}"
                        logger.error(error_message)
                        error_messages.append(error_message)
                        continue

                    # Check if player exists (by ID or name+position)
                    player = None

                    # Try to find by player_id if provided
                    if df.has_column("player_id"):
                        player_id = series_to_str(row, "player_id")
                        if player_id:
                            player = (
                                self.db.query(Player).filter(Player.player_id == player_id).first()
                            )

                    # If not found by ID, try to find by name and position
                    if not player:
                        player = (
                            self.db.query(Player)
                            .filter(Player.name == name, Player.position == position)
                            .first()
                        )

                    # Update existing or create new player
                    if player:
                        # Update existing player
                        player.team = team

                        # Parse date_of_birth with error handling
                        if df.has_column("date_of_birth"):
                            dob_str = safe_series_get(row, "date_of_birth")
                            if dob_str and not pd.isna(dob_str):
                                try:
                                    player.date_of_birth = parse_date(dob_str).date()
                                except (ValueError, TypeError) as e:
                                    logger.warning(
                                        f"Invalid date format for {name}: {dob_str}, {str(e)}"
                                    )

                        # Handle numeric fields with type safety
                        if df.has_column("height"):
                            player.height = series_to_int(row, "height")

                        if df.has_column("weight"):
                            player.weight = series_to_int(row, "weight")

                        # Handle string fields with type safety
                        if df.has_column("status"):
                            status = series_to_str(row, "status")
                            if status:
                                player.status = status

                        if df.has_column("depth_chart_position"):
                            depth_pos = series_to_str(row, "depth_chart_position")
                            if depth_pos:
                                player.depth_chart_position = depth_pos

                        # Handle draft fields with type safety
                        if df.has_column("draft_position"):
                            player.draft_position = series_to_int(row, "draft_position")

                        if df.has_column("draft_team"):
                            draft_team = series_to_str(row, "draft_team")
                            if draft_team:
                                player.draft_team = draft_team

                        if df.has_column("draft_round"):
                            player.draft_round = series_to_int(row, "draft_round")

                        if df.has_column("draft_pick"):
                            player.draft_pick = series_to_int(row, "draft_pick")

                        player.updated_at = datetime.utcnow()

                    else:
                        # Create new player with safe conversions
                        new_player = Player(
                            player_id=str(uuid.uuid4()), name=name, team=team, position=position
                        )

                        # Handle date_of_birth with error handling
                        if df.has_column("date_of_birth"):
                            dob_str = safe_series_get(row, "date_of_birth")
                            if dob_str and not pd.isna(dob_str):
                                try:
                                    new_player.date_of_birth = parse_date(dob_str).date()
                                except (ValueError, TypeError) as e:
                                    logger.warning(
                                        f"Invalid date format for {name}: {dob_str}, {str(e)}"
                                    )

                        # Set optional fields with type safety
                        if df.has_column("height"):
                            new_player.height = series_to_int(row, "height")

                        if df.has_column("weight"):
                            new_player.weight = series_to_int(row, "weight")

                        # String fields with defaults
                        new_player.status = series_to_str(row, "status", "Active")
                        new_player.depth_chart_position = series_to_str(
                            row, "depth_chart_position", "Backup"
                        )

                        # Draft information
                        if df.has_column("draft_position"):
                            new_player.draft_position = series_to_int(row, "draft_position")

                        if df.has_column("draft_team"):
                            new_player.draft_team = series_to_str(row, "draft_team")

                        if df.has_column("draft_round"):
                            new_player.draft_round = series_to_int(row, "draft_round")

                        if df.has_column("draft_pick"):
                            new_player.draft_pick = series_to_int(row, "draft_pick")

                        self.db.add(new_player)

                    success_count += 1

                except Exception as e:
                    # Use series_to_str to safely access name even if it caused the error
                    player_name = "Unknown"
                    try:
                        player_name = series_to_str(df.df.iloc[idx], "name", "Unknown")
                    except Exception:
                        pass

                    error_message = (
                        f"Error processing player {player_name} at row {idx+1}: {str(e)}"
                    )
                    logger.error(error_message)
                    error_messages.append(error_message)

            # Commit changes
            self.db.commit()
            return {"success_count": success_count, "error_messages": error_messages}

        except Exception as e:
            logger.error(f"Error importing players: {str(e)}")
            self.db.rollback()
            return {"success_count": 0, "error_messages": [str(e)]}
