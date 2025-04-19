from typing import Dict, List, Optional, Union, Any, cast
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
import logging
from datetime import datetime
import uuid

from backend.database.models import (
    Player,
    Projection,
    DraftStatus,
    DraftBoard,
    RookieProjectionTemplate,
)
from backend.services.rookie_projection_service import RookieProjectionService
from backend.services.typing import (
    safe_float, safe_dict_get, 
    PlayerDraftDataDict, DraftBoardDict, DraftStatusUpdateDict, DraftResultDict
)

logger = logging.getLogger(__name__)


class DraftService:
    """
    Service for managing fantasy football draft operations.
    Handles player draft status updates, draft board management, and related operations.
    """

    def __init__(self, db: Session):
        self.db = db
        self.rookie_projection_service = RookieProjectionService(db)

    async def get_draft_board(
        self,
        status: Optional[str] = None,
        position: Optional[str] = None,
        team: Optional[str] = None,
        order_by: str = "ranking",
        limit: int = 100,
        offset: int = 0,
    ) -> DraftBoardDict:
        """
        Retrieve players for the draft board with optional filters.

        Args:
            status: Filter by draft status (available, drafted, watched)
            position: Filter by player position (QB, RB, WR, TE)
            team: Filter by NFL team
            order_by: Field to order by (ranking, name, position, team, points)
            limit: Maximum number of players to return
            offset: Number of players to skip

        Returns:
            Dict with player list and metadata
        """
        # Build the query with filters
        query = self.db.query(Player)

        # Apply status filter if provided
        if status:
            try:
                draft_status = DraftStatus(status)
                query = query.filter(Player.draft_status == draft_status)
            except ValueError:
                # Invalid status, log and ignore
                logger.warning(f"Invalid draft status filter: {status}")

        # Apply position filter if provided
        if position:
            query = query.filter(Player.position == position)

        # Apply team filter if provided
        if team:
            query = query.filter(Player.team == team)

        # Apply ordering
        if order_by == "name":
            query = query.order_by(Player.name)
        elif order_by == "position":
            query = query.order_by(Player.position, Player.name)
        elif order_by == "team":
            query = query.order_by(Player.team, Player.name)
        elif order_by == "points":
            # Join with projections to order by points
            query = query.join(
                Projection,
                and_(Player.player_id == Projection.player_id, Projection.scenario_id.is_(None)),
            ).order_by(desc(Projection.half_ppr))
        else:
            # Default ordering by draft status first (available first), then by name
            query = query.order_by(
                # Available first, then watched, then drafted
                Player.draft_status,
                Player.name,
            )

        # Count the total before applying limit/offset
        total_count = query.count()

        # Apply limit and offset
        players = query.limit(limit).offset(offset).all()

        # Get projections for these players
        player_ids = [p.player_id for p in players]
        projections = (
            self.db.query(Projection)
            .filter(and_(Projection.player_id.in_(player_ids), Projection.scenario_id.is_(None)))
            .all()
        )

        # Create a lookup of projections by player_id
        proj_by_player = {p.player_id: p for p in projections}

        # Format the response
        formatted_players: List[PlayerDraftDataDict] = []
        for player in players:
            player_data: PlayerDraftDataDict = {
                "player_id": player.player_id,
                "name": player.name,
                "team": player.team,
                "position": player.position,
                "draft_status": player.draft_status.value,
                "fantasy_team": player.fantasy_team,
                "draft_order": player.draft_order,
                "is_rookie": player.is_rookie,
            }

            # Add projection data if available
            if player.player_id in proj_by_player:
                proj = proj_by_player[player.player_id]
                player_data["points"] = safe_float(proj.half_ppr)
                player_data["games"] = proj.games

            formatted_players.append(player_data)

        # Get status counts
        status_counts = {}
        for status in ["available", "drafted", "watched"]:
            count = self.db.query(Player).filter(Player.draft_status == status).count()
            status_counts[status] = count

        return {"players": formatted_players, "total": total_count, "counts": status_counts}

    async def update_draft_status(
        self,
        player_id: str,
        status: str,
        fantasy_team: Optional[str] = None,
        draft_order: Optional[int] = None,
        create_projection: bool = False,
    ) -> Optional[Player]:
        """
        Update a player's draft status.

        Args:
            player_id: The ID of the player to update
            status: The new status (available, drafted, watched)
            fantasy_team: The fantasy team that drafted the player (for 'drafted' status)
            draft_order: The order in which the player was drafted (for 'drafted' status)
            create_projection: Whether to create a projection for rookie players

        Returns:
            The updated player or None if player not found
        """
        try:
            # Find the player
            player = self.db.query(Player).filter(Player.player_id == player_id).first()
            if not player:
                logger.warning(f"Player not found: {player_id}")
                return None

            # Update the status
            try:
                draft_status = DraftStatus(status)
                player.draft_status = draft_status
            except ValueError:
                logger.warning(f"Invalid draft status: {status}")
                return None

            # If status is 'drafted', update fantasy team and draft order
            if draft_status == DraftStatus.DRAFTED:
                player.fantasy_team = fantasy_team

                # If no draft order provided, use the next available slot
                if draft_order is None:
                    # Get the highest draft order so far
                    highest = (
                        self.db.query(Player)
                        .filter(Player.draft_status == DraftStatus.DRAFTED)
                        .order_by(desc(Player.draft_order))
                        .first()
                    )

                    if highest and highest.draft_order:
                        draft_order = highest.draft_order + 1
                    else:
                        draft_order = 1

                player.draft_order = draft_order

                # Create projection for rookies if requested
                if create_projection and player.is_rookie:
                    # Get current season
                    current_season = datetime.now().year
                    # Check if we're past the draft for this year's season
                    # and should be projecting for next year
                    if datetime.now().month >= 9:  # September or later
                        current_season += 1

                    # Check for existing projection
                    existing = (
                        self.db.query(Projection)
                        .filter(
                            and_(
                                Projection.player_id == player_id,
                                Projection.season == current_season,
                                Projection.scenario_id.is_(None),
                            )
                        )
                        .first()
                    )

                    if not existing:
                        # Get draft position for rookie projection
                        draft_position = (
                            player.draft_pick if player.draft_pick else player.draft_position
                        )

                        if draft_position:
                            projection = (
                                await self.rookie_projection_service.create_draft_based_projection(
                                    player_id=player_id,
                                    draft_position=draft_position,
                                    season=current_season,
                                )
                            )

                            if projection:
                                logger.info(
                                    f"Created projection for rookie {player.name} at draft position {draft_position}"
                                )

            # Update player and commit changes
            self.db.commit()
            return player

        except Exception as e:
            logger.error(f"Error updating draft status: {str(e)}")
            self.db.rollback()
            return None

    async def batch_update_draft_status(self, updates: List[DraftStatusUpdateDict]) -> DraftResultDict:
        """
        Update draft status for multiple players in one operation.

        Args:
            updates: List of player updates with player_id, status, and optional fantasy_team/draft_order

        Returns:
            Dict with success/error counts
        """
        success_count = 0
        error_messages = []

        try:
            # Process each update in sequence
            for update in updates:
                player_id = update.get("player_id")
                status = update.get("status")

                if not player_id or not status:
                    error_messages.append(f"Missing player_id or status in update: {update}")
                    continue

                # Update the player
                result = await self.update_draft_status(
                    player_id=player_id,
                    status=status,
                    fantasy_team=update.get("fantasy_team"),
                    draft_order=update.get("draft_order"),
                    create_projection=update.get("create_projection", False),
                )

                if result:
                    success_count += 1
                else:
                    error_messages.append(f"Failed to update player {player_id}")

            # Success if at least one update succeeded
            return {
                "success": success_count > 0,
                "success_count": success_count,
                "error_count": len(error_messages),
                "error_messages": error_messages,
            }

        except Exception as e:
            logger.error(f"Error in batch update: {str(e)}")
            self.db.rollback()
            return {
                "success": False,
                "success_count": success_count,
                "error_count": 1,
                "error_messages": [str(e)],
            }

    async def reset_draft(self) -> DraftResultDict:
        """
        Reset all players to 'available' status.

        Returns:
            Dict with reset count
        """
        try:
            # Get count of non-available players
            count = (
                self.db.query(Player).filter(Player.draft_status != DraftStatus.AVAILABLE).count()
            )

            # Update all players to available
            self.db.query(Player).update(
                {"draft_status": DraftStatus.AVAILABLE, "fantasy_team": None, "draft_order": None}
            )

            self.db.commit()
            return {"success": True, "reset_count": count}

        except Exception as e:
            logger.error(f"Error resetting draft: {str(e)}")
            self.db.rollback()
            return {"success": False, "error": str(e)}

    async def undo_last_draft_pick(self) -> DraftResultDict:
        """
        Undo the last draft pick by setting the player with the highest draft order back to 'available'.

        Returns:
            Dict with player info or error
        """
        try:
            # Find the last drafted player
            last_pick = (
                self.db.query(Player)
                .filter(Player.draft_status == DraftStatus.DRAFTED)
                .order_by(desc(Player.draft_order))
                .first()
            )

            if not last_pick:
                return {"success": False, "error": "No drafted players found"}

            # Store player info for response
            player_info = {
                "player_id": last_pick.player_id,
                "name": last_pick.name,
                "team": last_pick.team,
                "position": last_pick.position,
                "fantasy_team": last_pick.fantasy_team,
                "draft_order": last_pick.draft_order,
            }

            # Reset player to available
            last_pick.draft_status = DraftStatus.AVAILABLE
            last_pick.fantasy_team = None
            last_pick.draft_order = None

            self.db.commit()
            return {"success": True, "player": player_info}

        except Exception as e:
            logger.error(f"Error undoing last draft pick: {str(e)}")
            self.db.rollback()
            return {"success": False, "error": str(e)}

    async def get_draft_progress(self) -> Dict[str, Any]:
        """
        Get overall draft progress statistics.

        Returns:
            Dict with draft progress metrics
        """
        try:
            # Get total player count
            total_players = self.db.query(Player).count()

            # Get count by status
            available_count = (
                self.db.query(Player).filter(Player.draft_status == DraftStatus.AVAILABLE).count()
            )

            drafted_count = (
                self.db.query(Player).filter(Player.draft_status == DraftStatus.DRAFTED).count()
            )

            watched_count = (
                self.db.query(Player).filter(Player.draft_status == DraftStatus.WATCHED).count()
            )

            # Get counts by position for drafted players
            position_counts = {}
            for position in ["QB", "RB", "WR", "TE"]:
                count = (
                    self.db.query(Player)
                    .filter(
                        and_(
                            Player.draft_status == DraftStatus.DRAFTED, Player.position == position
                        )
                    )
                    .count()
                )
                position_counts[position] = count

            # Get the highest draft order for positions filled
            highest_order = (
                self.db.query(Player)
                .filter(Player.draft_status == DraftStatus.DRAFTED)
                .order_by(desc(Player.draft_order))
                .first()
            )

            draft_positions_filled = highest_order.draft_order if highest_order else 0

            return {
                "total_players": total_players,
                "available_players": available_count,
                "drafted_players": drafted_count,
                "watched_players": watched_count,
                "position_counts": position_counts,
                "draft_positions_filled": draft_positions_filled,
            }

        except Exception as e:
            logger.error(f"Error getting draft progress: {str(e)}")
            return {"error": str(e)}

    async def create_draft_board(
        self,
        name: str,
        description: Optional[str] = None,
        season: Optional[int] = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> Optional[DraftBoard]:
        """
        Create a new draft board.

        Args:
            name: The name of the draft board
            description: Optional description
            season: The season for the draft (defaults to current year)
            settings: Optional configuration settings

        Returns:
            The created draft board or None if creation failed
        """
        try:
            # Use current year if season not provided
            if not season:
                season = datetime.now().year

            # Create new draft board
            draft_board = DraftBoard(
                draft_board_id=str(uuid.uuid4()),
                name=name,
                description=description,
                season=season,
                settings=settings,
            )

            self.db.add(draft_board)
            self.db.commit()
            return draft_board

        except Exception as e:
            logger.error(f"Error creating draft board: {str(e)}")
            self.db.rollback()
            return None

    async def get_draft_boards(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get all draft boards with optional filtering.

        Args:
            active_only: If True, only return active draft boards

        Returns:
            List of draft boards
        """
        try:
            query = self.db.query(DraftBoard)

            if active_only:
                query = query.filter(DraftBoard.active == True)

            boards = query.order_by(DraftBoard.created_at.desc()).all()

            # Format the response
            result = []
            for board in boards:
                result.append(
                    {
                        "draft_board_id": board.draft_board_id,
                        "name": board.name,
                        "description": board.description,
                        "season": board.season,
                        "active": board.active,
                        "number_of_teams": board.number_of_teams,
                        "roster_spots": board.roster_spots,
                        "current_pick": board.current_pick,
                        "created_at": board.created_at.isoformat() if board.created_at else None,
                    }
                )

            return result

        except Exception as e:
            logger.error(f"Error getting draft boards: {str(e)}")
            return []
