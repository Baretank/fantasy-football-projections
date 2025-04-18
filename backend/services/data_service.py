from typing import Dict, List, Optional, cast, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from backend.database.models import Player, BaseStat, GameStats, TeamStat
import logging

from backend.services.typing import (
    safe_float, safe_dict_get, PlayerDataDict, GameStatsDict, PlayerSplitsDict
)

logger = logging.getLogger(__name__)


class DataService:
    """
    Service for managing player and statistical data.
    Handles data retrieval and updates, but not imports.
    """

    def __init__(self, db: Session):
        self.db = db

    async def get_player(self, player_id: str) -> Optional[Player]:
        """Retrieve a player by ID."""
        return self.db.query(Player).filter(Player.player_id == player_id).first()

    async def get_players(
        self, position: Optional[str] = None, team: Optional[str] = None
    ) -> List[Player]:
        """Retrieve players with optional filters."""
        query = self.db.query(Player)

        if position:
            query = query.filter(Player.position == position)
        if team:
            query = query.filter(Player.team == team)

        return query.all()

    async def get_player_stats(
        self, player_id: str, season: Optional[int] = None
    ) -> List[BaseStat]:
        """Retrieve player season statistics."""
        query = self.db.query(BaseStat).filter(BaseStat.player_id == player_id)

        if season:
            query = query.filter(BaseStat.season == season)

        return query.all()

    async def get_player_game_logs(
        self, player_id: str, season: Optional[int] = None
    ) -> List[GameStats]:
        """Retrieve player game-by-game statistics."""
        query = self.db.query(GameStats).filter(GameStats.player_id == player_id)

        if season:
            query = query.filter(GameStats.season == season)

        return query.order_by(GameStats.season, GameStats.week).all()

    async def update_player(self, player_id: str, data: PlayerDataDict) -> Optional[Player]:
        """Update player information."""
        try:
            player = await self.get_player(player_id)
            if player:
                for key, value in data.items():
                    setattr(player, key, value)
                self.db.commit()
            return player
        except Exception as e:
            logger.error(f"Error updating player {player_id}: {str(e)}")
            self.db.rollback()
            return None

    async def get_team_stats(
        self, team: str, season: int, week: Optional[int] = None
    ) -> Optional[TeamStat]:
        """Retrieve team statistics."""
        query = self.db.query(TeamStat).filter(
            and_(TeamStat.team == team, TeamStat.season == season)
        )

        if week:
            query = query.filter(TeamStat.week == week)

        return query.first()

    async def get_all_team_stats(self, season: int) -> List[TeamStat]:
        """Retrieve statistics for all teams in a season."""
        return self.db.query(TeamStat).filter(TeamStat.season == season).all()

    async def get_player_splits(self, player_id: str, season: int, split_type: str) -> PlayerSplitsDict:
        """
        Get player statistical splits (home/away, win/loss, etc).

        Args:
            player_id: Player's unique identifier
            season: Season year
            split_type: Type of split ('home_away' or 'win_loss')

        Returns:
            Dictionary of split statistics
        """
        game_logs = await self.get_player_game_logs(player_id, season)

        if split_type == "home_away":
            home_games = [g for g in game_logs if g.game_location == "home"]
            away_games = [g for g in game_logs if g.game_location == "away"]

            return {
                "home": self._aggregate_game_stats(home_games),
                "away": self._aggregate_game_stats(away_games),
            }

        elif split_type == "win_loss":
            wins = [g for g in game_logs if g.result == "W"]
            losses = [g for g in game_logs if g.result == "L"]

            return {
                "wins": self._aggregate_game_stats(wins),
                "losses": self._aggregate_game_stats(losses),
            }

        else:
            raise ValueError(f"Unknown split type: {split_type}")

    def _aggregate_game_stats(self, games: List[GameStats]) -> GameStatsDict:
        """Aggregate statistics from a list of games."""
        if not games:
            return {}

        # Initialize with game counts
        aggregated: GameStatsDict = {
            "games": len(games),
            "total_points": sum(safe_float(g.team_score, 0.0) for g in games),
            "points_allowed": sum(safe_float(g.opponent_score, 0.0) for g in games),
        }

        # Aggregate all stats from the JSON field
        if games and games[0].stats:
            for stat_key in games[0].stats.keys():
                try:
                    aggregated[stat_key] = sum(safe_float(safe_dict_get(g.stats, stat_key, 0.0)) for g in games)
                except (ValueError, TypeError):
                    # Skip any non-numeric stats
                    continue

        return cast(GameStatsDict, aggregated)
