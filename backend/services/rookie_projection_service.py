from typing import Dict, List, Optional, Tuple, Any, Union, cast
from sqlalchemy.orm import Session
from sqlalchemy import and_
import pandas as pd
import logging
import json
import uuid
from pathlib import Path
from datetime import datetime

from backend.database.models import Player, Projection, TeamStat, Scenario, RookieProjectionTemplate

logger = logging.getLogger(__name__)


class RookieProjectionService:
    """Service for creating and managing rookie player projections."""

    def __init__(self, db: Session):
        self.db = db
        self.rookie_comp_model = {
            "QB": {
                "high": {
                    "pass_attempts": 550,
                    "comp_pct": 0.64,
                    "yards_per_att": 7.5,
                    "pass_td_rate": 0.05,
                    "int_rate": 0.025,
                    "rush_att_per_game": 4.5,
                    "rush_yards_per_att": 5.0,
                    "rush_td_per_game": 0.25,
                },
                "medium": {
                    "pass_attempts": 450,
                    "comp_pct": 0.60,
                    "yards_per_att": 6.8,
                    "pass_td_rate": 0.04,
                    "int_rate": 0.03,
                    "rush_att_per_game": 3.5,
                    "rush_yards_per_att": 4.5,
                    "rush_td_per_game": 0.2,
                },
                "low": {
                    "pass_attempts": 300,
                    "comp_pct": 0.56,
                    "yards_per_att": 6.2,
                    "pass_td_rate": 0.03,
                    "int_rate": 0.035,
                    "rush_att_per_game": 2.5,
                    "rush_yards_per_att": 4.0,
                    "rush_td_per_game": 0.1,
                },
            },
            "RB": {
                "high": {
                    "rush_att_per_game": 15.0,
                    "rush_yards_per_att": 4.6,
                    "rush_td_per_att": 0.04,
                    "targets_per_game": 4.0,
                    "catch_rate": 0.75,
                    "rec_yards_per_catch": 8.5,
                    "rec_td_per_catch": 0.05,
                },
                "medium": {
                    "rush_att_per_game": 11.0,
                    "rush_yards_per_att": 4.2,
                    "rush_td_per_att": 0.03,
                    "targets_per_game": 3.0,
                    "catch_rate": 0.7,
                    "rec_yards_per_catch": 7.5,
                    "rec_td_per_catch": 0.03,
                },
                "low": {
                    "rush_att_per_game": 7.0,
                    "rush_yards_per_att": 3.8,
                    "rush_td_per_att": 0.02,
                    "targets_per_game": 2.0,
                    "catch_rate": 0.65,
                    "rec_yards_per_catch": 6.5,
                    "rec_td_per_catch": 0.02,
                },
            },
            "WR": {
                "high": {
                    "targets_per_game": 7.5,
                    "catch_rate": 0.65,
                    "rec_yards_per_catch": 13.5,
                    "rec_td_per_catch": 0.08,
                    "rush_att_per_game": 0.5,
                    "rush_yards_per_att": 8.0,
                    "rush_td_per_att": 0.04,
                },
                "medium": {
                    "targets_per_game": 5.5,
                    "catch_rate": 0.62,
                    "rec_yards_per_catch": 12.0,
                    "rec_td_per_catch": 0.06,
                    "rush_att_per_game": 0.3,
                    "rush_yards_per_att": 7.0,
                    "rush_td_per_att": 0.03,
                },
                "low": {
                    "targets_per_game": 3.5,
                    "catch_rate": 0.58,
                    "rec_yards_per_catch": 10.5,
                    "rec_td_per_catch": 0.04,
                    "rush_att_per_game": 0.1,
                    "rush_yards_per_att": 6.0,
                    "rush_td_per_att": 0.02,
                },
            },
            "TE": {
                "high": {
                    "targets_per_game": 5.5,
                    "catch_rate": 0.68,
                    "rec_yards_per_catch": 11.5,
                    "rec_td_per_catch": 0.07,
                    "rush_att_per_game": 0.0,
                    "rush_yards_per_att": 0.0,
                    "rush_td_per_att": 0.0,
                },
                "medium": {
                    "targets_per_game": 3.5,
                    "catch_rate": 0.65,
                    "rec_yards_per_catch": 10.0,
                    "rec_td_per_catch": 0.05,
                    "rush_att_per_game": 0.0,
                    "rush_yards_per_att": 0.0,
                    "rush_td_per_att": 0.0,
                },
                "low": {
                    "targets_per_game": 2.0,
                    "catch_rate": 0.60,
                    "rec_yards_per_catch": 9.0,
                    "rec_td_per_catch": 0.03,
                    "rush_att_per_game": 0.0,
                    "rush_yards_per_att": 0.0,
                    "rush_td_per_att": 0.0,
                },
            },
        }

    async def get_rookie_data(self) -> List[Dict[str, Any]]:
        """
        Load rookie data from the rookies.json file.
        """
        try:
            data_dir = Path(__file__).parent.parent.parent / "data"
            rookie_file = data_dir / "rookies.json"

            if not rookie_file.exists():
                logger.error(f"Rookie data file not found: {rookie_file}")
                return []

            with open(rookie_file, "r") as f:
                rookie_data = json.load(f)

            return rookie_data.get("rookies", [])

        except Exception as e:
            logger.error(f"Error reading rookie data: {str(e)}")
            return []

    async def create_rookie_projections(
        self, season: int, scenario_id: Optional[str] = None
    ) -> Tuple[int, List[str]]:
        """
        Create projections for all rookies in the rookies.json file.
        Returns (success_count, error_messages)
        """
        rookies = await self.get_rookie_data()
        if not rookies:
            return 0, ["No rookie data found"]

        success_count = 0
        error_messages = []

        for rookie_data in rookies:
            try:
                # Check if player already exists
                player = (
                    self.db.query(Player)
                    .filter(
                        and_(
                            Player.name == rookie_data["name"],
                            Player.position == rookie_data["position"],
                        )
                    )
                    .first()
                )

                # Create player if needed
                if not player:
                    player = Player(
                        player_id=str(uuid.uuid4()),
                        name=rookie_data["name"],
                        team=rookie_data["team"],
                        position=rookie_data["position"],
                    )
                    self.db.add(player)
                    self.db.flush()
                    logger.info(f"Created new player for rookie: {rookie_data['name']}")
                elif player.team != rookie_data["team"]:
                    # Update team if it changed
                    player.team = rookie_data["team"]
                    logger.info(
                        f"Updated team for rookie: {rookie_data['name']} to {rookie_data['team']}"
                    )

                # Create or update projection
                await self._create_rookie_projection(
                    player=player, rookie_data=rookie_data, season=season, scenario_id=scenario_id
                )

                success_count += 1

            except Exception as e:
                msg = (
                    f"Error creating projection for {rookie_data.get('name', 'unknown')}: {str(e)}"
                )
                logger.error(msg)
                error_messages.append(msg)

        # Commit all changes
        self.db.commit()
        return success_count, error_messages

    async def enhance_rookie_projection(
        self,
        player_id: str,
        comp_level: str = "medium",
        playing_time_pct: float = 0.5,
        season: int = 2025,
    ) -> Optional[Projection]:
        """
        Enhance a rookie projection using historical comparison models.

        Args:
            player_id: The player ID to enhance
            comp_level: Comparison level (high, medium, low)
            playing_time_pct: Percentage of playing time (0.0-1.0)
            season: The season year

        Returns:
            Updated projection or None if error
        """
        try:
            # Get the player and team context
            player = self.db.query(Player).get(player_id)
            if not player:
                logger.error(f"Player {player_id} not found")
                return None

            # Get existing projection
            projection = (
                self.db.query(Projection)
                .filter(
                    and_(
                        Projection.player_id == player_id,
                        Projection.season == season,
                        Projection.scenario_id == None,  # Base projection
                    )
                )
                .first()
            )

            if not projection:
                logger.error(f"No base projection found for {player.name}")
                return None

            # Get team stats
            team_stats = (
                self.db.query(TeamStat)
                .filter(and_(TeamStat.team == player.team, TeamStat.season == season))
                .first()
            )

            # If no team stats, enhance based solely on comp model
            if not team_stats:
                enhanced_proj = await self._enhance_with_comp_model(
                    projection, player, comp_level, playing_time_pct
                )
            else:
                # Enhance using both comp model and team context
                enhanced_proj = await self._enhance_with_team_context(
                    projection, player, team_stats, comp_level, playing_time_pct
                )

            # Recalculate fantasy points
            if enhanced_proj:
                enhanced_proj.half_ppr = enhanced_proj.calculate_fantasy_points()
                enhanced_proj.updated_at = datetime.utcnow()
                self.db.commit()

            return enhanced_proj

        except Exception as e:
            logger.error(f"Error enhancing rookie projection: {str(e)}")
            self.db.rollback()
            return None

    async def _create_rookie_projection(
        self, player: Player, rookie_data: Dict, season: int, scenario_id: Optional[str] = None
    ) -> Projection:
        """
        Create or update a projection for a rookie player.
        """
        # Check if projection already exists
        projection = (
            self.db.query(Projection)
            .filter(
                and_(
                    Projection.player_id == player.player_id,
                    Projection.season == season,
                    Projection.scenario_id == scenario_id,
                )
            )
            .first()
        )

        # Use rookie data for initial projection
        projected_stats = rookie_data.get("projected_stats", {})

        # Determine if this is a high-draft pick (top 64)
        is_high_pick = rookie_data.get("draft_position", 999) <= 64

        # Get comp model level based on draft position
        if is_high_pick:
            comp_level = "high"
        elif rookie_data.get("draft_position", 999) <= 150:
            comp_level = "medium"
        else:
            comp_level = "low"

        # If no projection exists, create a new one
        if not projection:
            projection = Projection(
                projection_id=str(uuid.uuid4()),
                player_id=player.player_id,
                scenario_id=scenario_id,
                season=season,
                games=projected_stats.get("games", 17),
                half_ppr=0.0,  # Will be calculated
            )

            # Set initial stats based on position
            if player.position == "QB":
                projection.pass_attempts = projected_stats.get("pass_attempts", 0)
                projection.completions = projected_stats.get("completions", 0)
                projection.pass_yards = projected_stats.get("pass_yards", 0)
                projection.pass_td = projected_stats.get("pass_td", 0)
                projection.interceptions = projected_stats.get("interceptions", 0)
                projection.rush_attempts = projected_stats.get("rush_attempts", 0)
                projection.rush_yards = projected_stats.get("rush_yards", 0)
                projection.rush_td = projected_stats.get("rush_td", 0)

                # Calculate efficiency metrics
                # Add None checks to prevent type errors
                if projection.pass_attempts is not None and projection.pass_attempts > 0:
                    if projection.completions is not None:
                        projection.comp_pct = projection.completions / projection.pass_attempts
                    if projection.pass_yards is not None:
                        projection.yards_per_att = projection.pass_yards / projection.pass_attempts
                    if projection.pass_td is not None:
                        projection.pass_td_rate = projection.pass_td / projection.pass_attempts
                    if projection.interceptions is not None:
                        projection.int_rate = projection.interceptions / projection.pass_attempts

                if projection.rush_attempts is not None and projection.rush_attempts > 0 and projection.rush_yards is not None:
                    projection.yards_per_carry = projection.rush_yards / projection.rush_attempts

            elif player.position in ["RB", "WR", "TE"]:
                projection.rush_attempts = projected_stats.get(
                    "rush_attempts", 0
                ) or projected_stats.get("rush_attempts", 0)
                projection.rush_yards = projected_stats.get("rush_yards", 0)
                projection.rush_td = projected_stats.get("rush_td", 0)
                projection.targets = projected_stats.get("targets", 0)
                projection.receptions = projected_stats.get("receptions", 0)
                projection.rec_yards = projected_stats.get("rec_yards", 0)
                projection.rec_td = projected_stats.get("rec_td", 0)

                # Calculate efficiency metrics
                # Add None checks to prevent type errors
                if projection.rush_attempts is not None and projection.rush_attempts > 0 and projection.rush_yards is not None:
                    projection.yards_per_carry = projection.rush_yards / projection.rush_attempts

                if projection.targets is not None and projection.targets > 0:
                    if projection.receptions is not None:
                        projection.catch_pct = projection.receptions / projection.targets
                    if projection.rec_yards is not None:
                        projection.yards_per_target = projection.rec_yards / projection.targets

                if projection.receptions is not None and projection.receptions > 0 and projection.rec_yards is not None:
                    projection.yards_per_reception = projection.rec_yards / projection.receptions

            # Add to db
            self.db.add(projection)

        else:
            # Update existing projection with new data
            logger.info(f"Updating existing projection for {player.name}")

            if player.position == "QB":
                # Only update if values are provided
                if "pass_attempts" in projected_stats:
                    projection.pass_attempts = projected_stats["pass_attempts"]
                if "completions" in projected_stats:
                    projection.completions = projected_stats["completions"]
                if "pass_yards" in projected_stats:
                    projection.pass_yards = projected_stats["pass_yards"]
                if "pass_td" in projected_stats:
                    projection.pass_td = projected_stats["pass_td"]
                if "interceptions" in projected_stats:
                    projection.interceptions = projected_stats["interceptions"]
                if "rush_attempts" in projected_stats:
                    projection.rush_attempts = projected_stats["rush_attempts"]
                if "rush_yards" in projected_stats:
                    projection.rush_yards = projected_stats["rush_yards"]
                if "rush_td" in projected_stats:
                    projection.rush_td = projected_stats["rush_td"]

            elif player.position in ["RB", "WR", "TE"]:
                if "rush_attempts" in projected_stats or "rush_attempts" in projected_stats:
                    projection.rush_attempts = projected_stats.get(
                        "rush_attempts",
                        projected_stats.get("rush_attempts", projection.rush_attempts),
                    )
                if "rush_yards" in projected_stats:
                    projection.rush_yards = projected_stats["rush_yards"]
                if "rush_td" in projected_stats:
                    projection.rush_td = projected_stats["rush_td"]
                if "targets" in projected_stats:
                    projection.targets = projected_stats["targets"]
                if "receptions" in projected_stats:
                    projection.receptions = projected_stats["receptions"]
                if "rec_yards" in projected_stats:
                    projection.rec_yards = projected_stats["rec_yards"]
                if "rec_td" in projected_stats:
                    projection.rec_td = projected_stats["rec_td"]

        # Apply historical comp model to enhance the projection
        await self._enhance_with_comp_model(projection, player, comp_level, 1.0)

        # Calculate fantasy points
        projection.half_ppr = projection.calculate_fantasy_points()

        return projection

    async def _enhance_with_comp_model(
        self,
        projection: Projection,
        player: Player,
        comp_level: str = "medium",
        playing_time_pct: float = 1.0,
    ) -> Projection:
        """
        Enhance a rookie projection using the historical comparison model.
        """
        # Ensure valid comp level
        if comp_level not in ["high", "medium", "low"]:
            comp_level = "medium"

        # Get comparison model for position
        if player.position not in self.rookie_comp_model:
            logger.warning(f"No comparison model for position: {player.position}")
            return projection

        model = self.rookie_comp_model[player.position][comp_level]
        games = projection.games

        # Apply model based on position
        if player.position == "QB":
            # Apply comparison model with playing time adjustment
            pass_attempts = model["pass_attempts"] * playing_time_pct
            projection.pass_attempts = pass_attempts
            projection.completions = pass_attempts * model["comp_pct"]
            projection.pass_yards = pass_attempts * model["yards_per_att"]
            projection.pass_td = pass_attempts * model["pass_td_rate"]
            projection.interceptions = pass_attempts * model["int_rate"]

            # Rushing stats
            projection.rush_attempts = games * model["rush_att_per_game"] * playing_time_pct
            projection.rush_yards = projection.rush_attempts * model["rush_yards_per_att"]
            projection.rush_td = games * model["rush_td_per_game"] * playing_time_pct

            # Calculate efficiency metrics
            projection.comp_pct = model["comp_pct"]
            projection.yards_per_att = model["yards_per_att"]
            projection.pass_td_rate = model["pass_td_rate"]
            projection.int_rate = model["int_rate"]
            projection.yards_per_carry = model["rush_yards_per_att"]

        elif player.position == "RB":
            # Rushing stats
            projection.rush_attempts = games * model["rush_att_per_game"] * playing_time_pct
            projection.rush_yards = projection.rush_attempts * model["rush_yards_per_att"]
            projection.rush_td = projection.rush_attempts * model["rush_td_per_att"]

            # Receiving stats
            projection.targets = games * model["targets_per_game"] * playing_time_pct
            projection.receptions = projection.targets * model["catch_rate"]
            projection.rec_yards = projection.receptions * model["rec_yards_per_catch"]
            projection.rec_td = projection.receptions * model["rec_td_per_catch"]

            # Efficiency metrics
            projection.catch_pct = model["catch_rate"]
            projection.yards_per_carry = model["rush_yards_per_att"]
            projection.yards_per_target = model["rec_yards_per_catch"] * model["catch_rate"]

        elif player.position in ["WR", "TE"]:
            # Receiving stats
            projection.targets = games * model["targets_per_game"] * playing_time_pct
            projection.receptions = projection.targets * model["catch_rate"]
            projection.rec_yards = projection.receptions * model["rec_yards_per_catch"]
            projection.rec_td = projection.receptions * model["rec_td_per_catch"]

            # Rushing stats (mainly for WR)
            projection.rush_attempts = games * model["rush_att_per_game"] * playing_time_pct
            projection.rush_yards = projection.rush_attempts * model["rush_yards_per_att"]
            projection.rush_td = projection.rush_attempts * model["rush_td_per_att"]

            # Efficiency metrics
            projection.catch_pct = model["catch_rate"]
            projection.yards_per_target = model["rec_yards_per_catch"] * model["catch_rate"]
            if projection.receptions > 0:
                projection.yards_per_reception = model["rec_yards_per_catch"]

        return projection

    async def create_draft_based_projection(
        self, player_id: str, draft_position: int, season: int, scenario_id: Optional[str] = None
    ) -> Optional[Projection]:
        """
        Create a rookie projection based on draft position.

        Args:
            player_id: The rookie player's ID
            draft_position: Overall draft position (1-262)
            season: The projection season
            scenario_id: Optional scenario ID

        Returns:
            Created projection or None if failed
        """
        try:
            # Get the player
            player = self.db.query(Player).filter(Player.player_id == player_id).first()
            if not player:
                logger.error(f"Player {player_id} not found")
                return None

            # Set status to Rookie
            player.status = "Rookie"
            player.draft_position = draft_position

            # Find appropriate template based on position and draft position
            template = (
                self.db.query(RookieProjectionTemplate)
                .filter(
                    RookieProjectionTemplate.position == player.position,
                    RookieProjectionTemplate.draft_pick_min <= draft_position,
                    RookieProjectionTemplate.draft_pick_max >= draft_position,
                )
                .first()
            )

            if not template:
                logger.warning(f"No template found for {player.position} at pick {draft_position}")
                # Fall back to most generic template for this position
                template = (
                    self.db.query(RookieProjectionTemplate)
                    .filter(RookieProjectionTemplate.position == player.position)
                    .order_by(RookieProjectionTemplate.draft_pick_max.desc())
                    .first()
                )

                # If we still don't have a template, create a default one based on position
                if not template:
                    logger.warning(f"Creating default template for {player.position}")
                    template = RookieProjectionTemplate(
                        template_id=str(uuid.uuid4()),
                        position=player.position,
                        draft_round=draft_position // 32 + 1,
                        draft_pick_min=1,
                        draft_pick_max=262,
                        games=16.0,
                        snap_share=0.5,
                    )

                    # Set position-specific fields with default values
                    if player.position == "QB":
                        template.pass_attempts = 450.0
                        template.comp_pct = 0.62
                        template.yards_per_att = 7.0
                        template.pass_td_rate = 0.042
                        template.int_rate = 0.025
                        template.rush_att_per_game = 4.0
                        template.rush_yards_per_att = 4.8
                        template.rush_td_per_game = 0.2
                    elif player.position == "RB":
                        template.rush_att_per_game = 11.0
                        template.rush_yards_per_att = 4.2
                        template.rush_td_per_att = 0.03
                        template.targets_per_game = 3.0
                        template.catch_rate = 0.7
                        template.rec_yards_per_catch = 8.0
                        template.rec_td_per_catch = 0.03
                    elif player.position in ["WR", "TE"]:
                        template.targets_per_game = 5.0
                        template.catch_rate = 0.65
                        template.rec_yards_per_catch = 12.0
                        template.rec_td_per_catch = 0.05
                        template.rush_att_per_game = 0.3
                        template.rush_yards_per_att = 7.0
                        template.rush_td_per_att = 0.03

                if not template:
                    logger.error(f"No fallback template found for {player.position}")
                    # Use the comp model if no template found
                    comp_level = "low"
                    if draft_position <= 32:
                        comp_level = "high"
                    elif draft_position <= 100:
                        comp_level = "medium"

                    # Create a basic projection
                    projection = Projection(
                        projection_id=str(uuid.uuid4()),
                        player_id=player_id,
                        scenario_id=scenario_id,
                        season=season,
                        games=17.0,
                    )

                    # Use the standard comp model
                    self.db.add(projection)
                    enhanced_proj = await self._enhance_with_comp_model(
                        projection, player, comp_level, 0.6
                    )

                    if enhanced_proj:
                        enhanced_proj.half_ppr = enhanced_proj.calculate_fantasy_points()
                        self.db.commit()
                        return enhanced_proj
                    return None

            # Create projection based on template
            projection = Projection(
                projection_id=str(uuid.uuid4()),
                player_id=player_id,
                scenario_id=scenario_id,
                season=season,
                games=template.games,
            )

            # Set position-specific metrics from template
            if player.position == "QB":
                if template.pass_attempts is not None:
                    # Ensure all fields are properly checked for None before operations
                    projection.pass_attempts = template.pass_attempts * template.games
                    
                    if template.comp_pct is not None:
                        projection.completions = projection.pass_attempts * template.comp_pct
                    else:
                        projection.completions = projection.pass_attempts * 0.62  # Default comp_pct
                        
                    if template.yards_per_att is not None:
                        projection.pass_yards = projection.pass_attempts * template.yards_per_att
                    else:
                        projection.pass_yards = projection.pass_attempts * 7.0  # Default yards_per_att
                        
                    if template.pass_td_rate is not None:
                        projection.pass_td = projection.pass_attempts * template.pass_td_rate
                    else:
                        projection.pass_td = projection.pass_attempts * 0.042  # Default pass_td_rate
                        
                    if template.int_rate is not None:
                        projection.interceptions = projection.pass_attempts * template.int_rate
                    else:
                        projection.interceptions = projection.pass_attempts * 0.025  # Default int_rate
                else:
                    # Use defaults
                    projection.pass_attempts = 450.0
                    projection.completions = projection.pass_attempts * 0.62  # Default comp_pct
                    projection.pass_yards = projection.pass_attempts * 7.0  # Default yards_per_att
                    projection.pass_td = projection.pass_attempts * 0.042  # Default pass_td_rate
                    projection.interceptions = projection.pass_attempts * 0.025  # Default int_rate

                # Rush stats
                if template.rush_att_per_game is not None:
                    projection.rush_attempts = template.rush_att_per_game * template.games
                    if template.rush_yards_per_att is not None:
                        projection.rush_yards = (
                            projection.rush_attempts * template.rush_yards_per_att
                        )
                    else:
                        projection.rush_yards = projection.rush_attempts * 4.8  # Default
                    if template.rush_td_per_game is not None:
                        projection.rush_td = template.rush_td_per_game * template.games
                    else:
                        projection.rush_td = template.games * 0.2  # Default
                else:
                    projection.rush_attempts = 4.0 * template.games  # Default rush_att_per_game
                    projection.rush_yards = projection.rush_attempts * 4.8
                    projection.rush_td = template.games * 0.2

                # Set efficiency metrics
                projection.comp_pct = template.comp_pct
                projection.yards_per_att = template.yards_per_att
                projection.pass_td_rate = template.pass_td_rate
                projection.int_rate = template.int_rate
                projection.yards_per_carry = template.rush_yards_per_att

            elif player.position == "RB":
                # Rush stats
                if template.rush_att_per_game is not None:
                    projection.rush_attempts = template.rush_att_per_game * template.games
                    if template.rush_yards_per_att is not None:
                        projection.rush_yards = (
                            projection.rush_attempts * template.rush_yards_per_att
                        )
                    else:
                        projection.rush_yards = projection.rush_attempts * 4.2  # Default
                    if template.rush_td_per_att is not None:
                        projection.rush_td = projection.rush_attempts * template.rush_td_per_att
                    else:
                        projection.rush_td = projection.rush_attempts * 0.03  # Default
                else:
                    projection.rush_attempts = 11.0 * template.games  # Default
                    projection.rush_yards = projection.rush_attempts * 4.2  # Default
                    projection.rush_td = projection.rush_attempts * 0.03  # Default

                # Receiving stats
                if template.targets_per_game is not None:
                    projection.targets = template.targets_per_game * template.games
                    if template.catch_rate is not None:
                        projection.receptions = projection.targets * template.catch_rate
                    else:
                        projection.receptions = projection.targets * 0.7  # Default

                    if template.rec_yards_per_catch is not None and projection.receptions is not None and projection.receptions > 0:
                        projection.rec_yards = projection.receptions * template.rec_yards_per_catch
                    elif projection.receptions is not None:
                        projection.rec_yards = projection.receptions * 8.0  # Default
                    else:
                        projection.rec_yards = 0.0  # Fallback if receptions is None

                    if template.rec_td_per_catch is not None and projection.receptions is not None and projection.receptions > 0:
                        projection.rec_td = projection.receptions * template.rec_td_per_catch
                    elif projection.receptions is not None:
                        projection.rec_td = projection.receptions * 0.03  # Default
                    else:
                        projection.rec_td = 0.0  # Fallback if receptions is None
                else:
                    projection.targets = 3.0 * template.games  # Default
                    projection.receptions = projection.targets * 0.7  # Default
                    projection.rec_yards = projection.receptions * 8.0  # Default
                    projection.rec_td = projection.receptions * 0.03  # Default

                # Set efficiency metrics with proper None handling
                projection.catch_pct = template.catch_rate
                projection.yards_per_carry = template.rush_yards_per_att
                
                # Safely calculate yards_per_target with None checks
                if template.rec_yards_per_catch is not None and template.catch_rate is not None:
                    projection.yards_per_target = template.rec_yards_per_catch * template.catch_rate
                elif template.rec_yards_per_catch is not None:
                    projection.yards_per_target = template.rec_yards_per_catch * 0.7  # Default catch rate
                elif template.catch_rate is not None:
                    projection.yards_per_target = 8.0 * template.catch_rate  # Default yards per catch
                else:
                    projection.yards_per_target = 8.0 * 0.7  # Default values

            elif player.position in ["WR", "TE"]:
                # Receiving stats (primary for WR/TE)
                if template.targets_per_game is not None:
                    projection.targets = template.targets_per_game * template.games
                    if template.catch_rate is not None:
                        projection.receptions = projection.targets * template.catch_rate
                    else:
                        projection.receptions = projection.targets * 0.65  # Default

                    if template.rec_yards_per_catch is not None and projection.receptions > 0:
                        projection.rec_yards = projection.receptions * template.rec_yards_per_catch
                    else:
                        projection.rec_yards = projection.receptions * 12.0  # Default

                    if template.rec_td_per_catch is not None and projection.receptions > 0:
                        projection.rec_td = projection.receptions * template.rec_td_per_catch
                    else:
                        projection.rec_td = projection.receptions * 0.05  # Default
                else:
                    # Use defaults
                    default_targets_per_game = 5.0
                    projection.targets = default_targets_per_game * template.games
                    projection.receptions = projection.targets * 0.65  # Default
                    projection.rec_yards = projection.receptions * 12.0  # Default
                    projection.rec_td = projection.receptions * 0.05  # Default

                # Rush stats (minimal for WR, none for TE) with proper None handling
                if template.rush_att_per_game is not None and template.games is not None:
                    projection.rush_attempts = template.rush_att_per_game * template.games
                    
                    # Handle rush yards calculation with None checks
                    if projection.rush_attempts is not None:
                        if template.rush_yards_per_att is not None:
                            projection.rush_yards = (
                                projection.rush_attempts * template.rush_yards_per_att
                            )
                        else:
                            projection.rush_yards = projection.rush_attempts * 7.0  # Default

                        # Handle rush TD calculation with None checks
                        if template.rush_td_per_att is not None:
                            projection.rush_td = projection.rush_attempts * template.rush_td_per_att
                        else:
                            projection.rush_td = projection.rush_attempts * 0.03  # Default
                else:
                    # Use defaults - minimal for WR, none for TE
                    if player.position == "WR" and template.games is not None:
                        projection.rush_attempts = 0.3 * template.games  # Default
                        # Only set rush_yards if rush_attempts is not None
                        if projection.rush_attempts is not None:
                            projection.rush_yards = projection.rush_attempts * 7.0  # Default
                        projection.rush_td = projection.rush_attempts * 0.03  # Default
                    else:  # TE
                        projection.rush_attempts = 0.0
                        projection.rush_yards = 0.0
                        projection.rush_td = 0.0

                # Set efficiency metrics with proper None handling
                projection.catch_pct = template.catch_rate
                
                # Safely calculate yards_per_target with None checks
                if template.rec_yards_per_catch is not None and template.catch_rate is not None:
                    projection.yards_per_target = template.rec_yards_per_catch * template.catch_rate
                elif template.rec_yards_per_catch is not None:
                    projection.yards_per_target = template.rec_yards_per_catch * 0.7  # Default catch rate
                elif template.catch_rate is not None:
                    projection.yards_per_target = 8.0 * template.catch_rate  # Default yards per catch
                else:
                    projection.yards_per_target = 8.0 * 0.7  # Default values
                
                # Set yards_per_reception with None checks
                if projection.receptions is not None and projection.receptions > 0:
                    projection.yards_per_reception = template.rec_yards_per_catch

            # Set usage metrics
            projection.snap_share = template.snap_share

            # Calculate fantasy points
            projection.half_ppr = projection.calculate_fantasy_points()

            # Save to database
            self.db.add(projection)
            self.db.commit()

            return projection

        except Exception as e:
            logger.error(f"Error creating draft-based projection: {str(e)}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            self.db.rollback()
            return None

    async def _enhance_with_team_context(
        self,
        projection: Projection,
        player: Player,
        team_stats: TeamStat,
        comp_level: str = "medium",
        playing_time_pct: float = 0.5,
    ) -> Projection:
        """
        Enhance a rookie projection using both the comparison model and team context.
        """
        # First enhance with comp model
        projection = await self._enhance_with_comp_model(
            projection, player, comp_level, playing_time_pct
        )

        # Then adjust based on team context
        if player.position == "QB":
            # Adjust pass volume based on team tendencies, with proper None handling
            team_pass_att_per_game = float(team_stats.pass_attempts) / 17.0
            
            # Make sure pass_attempts and games are not None before division
            if projection.pass_attempts is not None and projection.games is not None and projection.games > 0:
                model_pass_att_per_game = projection.pass_attempts / projection.games

                # Blend model and team tendencies (70% model, 30% team)
                adjusted_pass_att = (
                    (model_pass_att_per_game * 0.7 + team_pass_att_per_game * 0.3)
                    * projection.games
                    * playing_time_pct
                )

                # Apply adjustment - check if pass_attempts is positive
                if projection.pass_attempts > 0:
                    adj_factor = adjusted_pass_att / projection.pass_attempts
                    projection.pass_attempts = adjusted_pass_att
                    
                    # Apply adjustments to related stats with None checks
                    if projection.completions is not None:
                        projection.completions *= adj_factor
                    if projection.pass_yards is not None:
                        projection.pass_yards *= adj_factor
                    if projection.pass_td is not None:
                        projection.pass_td *= adj_factor
                    if projection.interceptions is not None:
                        projection.interceptions *= adj_factor

        elif player.position == "RB":
            # Adjust rush volume based on team tendencies, with proper None handling
            team_rush_att_per_game = float(team_stats.rush_attempts) / 17.0
            
            # Make sure rush_attempts and games are not None before division
            if projection.rush_attempts is not None and projection.games is not None and projection.games > 0:
                model_rush_att_per_game = projection.rush_attempts / projection.games

                # Blend model and team tendencies (60% model, 40% team)
                adjusted_rush_att = (
                    (
                        model_rush_att_per_game * 0.6
                        + team_rush_att_per_game * 0.4 * 0.3  # Assume 30% team share
                    )
                    * projection.games
                    * playing_time_pct
                )

            # Apply adjustment if rush_attempts is defined and positive
            if (projection.rush_attempts is not None and projection.rush_attempts > 0 and 
                'adjusted_rush_att' in locals()):  # Check if adjusted_rush_att is defined
                adj_factor = adjusted_rush_att / projection.rush_attempts
                projection.rush_attempts = adjusted_rush_att
                
                # Apply adjustments to related stats with None checks
                if projection.rush_yards is not None:
                    projection.rush_yards *= adj_factor
                if projection.rush_td is not None:
                    projection.rush_td *= adj_factor

            # Adjust receiving volume with proper None handling
            team_targets_per_game = float(team_stats.targets) / 17.0
            rb_target_share = 0.15  # Assume RBs get ~15% of targets

            # Calculate adjusted targets only if games is not None
            if projection.games is not None:
                adjusted_targets = (
                    (team_targets_per_game * rb_target_share * 0.3)  # Assume 30% of RB targets
                    * projection.games
                    * playing_time_pct
                )

                # Apply adjustment if targets is defined and positive
                if projection.targets is not None and projection.targets > 0:
                    adj_factor = adjusted_targets / projection.targets
                    projection.targets = adjusted_targets
                    
                    # Apply adjustments to related stats with None checks
                    if projection.receptions is not None:
                        projection.receptions *= adj_factor
                    if projection.rec_yards is not None:
                        projection.rec_yards *= adj_factor
                    if projection.rec_td is not None:
                        projection.rec_td *= adj_factor

        elif player.position == "WR":
            # Adjust target volume based on team tendencies with proper None handling
            team_targets_per_game = float(team_stats.targets) / 17.0
            wr_target_share = 0.7  # Assume WRs get ~70% of targets

            # Calculate adjusted targets only if games is not None
            if projection.games is not None:
                adjusted_targets = (
                    (
                        team_targets_per_game
                        * wr_target_share
                        * 0.2  # Assume rookie gets 20% of WR targets
                    )
                    * projection.games
                    * playing_time_pct
                )

                # Apply adjustment if targets is defined and positive
                if projection.targets is not None and projection.targets > 0:
                    adj_factor = adjusted_targets / projection.targets
                    projection.targets = adjusted_targets
                    
                    # Apply adjustments to related stats with None checks
                    if projection.receptions is not None:
                        projection.receptions *= adj_factor
                    if projection.rec_yards is not None:
                        projection.rec_yards *= adj_factor
                    if projection.rec_td is not None:
                        projection.rec_td *= adj_factor

        elif player.position == "TE":
            # Adjust target volume based on team tendencies with proper None handling
            team_targets_per_game = float(team_stats.targets) / 17.0
            te_target_share = 0.15  # Assume TEs get ~15% of targets

            # Calculate adjusted targets only if games is not None
            if projection.games is not None:
                adjusted_targets = (
                    (
                        team_targets_per_game
                        * te_target_share
                        * 0.5  # Assume rookie gets 50% of TE targets if starting
                    )
                    * projection.games
                    * playing_time_pct
                )

                # Apply adjustment if targets is defined and positive
                if projection.targets is not None and projection.targets > 0:
                    adj_factor = adjusted_targets / projection.targets
                    projection.targets = adjusted_targets
                    
                    # Apply adjustments to related stats with None checks
                    if projection.receptions is not None:
                        projection.receptions *= adj_factor
                    if projection.rec_yards is not None:
                        projection.rec_yards *= adj_factor
                    if projection.rec_td is not None:
                        projection.rec_td *= adj_factor

        return projection
