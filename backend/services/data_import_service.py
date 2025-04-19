from typing import Dict
from sqlalchemy.orm import Session
import pandas as pd
import logging
import uuid
from datetime import datetime

from backend.database.models import Player, BaseStat, GameStats, ImportLog
from backend.services.adapters.web_data_adapter import WebDataAdapter
from backend.services.active_player_service import ActivePlayerService
from backend.services.typing import ImportMetricsDict, DataImportResultDict, safe_float, safe_dict_get
from backend.services.typing_pandas import TypedDataFrame, safe_series_get, series_to_float, series_to_int, series_to_str

logger = logging.getLogger(__name__)


class DataImportService:
    """
    Service for importing player data from external sources.

    This service coordinates data import from web sources,
    processes the data, and stores it in the database.
    """

    def __init__(self, db: Session, logger=None, active_player_service=None):
        """
        Initialize the data import service.

        Args:
            db: SQLAlchemy database session
            logger: Optional logger instance
            active_player_service: Optional ActivePlayerService instance
        """
        self.db = db
        self.logger = logger or logging.getLogger(__name__)
        self.web_data_adapter = WebDataAdapter()
        self.active_player_service = active_player_service or ActivePlayerService()

        # Metrics tracking
        self.metrics: ImportMetricsDict = {
            "requests_made": 0,
            "errors": 0,
            "players_processed": 0,
            "game_stats_processed": 0,
            "players_filtered": 0,
            "start_time": None,
            "end_time": None,
        }

        # Position-specific stat mappings
        self.stat_mappings = {
            "QB": {
                "pass_attempts": "att",
                "completions": "cmp",
                "pass_yards": "pass_yds",
                "pass_td": "pass_td",
                "interceptions": "int",
                "rush_attempts": "rush_att",
                "rush_yards": "rush_yds",
                "rush_td": "rush_td",
            },
            "RB": {
                "rush_attempts": "att",
                "rush_yards": "yds",
                "rush_td": "td",
                "targets": "tgt",
                "receptions": "rec",
                "rec_yards": "rec_yds",
                "rec_td": "rec_td",
            },
            "WR": {
                "targets": "tgt",
                "receptions": "rec",
                "rec_yards": "yds",
                "rec_td": "td",
                "rush_attempts": "rush_att",
                "rush_yards": "rush_yds",
                "rush_td": "rush_td",
            },
            "TE": {"targets": "tgt", "receptions": "rec", "rec_yards": "yds", "rec_td": "td"},
        }

    def start_monitoring(self):
        """Start the monitoring session."""
        self.metrics["start_time"] = datetime.now()
        self.logger.info(f"Started import operation at {self.metrics['start_time']}")

    def end_monitoring(self) -> DataImportResultDict:
        """End the monitoring session and report metrics."""
        self.metrics["end_time"] = datetime.now()
        duration = (self.metrics["end_time"] - self.metrics["start_time"]).total_seconds()

        self.logger.info(f"Import operation completed in {duration:.2f} seconds")
        self.logger.info(f"Metrics: {self.metrics}")

        # Log detailed stats
        if self.metrics["requests_made"] > 0:
            error_rate = self.metrics["errors"] / self.metrics["requests_made"] * 100
            self.logger.info(f"Error rate: {error_rate:.2f}%")

        return {"duration_seconds": duration, "metrics": self.metrics}

    async def _fetch_game_log_data(self, player_id: str, season: int) -> TypedDataFrame:
        """
        Fetch game log data for a player.
        This method is mocked in tests.

        Args:
            player_id: The player's unique identifier
            season: The NFL season year

        Returns:
            TypedDataFrame containing game log data
        """
        # In a real implementation, this would call the web data adapter
        # For testing purposes, this is mocked to return test data
        self.metrics["requests_made"] += 1
        return TypedDataFrame(pd.DataFrame())

    async def _fetch_season_totals(self, player_id: str, season: int) -> TypedDataFrame:
        """
        Fetch season totals for a player.
        This method is mocked in tests.

        Args:
            player_id: The player's unique identifier
            season: The NFL season year

        Returns:
            TypedDataFrame containing season total statistics
        """
        # In a real implementation, this would call the web data adapter
        # For testing purposes, this is mocked to return test data
        self.metrics["requests_made"] += 1
        return TypedDataFrame(pd.DataFrame())

    async def _import_player_data(self, player_id: str, season: int) -> bool:
        """
        Import data for a specific player.

        Args:
            player_id: The player ID to import data for
            season: The season year

        Returns:
            Boolean indicating success or failure
        """
        try:
            # Check if player exists
            player = self.db.query(Player).filter(Player.player_id == player_id).first()
            if not player:
                self.logger.error(f"Player {player_id} not found in database")
                return False

            # Log the operation
            self.logger.info(
                f"Importing data for player {player.name} (ID: {player_id}) for season {season}"
            )

            # Get game log data for this player
            game_log = await self._fetch_game_log_data(player_id, season)
            if game_log is None or game_log.is_empty():
                self.logger.warning(f"No game log found for player {player.name}")
                return False

            # Process game stats
            games_processed = 0
            for idx in range(game_log.row_count()):
                # Create pandas Series from row for safer access
                row = game_log.df.iloc[idx]
                # Skip if week is missing
                if pd.isna(safe_series_get(row, "Week")):
                    continue

                week = series_to_int(row, "Week")

                # Check if weekly stat already exists
                existing_stat = (
                    self.db.query(GameStats)
                    .filter(
                        GameStats.player_id == player_id,
                        GameStats.season == season,
                        GameStats.week == week,
                    )
                    .first()
                )

                if existing_stat:
                    continue  # Skip if already imported

                # Get position-specific stats
                position = player.position
                stats = {}

                # Import stats based on position mappings
                for our_name, external_name in self.stat_mappings.get(position, {}).items():
                    stats[our_name] = series_to_float(row, external_name, 0.0)
                    if not pd.isna(safe_series_get(row, external_name)):
                        self.logger.debug(
                            f"Imported {external_name} -> {our_name}: {series_to_float(row, external_name)}"
                        )

                # Get game context data (opponent, result, etc.)
                opponent = series_to_str(row, "Opp", "UNK")
                result = series_to_str(row, "Result", "U")

                # Create new game stat
                game_stat = GameStats(
                    game_stat_id=str(uuid.uuid4()),
                    player_id=player_id,
                    season=season,
                    week=week,
                    opponent=opponent,
                    game_location="home" if "@" not in str(opponent) else "away",
                    result=result,
                    team_score=0,  # Would parse from result in real implementation
                    opponent_score=0,
                    stats=stats,
                )

                self.db.add(game_stat)
                games_processed += 1
                self.metrics["game_stats_processed"] += 1

            # Commit all new game stats
            self.db.commit()

            # Fetch season totals
            season_totals = await self._fetch_season_totals(player_id, season)
            if season_totals is None or season_totals.is_empty():
                self.logger.warning(f"No season totals found for player {player.name}")

            # Calculate season totals from game stats
            games_played = games_processed
            position = player.position

            # Initialize totals dictionary
            totals = {}

            # Get all game stats
            game_stats = (
                self.db.query(GameStats)
                .filter(GameStats.player_id == player_id, GameStats.season == season)
                .all()
            )

            # Aggregate stats based on position
            if position == "QB":
                totals = {
                    "pass_attempts": sum(g.stats.get("pass_attempts", 0) for g in game_stats),
                    "completions": sum(g.stats.get("completions", 0) for g in game_stats),
                    "pass_yards": sum(g.stats.get("pass_yards", 0) for g in game_stats),
                    "pass_td": sum(g.stats.get("pass_td", 0) for g in game_stats),
                    "interceptions": sum(g.stats.get("interceptions", 0) for g in game_stats),
                    "rush_attempts": sum(g.stats.get("rush_attempts", 0) for g in game_stats),
                    "rush_yards": sum(g.stats.get("rush_yards", 0) for g in game_stats),
                    "rush_td": sum(g.stats.get("rush_td", 0) for g in game_stats),
                }
            elif position == "RB":
                totals = {
                    "rush_attempts": sum(g.stats.get("rush_attempts", 0) for g in game_stats),
                    "rush_yards": sum(g.stats.get("rush_yards", 0) for g in game_stats),
                    "rush_td": sum(g.stats.get("rush_td", 0) for g in game_stats),
                    "targets": sum(g.stats.get("targets", 0) for g in game_stats),
                    "receptions": sum(g.stats.get("receptions", 0) for g in game_stats),
                    "rec_yards": sum(g.stats.get("rec_yards", 0) for g in game_stats),
                    "rec_td": sum(g.stats.get("rec_td", 0) for g in game_stats),
                }
            else:  # WR and TE
                totals = {
                    "targets": sum(g.stats.get("targets", 0) for g in game_stats),
                    "receptions": sum(g.stats.get("receptions", 0) for g in game_stats),
                    "rec_yards": sum(g.stats.get("rec_yards", 0) for g in game_stats),
                    "rec_td": sum(g.stats.get("rec_td", 0) for g in game_stats),
                }

                # Add rushing stats for WRs
                if position == "WR":
                    totals.update(
                        {
                            "rush_attempts": sum(
                                g.stats.get("rush_attempts", 0) for g in game_stats
                            ),
                            "rush_yards": sum(g.stats.get("rush_yards", 0) for g in game_stats),
                            "rush_td": sum(g.stats.get("rush_td", 0) for g in game_stats),
                        }
                    )

            # Calculate half-PPR fantasy points
            fantasy_points = self._calculate_fantasy_points(totals, position)

            # Create or update BaseStat records
            for stat_name, value in totals.items():
                self._create_or_update_base_stat(player_id, season, stat_name, value)

            # Add games and half_ppr
            self._create_or_update_base_stat(player_id, season, "games", games_played)
            self._create_or_update_base_stat(player_id, season, "half_ppr", fantasy_points)

            # Commit changes
            self.db.commit()

            # Log success
            self._log_import(
                "player_data_import",
                "success",
                f"Successfully imported data for player {player.name} (ID: {player_id})",
                {"season": season, "games": games_played},
            )

            return True

        except Exception as e:
            self.db.rollback()
            self.metrics["errors"] += 1
            self.logger.error(f"Error importing player data for {player_id}: {str(e)}")
            self._log_import(
                "player_data_import",
                "error",
                f"Error importing player data for {player_id}: {str(e)}",
            )
            return False

    def _create_or_update_base_stat(
        self, player_id: str, season: int, stat_type: str, value: float
    ) -> None:
        """Create or update a base stat for a player."""
        # Check if the stat already exists
        existing_stat = (
            self.db.query(BaseStat)
            .filter(
                BaseStat.player_id == player_id,
                BaseStat.season == season,
                BaseStat.stat_type == stat_type,
            )
            .first()
        )

        if existing_stat:
            # Update existing stat
            existing_stat.value = value
        else:
            # Create new stat
            new_stat = BaseStat(
                stat_id=str(uuid.uuid4()),
                player_id=player_id,
                season=season,
                stat_type=stat_type,
                value=value,
            )
            self.db.add(new_stat)

    def _calculate_fantasy_points(self, stats: Dict[str, float], position: str) -> float:
        """
        Calculate half-PPR fantasy points from stats.

        Args:
            stats: Dictionary of player statistics
            position: Player position

        Returns:
            Fantasy points in half-PPR scoring
        """
        points = 0.0

        # Passing points
        points += safe_float(safe_dict_get(stats, "pass_yards", 0)) * 0.04  # 1 point per 25 yards
        points += safe_float(safe_dict_get(stats, "pass_td", 0)) * 4  # 4 points per passing TD
        points -= safe_float(safe_dict_get(stats, "interceptions", 0)) * 1  # -1 point per interception

        # Rushing points
        points += safe_float(safe_dict_get(stats, "rush_yards", 0)) * 0.1  # 1 point per 10 yards
        points += safe_float(safe_dict_get(stats, "rush_td", 0)) * 6  # 6 points per rushing TD

        # Receiving points
        points += safe_float(safe_dict_get(stats, "rec_yards", 0)) * 0.1  # 1 point per 10 yards
        points += safe_float(safe_dict_get(stats, "rec_td", 0)) * 6  # 6 points per receiving TD
        points += safe_float(safe_dict_get(stats, "receptions", 0)) * 0.5  # 0.5 points per reception (half-PPR)

        return round(points, 1)

    def filter_active_players(self, players_df: TypedDataFrame) -> TypedDataFrame:
        """
        Filter a DataFrame of players to include only active players.
        
        Args:
            players_df: TypedDataFrame containing player information

        Returns:
            TypedDataFrame with only active players
        """
        if players_df is None or players_df.is_empty():
            return players_df
            
        try:
            # Convert TypedDataFrame to standard DataFrame for filtering
            df = players_df.df
            
            # Skip filtering if key columns missing
            if 'display_name' not in df.columns or 'team_abbr' not in df.columns:
                self.logger.warning("Cannot filter active players: required columns missing")
                return players_df
                
            # Apply active player filtering
            original_count = len(df)
            filtered_df = self.active_player_service.filter_active(df)
            filtered_count = len(filtered_df)
            
            # Update metrics and log results
            players_filtered = original_count - filtered_count
            self.metrics["players_filtered"] += players_filtered
            
            self.logger.info(
                f"Active player filtering: {filtered_count}/{original_count} "
                f"players retained ({players_filtered} filtered out)"
            )
            
            # Return new TypedDataFrame with filtered data
            return TypedDataFrame(filtered_df)
            
        except Exception as e:
            self.logger.error(f"Error filtering active players: {str(e)}")
            # Return original data on error
            return players_df

    def _log_import(self, operation: str, status: str, message: str, details: Dict = None) -> None:
        """
        Log an import operation to the database.

        Args:
            operation: Type of operation
            status: success, warning, or error
            message: Log message
            details: Optional details dictionary
        """
        try:
            log_entry = ImportLog(
                log_id=str(uuid.uuid4()),
                operation=operation,
                status=status,
                message=message,
                details=details,
            )
            self.db.add(log_entry)
            self.db.commit()
        except Exception as e:
            self.logger.error(f"Error logging import operation: {str(e)}")
            # Don't raise - this is a non-critical operation
