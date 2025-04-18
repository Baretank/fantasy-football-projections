import pandas as pd
import logging
import nfl_data_py as nfl

from backend.services.typing_pandas import TypedDataFrame
from backend.services.typing import safe_float

logger = logging.getLogger(__name__)


class NFLDataPyAdapter:
    """
    Adapter for the nfl-data-py package to retrieve NFL statistics.

    This adapter provides methods to fetch player data, weekly stats,
    and team stats from the nfl-data-py package.
    """

    async def get_players(self, season: int) -> TypedDataFrame:
        """
        Get player data for the specified season.

        Args:
            season: The NFL season year (e.g., 2023) - used for logging only

        Returns:
            TypedDataFrame containing player information (filtered to fantasy-relevant positions)
        """
        logger.info(f"Fetching player data (focusing on season {season}) from nfl-data-py")
        try:
            # Import player data - nfl_data_py import_players() doesn't accept a season parameter
            player_data = nfl.import_players()

            # Filter to only fantasy-relevant positions (QB, RB, WR, TE)
            fantasy_positions = ["QB", "RB", "WR", "TE"]
            original_count = len(player_data)
            player_data = player_data[player_data["position"].isin(fantasy_positions)]
            logger.info(
                f"Filtered from {original_count} to {len(player_data)} players with fantasy-relevant positions"
            )

            # We'll return all player data and filter by season in the service layer if needed
            # This will allow us to focus on 2024 players when we process the data
            logger.info(f"Retrieved {len(player_data)} fantasy-relevant players total")
            return TypedDataFrame(player_data)
        except Exception as e:
            logger.error(f"Error fetching player data: {str(e)}")
            raise

    async def get_weekly_stats(self, season: int) -> TypedDataFrame:
        """
        Get weekly statistics for the specified season.

        Args:
            season: The NFL season year (e.g., 2023)

        Returns:
            TypedDataFrame containing weekly player statistics
        """
        logger.info(f"Fetching weekly stats for season {season} from nfl-data-py")
        try:
            # Import weekly data
            weekly_data = nfl.import_weekly_data([season])
            logger.info(f"Retrieved {len(weekly_data)} weekly stat entries for season {season}")
            return TypedDataFrame(weekly_data)
        except Exception as e:
            logger.error(f"Error fetching weekly stats: {str(e)}")
            raise

    async def get_team_stats(self, season: int) -> TypedDataFrame:
        """
        Get team statistics for the specified season.

        Args:
            season: The NFL season year (e.g., 2023)

        Returns:
            TypedDataFrame containing team metadata and detailed team stats
        """
        logger.info(f"Fetching team stats for season {season} from nfl-data-py")
        try:
            # Import team descriptions for metadata
            team_desc = nfl.import_team_desc()
            logger.info(f"Retrieved information for {len(team_desc)} teams")

            # Use multiple sources to get the most complete team stats
            sources = []

            # Source 1: Try to get official seasonal data first
            logger.info(f"Attempting to get seasonal_data for {season}")
            seasonal_data = nfl.import_seasonal_data([season])
            if seasonal_data is not None and len(seasonal_data) > 0:
                # Filter to team-level data if possible
                team_data = (
                    seasonal_data[seasonal_data["player_id"].isna()]
                    if "player_id" in seasonal_data.columns
                    else seasonal_data
                )
                if len(team_data) > 0:
                    logger.info(
                        f"Successfully retrieved team seasonal_data with {len(team_data)} entries"
                    )
                    # Rename 'team' column to standardize
                    if "team" not in team_data.columns and "team_abbr" in team_data.columns:
                        team_data = team_data.rename(columns={"team_abbr": "team"})
                    sources.append(("seasonal_data", team_data))
                else:
                    logger.warning(f"No team-level data found in seasonal_data for {season}")
            else:
                logger.warning(f"No data from seasonal_data for {season}")

            # Source 2: Try to get PFR (Pro Football Reference) seasonal stats
            logger.info(f"Attempting to get seasonal_pfr data for {season}")
            try:
                pfr_stats = nfl.import_seasonal_pfr([season])
                if pfr_stats is not None and len(pfr_stats) > 0:
                    # Filter to team-level data if possible
                    pfr_team_stats = (
                        pfr_stats[pfr_stats["player_id"].isna()]
                        if "player_id" in pfr_stats.columns
                        else pfr_stats
                    )
                    if len(pfr_team_stats) > 0:
                        logger.info(
                            f"Successfully retrieved team data from seasonal_pfr with {len(pfr_team_stats)} entries"
                        )
                        # Rename 'team' column to standardize
                        if (
                            "team" not in pfr_team_stats.columns
                            and "team_abbr" in pfr_team_stats.columns
                        ):
                            pfr_team_stats = pfr_team_stats.rename(columns={"team_abbr": "team"})
                        sources.append(("seasonal_pfr", pfr_team_stats))
                    else:
                        logger.warning(f"No team-level data found in seasonal_pfr for {season}")
                else:
                    logger.warning(f"No data from seasonal_pfr for {season}")
            except Exception as e:
                logger.warning(f"Error retrieving seasonal_pfr data: {str(e)}")

            # Source 3: Aggregate from weekly player data as fallback
            logger.info(f"Attempting to aggregate stats from weekly data for {season}")
            weekly_data = nfl.import_weekly_data([season])
            if weekly_data is not None and len(weekly_data) > 0:
                # Log column names to debug
                logger.info(f"Weekly data columns: {weekly_data.columns.tolist()}")

                # Check which columns are available before aggregating
                agg_dict = {}
                stat_mappings = {
                    "passing_yards": ["passing_yards", "pass_yards"],
                    "passing_tds": ["passing_tds", "pass_tds", "pass_td"],
                    "passing_att": [
                        "attempts",
                        "passing_att",
                        "pass_att",
                    ],  # Updated order - attempts is the correct name in the data
                    "rushing_yards": ["rushing_yards", "rush_yards"],
                    "rushing_tds": ["rushing_tds", "rush_tds", "rush_td"],
                    "rushing_att": [
                        "carries",
                        "rushing_att",
                        "rush_att",
                    ],  # Updated order - carries is the correct name in the data
                    "receptions": ["receptions", "rec"],
                    "targets": ["targets"],
                    "receiving_yards": ["receiving_yards", "rec_yards"],
                    "receiving_tds": ["receiving_tds", "rec_tds", "rec_td"],
                }

                # Find which columns actually exist
                for our_key, possible_cols in stat_mappings.items():
                    for col in possible_cols:
                        if col in weekly_data.columns:
                            agg_dict[col] = "sum"
                            logger.debug(f"Using column {col} for {our_key}")
                            break

                if len(agg_dict) == 0:
                    logger.warning("No matching stat columns found in weekly data")
                else:
                    # Group by team and calculate aggregate stats
                    logger.info(
                        f"Aggregating team stats from {len(weekly_data)} weekly player entries using {len(agg_dict)} columns"
                    )
                    try:
                        team_col = "recent_team" if "recent_team" in weekly_data.columns else "team"
                        if team_col not in weekly_data.columns:
                            logger.warning(
                                f"No team column found in weekly data. Available columns: {weekly_data.columns.tolist()}"
                            )
                        else:
                            aggregated_stats = (
                                weekly_data.groupby(team_col).agg(agg_dict).reset_index()
                            )
                            # Rename to standardize column names
                            aggregated_stats = aggregated_stats.rename(columns={team_col: "team"})
                            sources.append(("weekly_aggregated", aggregated_stats))
                    except Exception as e:
                        logger.warning(f"Error aggregating weekly data: {str(e)}")
            else:
                logger.warning(f"No weekly data available for {season}")

            # Process the data and match our required format
            teams_data = []

            # For each team in our team descriptions
            for _, team in team_desc.iterrows():
                team_abbr = team["team_abbr"]

                # Find this team's data from our sources, prioritizing the most reliable sources
                team_row = None
                source_name = None

                for source_name, source_df in sources:
                    if source_df is not None and len(source_df) > 0:
                        team_matches = source_df[source_df["team"] == team_abbr]
                        if len(team_matches) > 0:
                            team_row = team_matches.iloc[0]
                            logger.debug(f"Found data for {team_abbr} in {source_name}")
                            break

                # Create the team data entry - using real data if available, calculated values if possible
                if team_row is not None:
                    # Get actual values with smart fallbacks based on the source
                    if source_name == "seasonal_data":
                        # These field names match import_seasonal_data
                        # Try different field name variations since the API might change
                        seasonal_pass_att_fields = ["attempts", "pass_att", "passing_att", "team_pass_att"]
                        seasonal_pass_att: float = 550.0  # Default value as float
                        for field in seasonal_pass_att_fields:
                            if field in team_row and pd.notna(team_row.get(field, None)):
                                seasonal_pass_att = float(team_row.get(field))
                                logger.info(
                                    f"Found passing attempts in field '{field}': {seasonal_pass_att}"
                                )
                                break

                        seasonal_rush_att_fields = [
                            "carries",
                            "rush_att",
                            "rushes",
                            "rush_attempts",
                            "team_rush_att",
                        ]
                        seasonal_rush_att: float = 450.0  # Default value as float
                        for field in seasonal_rush_att_fields:
                            if field in team_row and pd.notna(team_row.get(field, None)):
                                seasonal_rush_att = float(team_row.get(field))
                                logger.info(
                                    f"Found rushing attempts in field '{field}': {seasonal_rush_att}"
                                )
                                break

                        seasonal_pass_yards_fields = ["pass_yards", "passing_yards", "team_pass_yards"]
                        seasonal_pass_yards: float = 4000.0  # Default value as float
                        for field in seasonal_pass_yards_fields:
                            if field in team_row and pd.notna(team_row.get(field, None)):
                                seasonal_pass_yards = float(team_row.get(field))
                                break

                        seasonal_pass_td_fields = ["pass_td", "passing_tds", "team_pass_td"]
                        seasonal_pass_td: float = 25.0  # Default value as float
                        for field in seasonal_pass_td_fields:
                            if field in team_row and pd.notna(team_row.get(field, None)):
                                seasonal_pass_td = float(team_row.get(field))
                                break

                        seasonal_rush_yards_fields = ["rush_yards", "rushing_yards", "team_rush_yards"]
                        seasonal_rush_yards: float = 1800.0  # Default value as float
                        for field in seasonal_rush_yards_fields:
                            if field in team_row and pd.notna(team_row.get(field, None)):
                                seasonal_rush_yards = float(team_row.get(field))
                                break

                        seasonal_rush_td_fields = ["rush_td", "rushing_tds", "team_rush_td"]
                        seasonal_rush_td: float = 15.0  # Default value as float
                        for field in seasonal_rush_td_fields:
                            if field in team_row and pd.notna(team_row.get(field, None)):
                                seasonal_rush_td = float(team_row.get(field))
                                break

                        seasonal_plays_fields = ["plays", "total_plays"]
                        seasonal_plays: float = seasonal_pass_att + seasonal_rush_att  # Default to sum of attempts
                        for field in seasonal_plays_fields:
                            if field in team_row and pd.notna(team_row.get(field, None)):
                                seasonal_plays = float(team_row.get(field))
                                break

                    elif source_name == "seasonal_pfr":
                        # Pro Football Reference data might have different field names
                        pfr_pass_att_fields = ["attempts", "pass_att", "passing_att", "team_pass_att"]
                        pfr_pass_att: float = 550.0  # Default value as float
                        for field in pfr_pass_att_fields:
                            if field in team_row and pd.notna(team_row.get(field, None)):
                                pfr_pass_att = float(team_row.get(field))
                                logger.info(
                                    f"Found passing attempts in PFR data in field '{field}': {pfr_pass_att}"
                                )
                                break

                        pfr_rush_att_fields = [
                            "carries",
                            "rush_att",
                            "rushes",
                            "rush_attempts",
                            "team_rush_att",
                        ]
                        pfr_rush_att: float = 450.0  # Default value as float
                        for field in pfr_rush_att_fields:
                            if field in team_row and pd.notna(team_row.get(field, None)):
                                pfr_rush_att = float(team_row.get(field))
                                logger.info(
                                    f"Found rushing attempts in PFR data in field '{field}': {pfr_rush_att}"
                                )
                                break

                        pfr_pass_yards_fields = [
                            "pass_yds",
                            "pass_yards",
                            "passing_yards",
                            "team_pass_yards",
                        ]
                        pfr_pass_yards: float = 4000.0  # Default value as float
                        for field in pfr_pass_yards_fields:
                            if field in team_row and pd.notna(team_row.get(field, None)):
                                pfr_pass_yards = float(team_row.get(field))
                                break

                        pfr_pass_td_fields = ["pass_td", "pass_tds", "passing_tds", "team_pass_td"]
                        pfr_pass_td: float = 25.0  # Default value as float
                        for field in pfr_pass_td_fields:
                            if field in team_row and pd.notna(team_row.get(field, None)):
                                pfr_pass_td = float(team_row.get(field))
                                break

                        pfr_rush_yards_fields = [
                            "rush_yds",
                            "rush_yards",
                            "rushing_yards",
                            "team_rush_yards",
                        ]
                        pfr_rush_yards: float = 1800.0  # Default value as float
                        for field in pfr_rush_yards_fields:
                            if field in team_row and pd.notna(team_row.get(field, None)):
                                pfr_rush_yards = float(team_row.get(field))
                                break

                        pfr_rush_td_fields = ["rush_td", "rush_tds", "rushing_tds", "team_rush_td"]
                        pfr_rush_td: float = 15.0  # Default value as float
                        for field in pfr_rush_td_fields:
                            if field in team_row and pd.notna(team_row.get(field, None)):
                                pfr_rush_td = float(team_row.get(field))
                                break

                        pfr_plays = pfr_pass_att + pfr_rush_att  # Default to sum of attempts
                        if "total_plays" in team_row and pd.notna(team_row.get("total_plays")):
                            pfr_plays = float(team_row.get("total_plays"))
                    else:
                        # These field names match the weekly aggregated data
                        # Try to get passing attempts first from the available columns
                        weekly_pass_att: float = 550.0  # Default value as float
                        if "attempts" in team_row and pd.notna(team_row.get("attempts")):
                            weekly_pass_att = float(team_row.get("attempts"))
                            logger.info(
                                f"Found passing attempts in weekly data from 'attempts': {weekly_pass_att}"
                            )
                        elif "passing_att" in team_row and pd.notna(team_row.get("passing_att")):
                            weekly_pass_att = float(team_row.get("passing_att"))
                            logger.info(
                                f"Found passing attempts in weekly data from 'passing_att': {weekly_pass_att}"
                            )
                        else:
                            logger.warning(f"Using default value for passing attempts: {weekly_pass_att}")

                        # Try to get rushing attempts from the available columns
                        weekly_rush_att: float = 450.0  # Default value as float
                        if "carries" in team_row and pd.notna(team_row.get("carries")):
                            weekly_rush_att = float(team_row.get("carries"))
                            logger.info(
                                f"Found rushing attempts in weekly data from 'carries': {weekly_rush_att}"
                            )
                        elif "rushing_att" in team_row and pd.notna(team_row.get("rushing_att")):
                            weekly_rush_att = float(team_row.get("rushing_att"))
                            logger.info(
                                f"Found rushing attempts in weekly data from 'rushing_att': {weekly_rush_att}"
                            )
                        else:
                            logger.warning(f"Using default value for rushing attempts: {weekly_rush_att}")

                        weekly_pass_yards: float = (
                            float(team_row.get("passing_yards", 0))
                            if pd.notna(team_row.get("passing_yards", 0))
                            else 4000.0
                        )
                        weekly_pass_td: float = (
                            float(team_row.get("passing_tds", 0))
                            if pd.notna(team_row.get("passing_tds", 0))
                            else 25.0
                        )
                        weekly_rush_yards: float = (
                            float(team_row.get("rushing_yards", 0))
                            if pd.notna(team_row.get("rushing_yards", 0))
                            else 1800.0
                        )
                        weekly_rush_td: float = (
                            float(team_row.get("rushing_tds", 0))
                            if pd.notna(team_row.get("rushing_tds", 0))
                            else 15.0
                        )
                        weekly_plays: float = weekly_pass_att + weekly_rush_att

                    # Choose the right variables based on the source
                    if source_name == "seasonal_data":
                        pass_att_value = seasonal_pass_att
                        rush_att_value = seasonal_rush_att
                        plays_value = seasonal_plays
                        pass_yards_value = seasonal_pass_yards
                        pass_td_value = seasonal_pass_td
                        rush_yards_value = seasonal_rush_yards
                        rush_td_value = seasonal_rush_td
                    elif source_name == "seasonal_pfr":
                        pass_att_value = pfr_pass_att
                        rush_att_value = pfr_rush_att
                        plays_value = pfr_plays
                        pass_yards_value = pfr_pass_yards
                        pass_td_value = pfr_pass_td
                        rush_yards_value = pfr_rush_yards
                        rush_td_value = pfr_rush_td
                    else:  # weekly_aggregated
                        pass_att_value = weekly_pass_att
                        rush_att_value = weekly_rush_att
                        plays_value = weekly_plays
                        pass_yards_value = weekly_pass_yards
                        pass_td_value = weekly_pass_td
                        rush_yards_value = weekly_rush_yards
                        rush_td_value = weekly_rush_td

                    # Calculate derived values
                    total_plays = max(plays_value, pass_att_value + rush_att_value)  # Use max to avoid zero
                    pass_percentage = (pass_att_value / total_plays * 100) if total_plays > 0 else 55.0
                    pass_td_rate = (pass_td_value / pass_att_value * 100) if pass_att_value > 0 else 4.5
                    rush_ypc = (rush_yards_value / rush_att_value) if rush_att_value > 0 else 4.0

                    # Get receiving stats - using passing stats as fallbacks for consistency
                    targets = (
                        float(team_row.get("targets", pass_att_value))
                        if pd.notna(team_row.get("targets", pass_att_value))
                        else pass_att_value
                    )
                    receptions = (
                        float(team_row.get("receptions", 0))
                        if pd.notna(team_row.get("receptions", 0))
                        else (pass_att_value * 0.65)
                    )
                    rec_yards = (
                        float(team_row.get("receiving_yards", pass_yards_value))
                        if pd.notna(team_row.get("receiving_yards", pass_yards_value))
                        else pass_yards_value
                    )
                    rec_td = (
                        float(team_row.get("receiving_tds", pass_td_value))
                        if pd.notna(team_row.get("receiving_tds", pass_td_value))
                        else pass_td_value
                    )

                    # Get team rank if available
                    rank_col = next((c for c in team_row.index if "rank" in str(c).lower()), None)
                    rank = (
                        float(team_row.get(rank_col, 16))
                        if rank_col and pd.notna(team_row.get(rank_col))
                        else 16
                    )

                    logger.info(f"Using real data from {source_name} for team {team_abbr}")

                else:
                    # Use placeholder data if no stats found
                    logger.warning(
                        f"Using placeholder data for team {team_abbr} - no stats found in any source"
                    )
                    pass_att_value = 550.0
                    rush_att_value = 450.0
                    total_plays = 1000.0
                    pass_percentage = 55.0
                    pass_yards_value = 4000.0
                    pass_td_value = 25.0
                    pass_td_rate = 4.5
                    rush_yards_value = 1800.0
                    rush_td_value = 15.0
                    rush_ypc = 4.0
                    targets = 550.0
                    receptions = 350.0
                    rec_yards = 4000.0
                    rec_td = 25.0
                    rank = 16.0

                # Create standardized team data dictionary
                team_data = {
                    "team": team_abbr,
                    "season": season,
                    "plays": total_plays,
                    "pass_percentage": pass_percentage,
                    "pass_attempts": pass_att_value,
                    "pass_yards": pass_yards_value,
                    "pass_td": pass_td_value,
                    "pass_td_rate": pass_td_rate,
                    "rush_attempts": rush_att_value,
                    "rush_yards": rush_yards_value,
                    "rush_td": rush_td_value,
                    "rush_yards_per_carry": rush_ypc,
                    "targets": targets,
                    "receptions": receptions,
                    "rec_yards": rec_yards,
                    "rec_td": rec_td,
                    "rank": rank,
                }

                teams_data.append(team_data)

            # Convert to DataFrame
            team_data_df = pd.DataFrame(teams_data)

            # Log data quality stats
            real_data_count = len([t for t in teams_data if t["plays"] != 1000])  # Non-placeholder
            logger.info(
                f"Created team stats with {real_data_count} teams using real data, "
                + f"{len(teams_data) - real_data_count} teams using placeholder data"
            )

            # Verify data consistency using safe calculation patterns
            for t in teams_data:
                # Avoid division by zero with safe calculation
                if safe_float(t["plays"], 0) > 0:
                    calc_pass_pct = safe_float(t["pass_attempts"], 0) / safe_float(t["plays"], 1) * 100
                    if abs(safe_float(t["pass_percentage"], 0) - calc_pass_pct) > 1.0:
                        logger.warning(
                            f"Pass percentage inconsistency for {t['team']}: "
                            + f"{t['pass_percentage']} vs calculated {calc_pass_pct}"
                        )

                if safe_float(t["pass_attempts"], 0) > 0:
                    calc_td_rate = safe_float(t["pass_td"], 0) / safe_float(t["pass_attempts"], 1) * 100
                    if abs(safe_float(t["pass_td_rate"], 0) - calc_td_rate) > 1.0:
                        logger.warning(
                            f"Pass TD rate inconsistency for {t['team']}: "
                            + f"{t['pass_td_rate']} vs calculated {calc_td_rate}"
                        )

                if safe_float(t["rush_attempts"], 0) > 0:
                    calc_ypc = safe_float(t["rush_yards"], 0) / safe_float(t["rush_attempts"], 1)
                    if abs(safe_float(t["rush_yards_per_carry"], 0) - calc_ypc) > 0.5:
                        logger.warning(
                            f"Rush YPC inconsistency for {t['team']}: "
                            + f"{t['rush_yards_per_carry']} vs calculated {calc_ypc}"
                        )

            return TypedDataFrame(team_data_df)

        except Exception as e:
            logger.error(f"Error fetching team stats: {str(e)}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    async def get_schedules(self, season: int) -> TypedDataFrame:
        """
        Get NFL game schedules for the specified season.

        Args:
            season: The NFL season year (e.g., 2023)

        Returns:
            TypedDataFrame containing game schedule information
        """
        logger.info(f"Fetching game schedules for season {season} from nfl-data-py")
        try:
            # Import schedules
            schedule_data = nfl.import_schedules([season])
            logger.info(f"Retrieved {len(schedule_data)} schedule entries for season {season}")
            return TypedDataFrame(schedule_data)
        except Exception as e:
            logger.error(f"Error fetching schedules: {str(e)}")
            raise

    async def get_rosters(self, season: int) -> TypedDataFrame:
        """
        Get team rosters for the specified season.

        Args:
            season: The NFL season year (e.g., 2023)

        Returns:
            TypedDataFrame containing roster information
        """
        logger.info(f"Fetching team rosters for season {season} from nfl-data-py")
        try:
            # Import rosters
            roster_data = nfl.import_rosters([season])
            logger.info(f"Retrieved {len(roster_data)} roster entries for season {season}")
            return TypedDataFrame(roster_data)
        except Exception as e:
            logger.error(f"Error fetching rosters: {str(e)}")
            raise

    async def get_player_weekly_stats(self, player_id: str, season: int) -> TypedDataFrame:
        """
        Get weekly statistics for a specific player.

        Args:
            player_id: The player ID to get stats for
            season: The NFL season year (e.g., 2023)

        Returns:
            TypedDataFrame containing player's weekly statistics
        """
        logger.info(f"Fetching weekly stats for player {player_id} in season {season}")
        try:
            # Get all weekly data for the season
            weekly_data = await self.get_weekly_stats(season)

            # Filter for the specific player
            player_data_df = weekly_data.df[weekly_data.df["player_id"] == player_id].copy()

            logger.info(f"Found {len(player_data_df)} weekly stat entries for player {player_id}")
            return TypedDataFrame(player_data_df)
        except Exception as e:
            logger.error(f"Error fetching player weekly stats: {str(e)}")
            raise
