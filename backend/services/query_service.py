from typing import Dict, List, Optional, Any, Tuple, Union, cast
from sqlalchemy.orm import Session, joinedload, contains_eager
from sqlalchemy import and_, or_, desc, func, text
import logging
from datetime import datetime
import asyncio
import pandas as pd

from backend.database.models import Player, Projection, BaseStat, GameStats, Scenario
from backend.services.cache_service import get_cache
from backend.services.active_player_service import ActivePlayerService
from backend.services.typing import (
    safe_float, safe_dict_get, 
    PlayerQueryResultDict, QueryResultDict, PlayerProjectionDataDict
)

logger = logging.getLogger(__name__)


class QueryService:
    """Service for optimized database queries and player listings."""

    def __init__(self, db: Session, active_player_service=None):
        self.db = db
        self.cache = get_cache()
        self.active_player_service = active_player_service or ActivePlayerService()

    async def get_players_optimized(
        self,
        filters: Optional[Dict[str, Any]] = None,
        include_projections: bool = False,
        include_stats: bool = False,
        page: int = 1,
        page_size: int = 50,
        sort_by: str = "name",
        sort_dir: str = "asc",
        active_only: bool = True,
    ) -> Tuple[List[PlayerQueryResultDict], int]:
        """
        Get players with optimized query performance.

        Args:
            filters: Optional filters to apply
            include_projections: Whether to include projection data
            include_stats: Whether to include statistical data
            page: Page number (1-based)
            page_size: Number of results per page
            sort_by: Field to sort by
            sort_dir: Sort direction (asc or desc)

        Returns:
            Tuple of (players_list, total_count)
        """
        # Build cache key
        cache_key = self.cache.cache_key(
            "player_listing",
            filters=filters,
            include_projections=include_projections,
            include_stats=include_stats,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
            active_only=active_only,
        )

        # Check cache
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        # Start building query
        query = self.db.query(Player)

        # Apply joins based on what's needed
        if include_projections:
            query = query.outerjoin(
                Projection,
                and_(
                    Projection.player_id == Player.player_id,
                    Projection.scenario_id == None,  # Only include base projections
                ),
            ).options(contains_eager(Player.projections))

        if include_stats:
            # Join the most recent season's base stats
            subquery = (
                self.db.query(BaseStat.player_id, func.max(BaseStat.season).label("latest_season"))
                .group_by(BaseStat.player_id)
                .subquery()
            )

            query = query.outerjoin(
                BaseStat,
                and_(
                    BaseStat.player_id == Player.player_id,
                    BaseStat.season == subquery.c.latest_season,
                    BaseStat.week == None,  # Only season totals
                ),
            ).options(contains_eager(Player.base_stats))

        # Apply filters
        if filters:
            if "name" in filters:
                query = query.filter(Player.name.ilike(f"%{filters['name']}%"))
            if "team" in filters:
                query = query.filter(Player.team == filters["team"])
            if "position" in filters:
                if isinstance(filters["position"], list):
                    query = query.filter(Player.position.in_(filters["position"]))
                else:
                    query = query.filter(Player.position == filters["position"])
            if "min_fantasy_points" in filters and include_projections:
                query = query.filter(Projection.half_ppr >= filters["min_fantasy_points"])
            if "status" in filters:
                query = query.filter(Player.status == filters["status"])
            if "exclude_no_team" in filters and filters["exclude_no_team"]:
                query = query.filter(Player.team.isnot(None), Player.team != "", Player.team != "FA")

        # Add sorting
        if sort_by in ["name", "team", "position"]:
            sort_column = getattr(Player, sort_by)
        elif sort_by == "fantasy_points" and include_projections:
            sort_column = Projection.half_ppr
        else:
            sort_column = Player.name  # Default sort

        if sort_dir.lower() == "desc":
            sort_column = desc(sort_column)

        query = query.order_by(sort_column)

        # Get total count (before pagination)
        total_count = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Execute query
        players = query.all()
        
        # Apply active player filtering if requested
        filtered_players = players
        if active_only and players:
            try:
                # Determine which season to use for filtering
                # This affects filtering behavior (stricter for current season)
                filter_season = None
                
                # Check if filters contain a season parameter, regardless of projections
                if filters and "season" in filters:
                    filter_season = filters["season"]
                    logger.debug(f"Using season {filter_season} for active player filtering")
                
                # Convert players to DataFrame for filtering
                player_df = pd.DataFrame([
                    {
                        "display_name": p.name,
                        "team_abbr": p.team,
                        "position": p.position,
                        "player_id": p.player_id,
                        "status": p.status
                    } 
                    for p in players
                ])
                
                # Add fantasy points for historical filtering if available
                if include_projections:
                    fantasy_points = []
                    for p in players:
                        # Find base projection
                        base_proj = next((proj for proj in p.projections if proj.scenario_id is None), None)
                        
                        if base_proj and hasattr(base_proj, "half_ppr"):
                            fantasy_points.append(safe_float(base_proj.half_ppr, 0.0))
                        else:
                            fantasy_points.append(0.0)
                    
                    # Add to DataFrame
                    player_df["fantasy_points"] = fantasy_points
                
                # Filter active players with season awareness
                if not player_df.empty:
                    filtered_df = self.active_player_service.filter_active(
                        player_df, 
                        season=filter_season
                    )
                    
                    # Log filtering results
                    filtered_count = len(filtered_df) if not filtered_df.empty else 0
                    original_count = len(player_df)
                    logger.info(
                        f"Active player filtering (season: {filter_season}): {filtered_count}/{original_count} "
                        f"players retained ({original_count - filtered_count} filtered out)"
                    )
                    
                    # Filter players list to only include active players
                    if not filtered_df.empty:
                        active_ids = set(filtered_df["player_id"].tolist())
                        filtered_players = [p for p in players if p.player_id in active_ids]
                    else:
                        filtered_players = []
            except Exception as e:
                # Log error but continue with unfiltered players
                logger.error(f"Error filtering active players: {str(e)}")
        
        # Format result
        result: List[PlayerQueryResultDict] = []
        for player in filtered_players:
            player_data: PlayerQueryResultDict = {
                "player_id": player.player_id,
                "name": player.name,
                "team": player.team,
                "position": player.position,
            }

            if include_projections:
                # Find base projection
                base_proj = next((p for p in player.projections if p.scenario_id is None), None)

                if base_proj:
                    projection_data: PlayerProjectionDataDict = {
                        "projection_id": base_proj.projection_id,
                        "half_ppr": safe_float(base_proj.half_ppr),
                        "season": base_proj.season,
                    }

                    # Add position-specific stats
                    if player.position == "QB":
                        projection_data.update({
                            "pass_yards": safe_float(base_proj.pass_yards),
                            "pass_td": safe_float(base_proj.pass_td),
                            "interceptions": safe_float(base_proj.interceptions),
                            "rush_yards": safe_float(base_proj.rush_yards),
                            "rush_td": safe_float(base_proj.rush_td),
                        })
                    elif player.position in ["RB", "WR", "TE"]:
                        projection_data.update({
                            "rush_yards": safe_float(base_proj.rush_yards),
                            "rush_td": safe_float(base_proj.rush_td),
                            "rec_yards": safe_float(base_proj.rec_yards),
                            "rec_td": safe_float(base_proj.rec_td),
                        })
                    
                    player_data["projection"] = projection_data

            if include_stats:
                # Process base stats
                stats_data: Dict[str, Dict[str, float]] = {}
                for stat in player.base_stats:
                    season_str = str(stat.season)
                    if season_str not in stats_data:
                        stats_data[season_str] = {}
                    stats_data[season_str][stat.stat_type] = safe_float(stat.value)

                player_data["stats"] = stats_data

            result.append(player_data)

        # Cache the result
        self.cache.set(cache_key, (result, total_count), 300)  # 5 minute cache

        return result, total_count

    async def search_players(
        self, search_term: str, position: Optional[str] = None, limit: int = 20,
        active_only: bool = True
    ) -> List[PlayerQueryResultDict]:
        """
        Search for players by name with autocomplete functionality.

        Args:
            search_term: Term to search for
            position: Optional position filter
            limit: Maximum number of results

        Returns:
            List of matching players
        """
        # Build cache key
        cache_key = self.cache.cache_key(
            "player_search", search_term=search_term, position=position, limit=limit,
            active_only=active_only
        )

        # Check cache
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        # Build query for partial name matching
        query = self.db.query(Player).filter(Player.name.ilike(f"%{search_term}%"))

        # Apply position filter if provided
        if position:
            if isinstance(position, list):
                query = query.filter(Player.position.in_(position))
            else:
                query = query.filter(Player.position == position)

        # Add ordering and limit
        query = query.order_by(Player.name).limit(limit)

        # Execute query
        players = query.all()
        
        # Apply active player filtering if requested
        filtered_players = players
        if active_only and players:
            try:
                # Convert players to DataFrame for filtering
                player_df = pd.DataFrame([
                    {
                        "display_name": p.name,
                        "team_abbr": p.team,
                        "position": p.position,
                        "player_id": p.player_id,
                        "status": p.status
                    } 
                    for p in players
                ])
                
                # For search, we'll use the default filtering (current season)
                # This errs on the side of including more recent players in search
                
                # Filter active players
                if not player_df.empty:
                    filtered_df = self.active_player_service.filter_active(player_df)
                    
                    # Log filtering results
                    filtered_count = len(filtered_df) if not filtered_df.empty else 0
                    original_count = len(player_df)
                    logger.debug(
                        f"Search active player filtering: {filtered_count}/{original_count} "
                        f"players retained ({original_count - filtered_count} filtered out)"
                    )
                    
                    # Filter players list to only include active players
                    if not filtered_df.empty:
                        active_ids = set(filtered_df["player_id"].tolist())
                        filtered_players = [p for p in players if p.player_id in active_ids]
                    else:
                        filtered_players = []
            except Exception as e:
                # Log error but continue with unfiltered players
                logger.error(f"Error filtering active players in search: {str(e)}")

        # Format result
        result = [
            {
                "player_id": player.player_id,
                "name": player.name,
                "team": player.team,
                "position": player.position,
            }
            for player in filtered_players
        ]

        # Cache the result
        self.cache.set(cache_key, result, 300)  # 5 minute cache

        return result

    async def get_player_stats_optimized(
        self, player_id: str, seasons: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive player stats with optimized query.

        Args:
            player_id: Player ID
            seasons: Optional list of seasons to include

        Returns:
            Dict with player and stats data
        """
        # Build cache key
        cache_key = self.cache.cache_key("player_stats", player_id=player_id, seasons=seasons)

        # Check cache
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        # Get player info
        player = self.db.query(Player).get(player_id)
        if not player:
            return {}

        # Query base stats for seasons
        stats_query = self.db.query(BaseStat).filter(BaseStat.player_id == player_id)
        if seasons:
            stats_query = stats_query.filter(BaseStat.season.in_(seasons))

        # Order by season and week
        stats_query = stats_query.order_by(BaseStat.season.desc(), BaseStat.week)

        # Execute query
        stats = stats_query.all()

        # Query game stats
        games_query = self.db.query(GameStats).filter(GameStats.player_id == player_id)
        if seasons:
            games_query = games_query.filter(GameStats.season.in_(seasons))

        # Order by season and week
        games_query = games_query.order_by(GameStats.season.desc(), GameStats.week)

        # Execute query
        games = games_query.all()

        # Process stats
        stats_by_season = {}

        # Process base stats
        for stat in stats:
            if stat.season not in stats_by_season:
                stats_by_season[stat.season] = {"season_totals": {}, "weekly_stats": {}}

            if stat.week is None:
                # Season total
                stats_by_season[stat.season]["season_totals"][stat.stat_type] = stat.value
            else:
                # Weekly stat
                if stat.week not in stats_by_season[stat.season]["weekly_stats"]:
                    stats_by_season[stat.season]["weekly_stats"][stat.week] = {}

                stats_by_season[stat.season]["weekly_stats"][stat.week][stat.stat_type] = stat.value

        # Process game stats
        for game in games:
            if game.season not in stats_by_season:
                stats_by_season[game.season] = {"season_totals": {}, "weekly_stats": {}}

            if game.week not in stats_by_season[game.season]["weekly_stats"]:
                stats_by_season[game.season]["weekly_stats"][game.week] = {}

            # Add game data
            game_data = {
                "opponent": game.opponent,
                "game_location": game.game_location,
                "result": game.result,
                "team_score": game.team_score,
                "opponent_score": game.opponent_score,
            }

            # Add all game stats
            for key, value in game.stats.items():
                stats_by_season[game.season]["weekly_stats"][game.week][key] = value

            # Add game metadata
            stats_by_season[game.season]["weekly_stats"][game.week]["game_data"] = game_data

        # Build result
        result = {
            "player_id": player.player_id,
            "name": player.name,
            "team": player.team,
            "position": player.position,
            "stats": stats_by_season,
        }

        # Cache the result
        self.cache.set(cache_key, result, 300)  # 5 minute cache

        return result

    async def get_available_seasons(self, player_id: Optional[str] = None) -> List[int]:
        """
        Get list of seasons with data available.

        Args:
            player_id: Optional player ID to get seasons for specific player

        Returns:
            List of season years
        """
        # Build cache key
        cache_key = self.cache.cache_key("available_seasons", player_id=player_id)

        # Check cache
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        # Build query
        if player_id:
            # Get seasons for a specific player
            query = self.db.query(BaseStat.season.distinct()).filter(
                BaseStat.player_id == player_id
            )
        else:
            # Get all seasons with data
            query = self.db.query(BaseStat.season.distinct())

        # Execute query and extract seasons
        seasons = [season[0] for season in query.all()]

        # Sort in descending order (newest first)
        seasons.sort(reverse=True)

        # Cache the result
        self.cache.set(cache_key, seasons, 3600)  # 1 hour cache

        return seasons

    async def compare_players(
        self, player_ids: List[str], season: Optional[int] = None, stats: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Compare multiple players side by side.

        Args:
            player_ids: List of player IDs to compare
            season: Optional season to compare data from
            stats: Optional list of specific stats to compare

        Returns:
            Dict with player comparison data
        """
        if not player_ids:
            return {"players": [], "stats": []}

        # Build cache key
        cache_key = self.cache.cache_key(
            "player_comparison",
            player_ids=",".join(player_ids),
            season=season,
            stats=",".join(stats) if stats else "all",
        )

        # Check cache
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        # Get players
        players = self.db.query(Player).filter(Player.player_id.in_(player_ids)).all()

        # Get the latest projections or for specific season
        projections_query = self.db.query(Projection).filter(
            Projection.player_id.in_(player_ids),
            Projection.scenario_id == None,  # Base projections only
        )

        if season:
            projections_query = projections_query.filter(Projection.season == season)

        projections = projections_query.all()

        # Organize data by player
        player_data = []

        for player in players:
            # Find player's projection
            player_projection = next(
                (p for p in projections if p.player_id == player.player_id), None
            )

            # Basic player info
            player_info = {
                "player_id": player.player_id,
                "name": player.name,
                "team": player.team,
                "position": player.position,
                "stats": {},
                "projection": {},
            }

            # Add projection data if available
            if player_projection:
                if stats:
                    # Only include requested stats
                    for stat in stats:
                        if hasattr(player_projection, stat):
                            player_info["projection"][stat] = getattr(player_projection, stat)
                else:
                    # Include position-specific stats
                    if player.position == "QB":
                        player_info["projection"] = {
                            "half_ppr": player_projection.half_ppr,
                            "games": player_projection.games,
                            "pass_yards": player_projection.pass_yards,
                            "pass_td": player_projection.pass_td,
                            "interceptions": player_projection.interceptions,
                            "rush_yards": player_projection.rush_yards,
                            "rush_td": player_projection.rush_td,
                            "comp_pct": player_projection.comp_pct,
                            "yards_per_att": player_projection.yards_per_att,
                        }
                    elif player.position == "RB":
                        player_info["projection"] = {
                            "half_ppr": player_projection.half_ppr,
                            "games": player_projection.games,
                            "rush_attempts": player_projection.rush_attempts,
                            "rush_yards": player_projection.rush_yards,
                            "rush_td": player_projection.rush_td,
                            "targets": player_projection.targets,
                            "receptions": player_projection.receptions,
                            "rec_yards": player_projection.rec_yards,
                            "rec_td": player_projection.rec_td,
                            "yards_per_carry": player_projection.yards_per_carry,
                        }
                    elif player.position in ["WR", "TE"]:
                        player_info["projection"] = {
                            "half_ppr": player_projection.half_ppr,
                            "games": player_projection.games,
                            "targets": player_projection.targets,
                            "receptions": player_projection.receptions,
                            "rec_yards": player_projection.rec_yards,
                            "rec_td": player_projection.rec_td,
                            "catch_pct": player_projection.catch_pct,
                            "yards_per_target": player_projection.yards_per_target,
                        }

            # Get player stats if a season is specified
            if season:
                base_stats = (
                    self.db.query(BaseStat)
                    .filter(
                        BaseStat.player_id == player.player_id,
                        BaseStat.season == season,
                        BaseStat.week == None,  # Season totals only
                    )
                    .all()
                )

                # Format stats into a dictionary
                for stat in base_stats:
                    player_info["stats"][stat.stat_type] = stat.value

            player_data.append(player_info)

        # Determine which stats to include in the comparison
        comparison_stats = set()

        for player in player_data:
            comparison_stats.update(player["projection"].keys())
            comparison_stats.update(player["stats"].keys())

        # Create final result
        result = {"players": player_data, "stats": sorted(list(comparison_stats))}

        # Cache the result
        self.cache.set(cache_key, result, 300)  # 5 minute cache

        return result

    async def get_player_trends(
        self, player_id: str, season: Optional[int] = None, stats: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get trend data for a player's weekly performance.

        Args:
            player_id: Player ID
            season: Optional season filter
            stats: Optional list of specific stats to include

        Returns:
            Dict with player trend data
        """
        # Build cache key
        cache_key = self.cache.cache_key(
            "player_trends",
            player_id=player_id,
            season=season,
            stats=",".join(stats) if stats else "all",
        )

        # Check cache
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        # Get player
        player = self.db.query(Player).get(player_id)
        if not player:
            return {}

        # Get game stats
        game_stats_query = (
            self.db.query(GameStats)
            .filter(GameStats.player_id == player_id)
            .order_by(GameStats.season, GameStats.week)
        )

        if season:
            game_stats_query = game_stats_query.filter(GameStats.season == season)

        game_stats = game_stats_query.all()

        # Format data for trend analysis
        trend_data = {
            "player_id": player_id,
            "name": player.name,
            "team": player.team,
            "position": player.position,
            "seasons": {},
            "trends": {},
        }

        # Organize stats by season and week
        for game in game_stats:
            if game.season not in trend_data["seasons"]:
                trend_data["seasons"][game.season] = {}

            # Extract game data
            game_data = {
                "week": game.week,
                "opponent": game.opponent,
                "game_location": game.game_location,
                "result": game.result,
                "team_score": game.team_score,
                "opponent_score": game.opponent_score,
                "stats": {},
            }

            # Add stats from JSON
            for stat_name, stat_value in game.stats.items():
                # Filter to requested stats if provided
                if stats and stat_name not in stats:
                    continue

                game_data["stats"][stat_name] = stat_value

                # Add to trend tracking
                if stat_name not in trend_data["trends"]:
                    trend_data["trends"][stat_name] = []

                trend_data["trends"][stat_name].append(
                    {
                        "season": game.season,
                        "week": game.week,
                        "value": stat_value,
                        "opponent": game.opponent,
                    }
                )

            trend_data["seasons"][game.season][game.week] = game_data

        # Calculate trend indicators (positive, negative, or neutral)
        for stat_name, stat_values in trend_data["trends"].items():
            # Only calculate trends if we have enough data points
            if len(stat_values) >= 3:
                # Sort by season and week for proper trend analysis
                stat_values.sort(key=lambda x: (x["season"], x["week"]))

                # Calculate moving average
                for i in range(len(stat_values)):
                    if i >= 2:  # Need at least 3 data points for trend
                        prev_avg = sum(sv["value"] for sv in stat_values[i - 3 : i]) / 3
                        current_val = stat_values[i]["value"]

                        # Determine trend direction
                        if current_val > prev_avg * 1.1:  # 10% improvement
                            stat_values[i]["trend"] = "positive"
                        elif current_val < prev_avg * 0.9:  # 10% decline
                            stat_values[i]["trend"] = "negative"
                        else:
                            stat_values[i]["trend"] = "neutral"
                    else:
                        stat_values[i]["trend"] = "neutral"  # Not enough data

        # Cache the result
        self.cache.set(cache_key, trend_data, 300)  # 5 minute cache

        return trend_data

    async def get_player_watchlist(
        self, user_id: str, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get player watchlist (placeholder implementation).
        In a real system, this would retrieve user-specific watchlists from the database.

        Args:
            user_id: User ID
            filters: Optional filters to apply

        Returns:
            List of watchlisted players
        """
        # In a real implementation, this would query a watchlist table
        # For now, return an empty list as a placeholder
        return []

    async def search_players_advanced(
        self,
        search_term: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = "name",
        sort_dir: str = "asc",
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[PlayerQueryResultDict], int]:
        """
        Advanced player search with filtering, sorting and pagination.

        Args:
            search_term: Optional search term for player name
            filters: Optional filters to apply
            sort_by: Field to sort by
            sort_dir: Sort direction (asc or desc)
            page: Page number (1-based)
            page_size: Number of results per page

        Returns:
            Tuple of (players_list, total_count)
        """
        # Build cache key
        cache_key = self.cache.cache_key(
            "advanced_player_search",
            search_term=search_term,
            filters=filters,
            sort_by=sort_by,
            sort_dir=sort_dir,
            page=page,
            page_size=page_size,
        )

        # Check cache
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        # Start building query
        query = self.db.query(Player)

        # Apply name search if provided
        if search_term:
            query = query.filter(Player.name.ilike(f"%{search_term}%"))

        # Apply filters
        if filters:
            if "position" in filters:
                if isinstance(filters["position"], list):
                    query = query.filter(Player.position.in_(filters["position"]))
                else:
                    query = query.filter(Player.position == filters["position"])

            if "team" in filters:
                if isinstance(filters["team"], list):
                    query = query.filter(Player.team.in_(filters["team"]))
                else:
                    query = query.filter(Player.team == filters["team"])

            if "status" in filters:
                if isinstance(filters["status"], list):
                    query = query.filter(Player.status.in_(filters["status"]))
                else:
                    query = query.filter(Player.status == filters["status"])

            if "depth_chart_position" in filters:
                if isinstance(filters["depth_chart_position"], list):
                    query = query.filter(
                        Player.depth_chart_position.in_(filters["depth_chart_position"])
                    )
                else:
                    query = query.filter(
                        Player.depth_chart_position == filters["depth_chart_position"]
                    )

            # Stat thresholds with join to projections
            stat_thresholds = {
                key: value
                for key, value in filters.items()
                if key
                in [
                    "half_ppr",
                    "pass_yards",
                    "rush_yards",
                    "rec_yards",
                    "pass_td",
                    "rush_td",
                    "rec_td",
                    "receptions",
                ]
            }

            if stat_thresholds:
                # Join with projections if stat thresholds are specified
                query = query.join(
                    Projection,
                    and_(
                        Projection.player_id == Player.player_id,
                        Projection.scenario_id == None,  # Only base projections
                    ),
                )

                # Apply stat thresholds
                for stat, threshold in stat_thresholds.items():
                    if hasattr(Projection, stat):
                        query = query.filter(getattr(Projection, stat) >= threshold)

        # Get total count before pagination
        total_count = query.count()

        # Apply sorting
        if sort_by in ["name", "team", "position", "status", "draft_position"]:
            sort_column = getattr(Player, sort_by)
        else:
            # Default to sorting by name
            sort_column = Player.name

        if sort_dir.lower() == "desc":
            sort_column = desc(sort_column)

        query = query.order_by(sort_column)

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Execute query
        players = query.all()

        # Format player data
        result = []
        for player in players:
            # Basic player info
            player_data = {
                "player_id": player.player_id,
                "name": player.name,
                "team": player.team,
                "position": player.position,
                "status": player.status,
                "depth_chart_position": player.depth_chart_position,
                "date_of_birth": player.date_of_birth.isoformat() if player.date_of_birth else None,
                "height": player.height,
                "weight": player.weight,
                "draft_position": player.draft_position,
                "draft_team": player.draft_team,
                "draft_round": player.draft_round,
                "draft_pick": player.draft_pick,
                "created_at": player.created_at.isoformat(),
                "updated_at": player.updated_at.isoformat(),
            }

            result.append(player_data)

        # Cache the result
        self.cache.set(cache_key, (result, total_count), 300)  # 5 minute cache

        return result, total_count
