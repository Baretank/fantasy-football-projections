from typing import Dict, List, Optional, Any, Tuple, Union
from sqlalchemy.orm import Session, joinedload, contains_eager
from sqlalchemy import and_, or_, desc, func, text
import logging
from datetime import datetime
import asyncio

from backend.database.models import Player, Projection, BaseStat, GameStats, Scenario
from backend.services.cache_service import get_cache

logger = logging.getLogger(__name__)

class QueryService:
    """Service for optimized database queries and player listings."""
    
    def __init__(self, db: Session):
        self.db = db
        self.cache = get_cache()
    
    async def get_players_optimized(
        self, 
        filters: Optional[Dict[str, Any]] = None,
        include_projections: bool = False,
        include_stats: bool = False,
        page: int = 1,
        page_size: int = 50,
        sort_by: str = "name",
        sort_dir: str = "asc"
    ) -> Tuple[List[Dict[str, Any]], int]:
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
            sort_dir=sort_dir
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
                    Projection.scenario_id == None  # Only include base projections
                )
            ).options(contains_eager(Player.projections))
        
        if include_stats:
            # Join the most recent season's base stats
            subquery = self.db.query(
                BaseStat.player_id,
                func.max(BaseStat.season).label('latest_season')
            ).group_by(BaseStat.player_id).subquery()
            
            query = query.outerjoin(
                BaseStat,
                and_(
                    BaseStat.player_id == Player.player_id,
                    BaseStat.season == subquery.c.latest_season,
                    BaseStat.week == None  # Only season totals
                )
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
        
        # Format result
        result = []
        for player in players:
            player_data = {
                "player_id": player.player_id,
                "name": player.name,
                "team": player.team,
                "position": player.position
            }
            
            if include_projections:
                # Find base projection
                base_proj = next(
                    (p for p in player.projections if p.scenario_id is None),
                    None
                )
                
                if base_proj:
                    player_data["projection"] = {
                        "projection_id": base_proj.projection_id,
                        "half_ppr": base_proj.half_ppr,
                        "season": base_proj.season
                    }
                    
                    # Add position-specific stats
                    if player.position == "QB":
                        player_data["projection"].update({
                            "pass_yards": base_proj.pass_yards,
                            "pass_td": base_proj.pass_td,
                            "interceptions": base_proj.interceptions,
                            "rush_yards": base_proj.rush_yards,
                            "rush_td": base_proj.rush_td
                        })
                    elif player.position in ["RB", "WR", "TE"]:
                        player_data["projection"].update({
                            "rush_yards": base_proj.rush_yards,
                            "rush_td": base_proj.rush_td,
                            "rec_yards": base_proj.rec_yards,
                            "rec_td": base_proj.rec_td
                        })
            
            if include_stats:
                # Process base stats
                stats_data = {}
                for stat in player.base_stats:
                    if stat.season not in stats_data:
                        stats_data[stat.season] = {}
                    stats_data[stat.season][stat.stat_type] = stat.value
                    
                player_data["stats"] = stats_data
                
            result.append(player_data)
        
        # Cache the result
        self.cache.set(cache_key, (result, total_count), 300)  # 5 minute cache
        
        return result, total_count
    
    async def search_players(
        self,
        search_term: str,
        position: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
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
            "player_search",
            search_term=search_term,
            position=position,
            limit=limit
        )
        
        # Check cache
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Build query for partial name matching
        query = self.db.query(Player).filter(
            Player.name.ilike(f"%{search_term}%")
        )
        
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
        
        # Format result
        result = [
            {
                "player_id": player.player_id,
                "name": player.name,
                "team": player.team,
                "position": player.position
            }
            for player in players
        ]
        
        # Cache the result
        self.cache.set(cache_key, result, 300)  # 5 minute cache
        
        return result
    
    async def get_player_stats_optimized(
        self,
        player_id: str,
        seasons: Optional[List[int]] = None
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
        cache_key = self.cache.cache_key(
            "player_stats",
            player_id=player_id,
            seasons=seasons
        )
        
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
                stats_by_season[stat.season] = {
                    "season_totals": {},
                    "weekly_stats": {}
                }
                
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
                stats_by_season[game.season] = {
                    "season_totals": {},
                    "weekly_stats": {}
                }
                
            if game.week not in stats_by_season[game.season]["weekly_stats"]:
                stats_by_season[game.season]["weekly_stats"][game.week] = {}
                
            # Add game data
            game_data = {
                "opponent": game.opponent,
                "game_location": game.game_location,
                "result": game.result,
                "team_score": game.team_score,
                "opponent_score": game.opponent_score
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
            "stats": stats_by_season
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
        cache_key = self.cache.cache_key(
            "available_seasons",
            player_id=player_id
        )
        
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