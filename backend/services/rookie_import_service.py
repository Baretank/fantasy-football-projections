from sqlalchemy.orm import Session
import pandas as pd
import logging
import uuid
from dateutil.parser import parse as parse_date
import json
from pathlib import Path

from backend.database.models import Player
from backend.services.typing import RookieImportResultDict, safe_dict_get
from backend.services.typing_pandas import (
    TypedDataFrame,
    safe_series_get,
    series_to_int,
    series_to_str,
)

logger = logging.getLogger(__name__)


class RookieImportService:
    def __init__(self, db: Session):
        self.db = db

    async def import_rookies_from_csv(self, csv_file_path: str) -> RookieImportResultDict:
        """
        Import rookies from a CSV file.

        Args:
            csv_file_path: Path to the CSV file containing rookie data

        Returns:
            RookieImportResultDict with success count and any error messages
        """
        success_count = 0
        error_messages = []

        try:
            # Read CSV file and wrap in TypedDataFrame
            df_raw = pd.read_csv(csv_file_path)
            df = TypedDataFrame(df_raw)
            required_columns = ["name", "position"]

            # Validate CSV has required columns
            if not all(col in df.df.columns for col in required_columns):
                missing = [col for col in required_columns if col not in df.df.columns]
                return {
                    "success_count": 0,
                    "error_messages": [f"CSV missing required columns: {', '.join(missing)}"],
                }

            # Process each rookie
            for idx in range(df.row_count()):
                try:
                    # Get the row as Series for safer access
                    row = df.df.iloc[idx]

                    # Extract required fields with type safety
                    name = series_to_str(row, "name")
                    position = series_to_str(row, "position")

                    if not name or not position:
                        error_message = f"Missing required field at row {idx+1}: name={name}, position={position}"
                        logger.error(error_message)
                        error_messages.append(error_message)
                        continue

                    # Check if player already exists
                    existing = (
                        self.db.query(Player)
                        .filter(Player.name == name, Player.position == position)
                        .first()
                    )

                    has_team = "team" in df.df.columns
                    has_height = "height" in df.df.columns
                    has_weight = "weight" in df.df.columns
                    has_dob = "date_of_birth" in df.df.columns
                    has_draft_team = "draft_team" in df.df.columns
                    has_draft_round = "draft_round" in df.df.columns
                    has_draft_pick = "draft_pick" in df.df.columns

                    if existing:
                        # Update existing player
                        existing.status = "Rookie"

                        # Update team with proper null handling
                        if has_team:
                            team = series_to_str(row, "team")
                            existing.team = "FA" if not team else team
                        else:
                            existing.team = "FA"  # Free agent until drafted

                        # Update measurements with type-safe conversions
                        if has_height:
                            existing.height = series_to_str(row, "height")

                        if has_weight:
                            existing.weight = series_to_int(row, "weight")

                        if has_dob and not pd.isna(safe_series_get(row, "date_of_birth")):
                            try:
                                dob_value = series_to_str(row, "date_of_birth")
                                existing.date_of_birth = (
                                    parse_date(dob_value).date() if dob_value else None
                                )
                            except (ValueError, TypeError):
                                logger.warning(
                                    f"Invalid date format for {name}: {safe_series_get(row, 'date_of_birth')}"
                                )

                        # Draft information with type-safe conversions
                        if has_draft_team:
                            existing.draft_team = series_to_str(row, "draft_team")

                        if has_draft_round:
                            existing.draft_round = series_to_int(row, "draft_round")

                        if has_draft_pick:
                            existing.draft_pick = series_to_int(row, "draft_pick")

                        success_count += 1
                    else:
                        # Create new rookie with type-safe conversions
                        # Handle date of birth with proper error handling
                        dob = None
                        if has_dob and not pd.isna(safe_series_get(row, "date_of_birth")):
                            try:
                                dob_value = series_to_str(row, "date_of_birth")
                                dob = parse_date(dob_value).date() if dob_value else None
                            except (ValueError, TypeError):
                                logger.warning(
                                    f"Invalid date format for {name}: {safe_series_get(row, 'date_of_birth')}"
                                )

                        new_rookie = Player(
                            player_id=str(uuid.uuid4()),
                            name=name,
                            position=position,
                            team=series_to_str(row, "team", "FA") if has_team else "FA",
                            status="Rookie",
                            height=series_to_str(row, "height") if has_height else None,
                            weight=series_to_int(row, "weight") if has_weight else None,
                            date_of_birth=dob,
                            depth_chart_position="Reserve",
                            draft_team=series_to_str(row, "draft_team") if has_draft_team else None,
                            draft_round=(
                                series_to_int(row, "draft_round") if has_draft_round else None
                            ),
                            draft_pick=series_to_int(row, "draft_pick") if has_draft_pick else None,
                        )
                        self.db.add(new_rookie)
                        success_count += 1

                except Exception as e:
                    player_name = series_to_str(df.df.iloc[idx], "name", f"Row {idx+1}")
                    error_message = f"Error processing rookie {player_name}: {str(e)}"
                    logger.error(error_message)
                    error_messages.append(error_message)

            # Commit changes
            self.db.commit()
            return {"success_count": success_count, "error_messages": error_messages}

        except Exception as e:
            logger.error(f"Error importing rookies from CSV: {str(e)}")
            self.db.rollback()
            return {"success_count": 0, "error_messages": [str(e)]}

    async def import_rookies_from_excel(self, excel_file_path: str) -> RookieImportResultDict:
        """
        Import rookies from an Excel file.

        Args:
            excel_file_path: Path to the Excel file containing rookie data

        Returns:
            RookieImportResultDict with success count and any error messages
        """
        success_count = 0
        error_messages = []

        try:
            # Read Excel file and wrap in TypedDataFrame
            df_raw = pd.read_excel(excel_file_path)
            df = TypedDataFrame(df_raw)
            required_columns = ["Name", "Pos"]

            # Validate Excel has required columns
            if not all(col in df.df.columns for col in required_columns):
                missing = [col for col in required_columns if col not in df.df.columns]
                return {
                    "success_count": 0,
                    "error_messages": [f"Excel missing required columns: {', '.join(missing)}"],
                }

            # Process each rookie
            for idx in range(df.row_count()):
                try:
                    # Get the row as Series for safer access
                    row = df.df.iloc[idx]

                    # Extract required fields with type safety
                    name = series_to_str(row, "Name")
                    position = series_to_str(row, "Pos")

                    if not name or not position:
                        error_message = (
                            f"Missing required field at row {idx+1}: Name={name}, Pos={position}"
                        )
                        logger.error(error_message)
                        error_messages.append(error_message)
                        continue

                    # Check if player already exists
                    existing = (
                        self.db.query(Player)
                        .filter(Player.name == name, Player.position == position)
                        .first()
                    )

                    # Check column existence
                    has_team = "Team" in df.df.columns
                    has_height = "Height" in df.df.columns
                    has_weight = "Weight" in df.df.columns
                    has_dob = "DOB" in df.df.columns

                    if existing:
                        # Update existing player
                        existing.status = "Rookie"

                        # Update team with proper null handling
                        if has_team:
                            team = series_to_str(row, "Team")
                            existing.team = "FA" if not team else team
                        else:
                            existing.team = "FA"  # Free agent until drafted

                        # Handle height conversion with proper error handling
                        if has_height:
                            height_value = safe_series_get(row, "Height")
                            if not pd.isna(height_value):
                                # Handle feet-inches format
                                if isinstance(height_value, str) and "-" in height_value:
                                    try:
                                        feet, inches = height_value.split("-")
                                        existing.height = int(feet) * 12 + int(inches)
                                    except (ValueError, TypeError):
                                        logger.warning(
                                            f"Invalid height format for {name}: {height_value}"
                                        )
                                else:
                                    try:
                                        existing.height = int(float(height_value))
                                    except (ValueError, TypeError):
                                        logger.warning(
                                            f"Invalid height value for {name}: {height_value}"
                                        )

                        # Update weight with type-safe conversion
                        if has_weight:
                            existing.weight = series_to_int(row, "Weight")

                        # Handle date of birth with proper error handling
                        if has_dob and not pd.isna(safe_series_get(row, "DOB")):
                            try:
                                dob_value = safe_series_get(row, "DOB")
                                existing.date_of_birth = pd.to_datetime(dob_value).date()
                            except Exception:
                                logger.warning(
                                    f"Invalid date of birth for {name}: {safe_series_get(row, 'DOB')}"
                                )

                        success_count += 1
                    else:
                        # Process height with proper error handling
                        height = None
                        if has_height:
                            height_value = safe_series_get(row, "Height")
                            if not pd.isna(height_value):
                                # Handle feet-inches format
                                if isinstance(height_value, str) and "-" in height_value:
                                    try:
                                        feet, inches = height_value.split("-")
                                        height = int(feet) * 12 + int(inches)
                                    except (ValueError, TypeError):
                                        logger.warning(
                                            f"Invalid height format for {name}: {height_value}"
                                        )
                                else:
                                    try:
                                        height = int(float(height_value))
                                    except (ValueError, TypeError):
                                        logger.warning(
                                            f"Invalid height value for {name}: {height_value}"
                                        )

                        # Process date of birth with proper error handling
                        dob = None
                        if has_dob and not pd.isna(safe_series_get(row, "DOB")):
                            try:
                                dob_value = safe_series_get(row, "DOB")
                                dob = pd.to_datetime(dob_value).date()
                            except Exception:
                                logger.warning(
                                    f"Invalid date of birth for {name}: {safe_series_get(row, 'DOB')}"
                                )

                        # Create new rookie with type-safe conversions
                        new_rookie = Player(
                            player_id=str(uuid.uuid4()),
                            name=name,
                            position=position,
                            team=series_to_str(row, "Team", "FA") if has_team else "FA",
                            status="Rookie",
                            height=height,
                            weight=series_to_int(row, "Weight") if has_weight else None,
                            date_of_birth=dob,
                            depth_chart_position="Reserve",
                        )
                        self.db.add(new_rookie)
                        success_count += 1

                except Exception as e:
                    player_name = series_to_str(df.df.iloc[idx], "Name", f"Row {idx+1}")
                    error_message = f"Error processing rookie {player_name}: {str(e)}"
                    logger.error(error_message)
                    error_messages.append(error_message)

            # Commit changes
            self.db.commit()
            return {"success_count": success_count, "error_messages": error_messages}

        except Exception as e:
            logger.error(f"Error importing rookies from Excel: {str(e)}")
            self.db.rollback()
            return {"success_count": 0, "error_messages": [str(e)]}

    async def import_rookies_from_json(self, json_file_path: str) -> RookieImportResultDict:
        """
        Import rookies from a JSON file created by convert_rookies.py.

        Args:
            json_file_path: Path to the JSON file containing rookie data

        Returns:
            RookieImportResultDict with success count and any error messages
        """
        success_count = 0
        error_messages = []

        try:
            # Read JSON file
            with open(json_file_path, "r") as f:
                data = json.load(f)

            if "rookies" not in data:
                return {
                    "success_count": 0,
                    "error_messages": ["Invalid JSON format: 'rookies' key not found"],
                }

            # Process each rookie
            for rookie in data["rookies"]:
                try:
                    # Extract required fields with safe_dict_get for type safety
                    name = safe_dict_get(rookie, "name")
                    position = safe_dict_get(rookie, "position")

                    if not name or not position:
                        error_message = f"Missing required field in rookie data: name={name}, position={position}"
                        logger.error(error_message)
                        error_messages.append(error_message)
                        continue

                    # Check if player already exists
                    existing = (
                        self.db.query(Player)
                        .filter(Player.name == name, Player.position == position)
                        .first()
                    )

                    if existing:
                        # Update existing player
                        existing.status = "Rookie"
                        existing.team = safe_dict_get(rookie, "team", "FA")

                        # Update measurements with safe_dict_get
                        if "height" in rookie:
                            existing.height = safe_dict_get(rookie, "height")

                        if "weight" in rookie:
                            weight_value = safe_dict_get(rookie, "weight")
                            if weight_value is not None:
                                try:
                                    existing.weight = int(weight_value)
                                except (ValueError, TypeError):
                                    logger.warning(
                                        f"Invalid weight value for {name}: {weight_value}"
                                    )

                        # Handle date of birth with proper error handling
                        if "date_of_birth" in rookie:
                            dob_value = safe_dict_get(rookie, "date_of_birth")
                            if dob_value:
                                try:
                                    existing.date_of_birth = parse_date(dob_value).date()
                                except (ValueError, TypeError):
                                    logger.warning(f"Invalid date format for {name}: {dob_value}")

                        # Draft information with safe_dict_get
                        existing.draft_team = safe_dict_get(rookie, "draft_team")

                        # Handle numeric conversions safely
                        draft_round = safe_dict_get(rookie, "draft_round")
                        if draft_round is not None:
                            try:
                                existing.draft_round = int(draft_round)
                            except (ValueError, TypeError):
                                logger.warning(f"Invalid draft round for {name}: {draft_round}")

                        draft_pick = safe_dict_get(rookie, "draft_pick")
                        if draft_pick is not None:
                            try:
                                existing.draft_pick = int(draft_pick)
                            except (ValueError, TypeError):
                                logger.warning(f"Invalid draft pick for {name}: {draft_pick}")

                        existing.draft_position = safe_dict_get(rookie, "draft_position")

                        success_count += 1
                    else:
                        # Process date of birth with proper error handling
                        dob = None
                        dob_value = safe_dict_get(rookie, "date_of_birth")
                        if dob_value:
                            try:
                                dob = parse_date(dob_value).date()
                            except (ValueError, TypeError):
                                logger.warning(f"Invalid date format for {name}: {dob_value}")

                        # Handle numeric conversions safely
                        weight = None
                        weight_value = safe_dict_get(rookie, "weight")
                        if weight_value is not None:
                            try:
                                weight = int(weight_value)
                            except (ValueError, TypeError):
                                logger.warning(f"Invalid weight value for {name}: {weight_value}")

                        draft_round = None
                        draft_round_value = safe_dict_get(rookie, "draft_round")
                        if draft_round_value is not None:
                            try:
                                draft_round = int(draft_round_value)
                            except (ValueError, TypeError):
                                logger.warning(
                                    f"Invalid draft round for {name}: {draft_round_value}"
                                )

                        draft_pick = None
                        draft_pick_value = safe_dict_get(rookie, "draft_pick")
                        if draft_pick_value is not None:
                            try:
                                draft_pick = int(draft_pick_value)
                            except (ValueError, TypeError):
                                logger.warning(f"Invalid draft pick for {name}: {draft_pick_value}")

                        # Create new rookie
                        new_rookie = Player(
                            player_id=str(uuid.uuid4()),
                            name=name,
                            position=position,
                            team=safe_dict_get(rookie, "team", "FA"),
                            status="Rookie",
                            height=safe_dict_get(rookie, "height"),
                            weight=weight,
                            date_of_birth=dob,
                            depth_chart_position="Reserve",
                            draft_team=safe_dict_get(rookie, "draft_team"),
                            draft_round=draft_round,
                            draft_pick=draft_pick,
                            draft_position=safe_dict_get(rookie, "draft_position"),
                        )
                        self.db.add(new_rookie)
                        success_count += 1

                except Exception as e:
                    player_name = safe_dict_get(rookie, "name", "Unknown rookie")
                    error_message = f"Error processing rookie {player_name}: {str(e)}"
                    logger.error(error_message)
                    error_messages.append(error_message)

            # Commit changes
            self.db.commit()
            return {"success_count": success_count, "error_messages": error_messages}

        except Exception as e:
            logger.error(f"Error importing rookies from JSON: {str(e)}")
            self.db.rollback()
            return {"success_count": 0, "error_messages": [str(e)]}

    async def import_rookies(self, file_path: str) -> RookieImportResultDict:
        """
        Import rookies from a file, automatically detecting the file format.
        Supports CSV, Excel (.xlsx), and JSON formats.
        Returns (success_count, error_messages)
        """
        path = Path(file_path)
        if not path.exists():
            return {"success_count": 0, "error_messages": [f"File not found: {file_path}"]}

        file_extension = path.suffix.lower()

        if file_extension == ".csv":
            return await self.import_rookies_from_csv(file_path)
        elif file_extension == ".xlsx":
            return await self.import_rookies_from_excel(file_path)
        elif file_extension == ".json":
            return await self.import_rookies_from_json(file_path)
        else:
            return {
                "success_count": 0,
                "error_messages": [
                    f"Unsupported file format: {file_extension}. Must be .csv, .xlsx, or .json"
                ],
            }
