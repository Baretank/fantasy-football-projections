from typing import Dict, List, Optional, Any, Tuple, Union, Callable, TypedDict, cast
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
import logging
import uuid
import csv
import io
import json
import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from backend.database.models import Player, Projection, BaseStat, Scenario, StatOverride, ImportLog
from backend.services.projection_service import ProjectionService
from backend.services.rookie_projection_service import RookieProjectionService
from backend.services.typing import (
    StatsDict, 
    AdjustmentDict, 
    PlayerDict,
    StatsDict_T,
    AdjustmentDict_T,
    safe_float,
    safe_dict_get
)

# Batch operation result types
class BatchResultDict(TypedDict, total=False):
    """Dictionary for batch operation results"""
    success: int
    failure: int
    failed_players: List[Dict[str, Any]]
    failed_projections: List[Dict[str, Any]]
    failed_scenarios: List[Dict[str, Any]]
    projection_ids: Dict[str, str]
    scenario_ids: Dict[str, str]
    error: str

class ExportFilterDict(TypedDict, total=False):
    """Dictionary for export filter options"""
    player_ids: List[str]
    team: str
    position: Union[str, List[str]]
    season: int
    scenario_id: str

logger = logging.getLogger(__name__)


class BatchService:
    """Service for handling batch operations on projections."""

    def __init__(self, db: Session):
        self.db = db
        self.projection_service = ProjectionService(db)
        self.rookie_service = RookieProjectionService(db)
        self.failure_threshold = 5  # Default threshold for circuit breaker pattern

    async def process_batch(
        self,
        service: Any,
        method_name: str,
        items: List[Any],
        batch_size: int = 5,
        delay: float = 1.0,
        **kwargs: Any,
    ) -> Dict[Any, bool]:
        """
        Process a batch of items using a specified service method.

        Args:
            service: Service instance to call methods on
            method_name: Name of the method to call
            items: List of items to process
            batch_size: Size of concurrent batches
            delay: Delay between batches in seconds
            **kwargs: Additional arguments to pass to the method

        Returns:
            Dictionary mapping items to success/failure results
        """
        results: Dict[Any, bool] = {}
        method = getattr(service, method_name)
        consecutive_failures: int = 0

        # Process in batches
        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]

            # Check if circuit breaker is active
            if consecutive_failures >= self.failure_threshold:
                # Log circuit breaker activation
                try:
                    details_dict: Dict[str, Any] = {
                        "failed_items": len(results), 
                        "total_items": len(items)
                    }
                    
                    log_entry = ImportLog(
                        log_id=str(uuid.uuid4()),
                        operation=f"batch_process:{method_name}",
                        status="failure",
                        message=f"Circuit breaker activated after {consecutive_failures} consecutive failures",
                        details=details_dict,
                    )
                    self.db.add(log_entry)
                    self.db.commit()
                except Exception as e:
                    logger.error(f"Error committing circuit breaker log: {str(e)}")
                    self.db.rollback()

                # Mark remaining items as failed
                for item in items[i:]:
                    results[item] = False
                break

            # Process this batch concurrently
            batch_tasks: List[Tuple[Any, asyncio.Task[bool]]] = []
            for item in batch:
                task = asyncio.create_task(self._safe_execute(method, item, **kwargs))
                batch_tasks.append((item, task))

            # Wait for batch completion
            batch_failures: int = 0
            for item, task in batch_tasks:
                try:
                    success = await task
                    results[item] = success
                    if not success:
                        batch_failures += 1
                except Exception as e:
                    results[item] = False
                    batch_failures += 1
                    # Log error
                    try:
                        details_dict: Dict[str, Any] = {"item": str(item)}
                        
                        log_entry = ImportLog(
                            log_id=str(uuid.uuid4()),
                            operation=f"batch_process:{method_name}",
                            status="failure",
                            message=f"Error processing item: {str(e)}",
                            details=details_dict,
                        )
                        self.db.add(log_entry)
                        self.db.commit()
                    except Exception as log_error:
                        logger.error(f"Error creating error log: {str(log_error)}")
                        self.db.rollback()

            # Update consecutive failures counter and explicitly check threshold
            if batch_failures == len(batch):
                consecutive_failures += 1
                # Circuit breaker check after updating
                if consecutive_failures >= self.failure_threshold:
                    logger.warning(
                        f"Circuit breaker threshold reached with {consecutive_failures} consecutive failures"
                    )
            else:
                consecutive_failures = 0

            # Commit logs
            try:
                self.db.commit()
            except Exception as e:
                logger.error(f"Error committing logs: {str(e)}")
                self.db.rollback()

            # Add delay between batches (if not the last batch)
            if i + batch_size < len(items):
                await asyncio.sleep(delay)

        return results

    async def _safe_execute(self, method: Callable[..., Any], item: Any, **kwargs: Any) -> bool:
        """
        Safely execute a method with error handling.

        Args:
            method: Method to call
            item: Item to process
            **kwargs: Additional arguments

        Returns:
            True if successful, False otherwise
        """
        try:
            result = await method(item, **kwargs)
            return bool(result)
        except Exception as e:
            # Log exception but don't raise
            logger.error(f"Error in batch processing: {str(e)}")
            return False

    async def batch_create_projections(
        self, player_ids: List[str], season: int, scenario_id: Optional[str] = None
    ) -> BatchResultDict:
        """
        Create projections for multiple players at once.

        Args:
            player_ids: List of player IDs to create projections for
            season: The season year
            scenario_id: Optional scenario ID

        Returns:
            Dict with success/failure counts and details
        """
        result: BatchResultDict = {
            "success": 0, 
            "failure": 0, 
            "failed_players": [], 
            "projection_ids": {}
        }

        try:
            # Get all players at once
            players = self.db.query(Player).filter(Player.player_id.in_(player_ids)).all()

            # Create a mapping for easy lookup
            player_map: Dict[str, Player] = {p.player_id: p for p in players}

            # Process each player
            for player_id in player_ids:
                try:
                    # Skip if player doesn't exist
                    if player_id not in player_map:
                        result["failure"] = result.get("failure", 0) + 1
                        if "failed_players" not in result:
                            result["failed_players"] = []
                        result["failed_players"].append(
                            {"player_id": player_id, "reason": "Player not found"}
                        )
                        continue

                    # Check if projection already exists
                    existing = (
                        self.db.query(Projection)
                        .filter(
                            and_(
                                Projection.player_id == player_id,
                                Projection.season == season,
                                Projection.scenario_id == scenario_id,
                            )
                        )
                        .first()
                    )

                    if existing:
                        # Add to successful results
                        result["success"] = result.get("success", 0) + 1
                        if "projection_ids" not in result:
                            result["projection_ids"] = {}
                        result["projection_ids"][player_id] = existing.projection_id
                        continue

                    # Create new projection
                    projection = await self.projection_service.create_base_projection(
                        player_id=player_id, season=season
                    )

                    if projection:
                        result["success"] = result.get("success", 0) + 1
                        if "projection_ids" not in result:
                            result["projection_ids"] = {}
                        result["projection_ids"][player_id] = projection.projection_id
                    else:
                        result["failure"] = result.get("failure", 0) + 1
                        if "failed_players" not in result:
                            result["failed_players"] = []
                        result["failed_players"].append(
                            {"player_id": player_id, "reason": "Failed to create projection"}
                        )

                except Exception as e:
                    result["failure"] = result.get("failure", 0) + 1
                    if "failed_players" not in result:
                        result["failed_players"] = []
                    result["failed_players"].append({"player_id": player_id, "reason": str(e)})

            # Commit all changes
            self.db.commit()
            return result

        except Exception as e:
            logger.error(f"Error in batch projection creation: {str(e)}")
            self.db.rollback()
            error_result: BatchResultDict = {
                "success": 0, 
                "failure": len(player_ids), 
                "error": str(e),
                "failed_players": [],
                "projection_ids": {}
            }
            return error_result

    async def batch_adjust_projections(
        self, adjustments: Dict[str, AdjustmentDict]
    ) -> BatchResultDict:
        """
        Apply adjustments to multiple projections at once.

        Args:
            adjustments: Dict mapping projection IDs to adjustment dictionaries
                {projection_id: {adjustment_metric: value}}

        Returns:
            Dict with success/failure counts and details
        """
        result: BatchResultDict = {
            "success": 0, 
            "failure": 0, 
            "failed_projections": []
        }

        try:
            # Get all projections at once
            projection_ids = list(adjustments.keys())
            projections = (
                self.db.query(Projection).filter(Projection.projection_id.in_(projection_ids)).all()
            )

            # Create a mapping for easy lookup
            projection_map: Dict[str, Projection] = {p.projection_id: p for p in projections}

            # Process each projection
            for proj_id, adj_values in adjustments.items():
                try:
                    # Skip if projection doesn't exist
                    if proj_id not in projection_map:
                        result["failure"] = result.get("failure", 0) + 1
                        if "failed_projections" not in result:
                            result["failed_projections"] = []
                        result["failed_projections"].append(
                            {"projection_id": proj_id, "reason": "Projection not found"}
                        )
                        continue

                    # Apply adjustments
                    updated = await self.projection_service.update_projection(
                        projection_id=proj_id, adjustments=adj_values
                    )

                    if updated:
                        result["success"] = result.get("success", 0) + 1
                    else:
                        result["failure"] = result.get("failure", 0) + 1
                        if "failed_projections" not in result:
                            result["failed_projections"] = []
                        result["failed_projections"].append(
                            {"projection_id": proj_id, "reason": "Failed to apply adjustments"}
                        )

                except Exception as e:
                    result["failure"] = result.get("failure", 0) + 1
                    if "failed_projections" not in result:
                        result["failed_projections"] = []
                    result["failed_projections"].append(
                        {"projection_id": proj_id, "reason": str(e)}
                    )

            # Commit all changes
            self.db.commit()
            return result

        except Exception as e:
            logger.error(f"Error in batch projection adjustment: {str(e)}")
            self.db.rollback()
            error_result: BatchResultDict = {
                "success": 0, 
                "failure": len(adjustments), 
                "error": str(e),
                "failed_projections": []
            }
            return error_result

    async def export_projections(
        self,
        format: str = "csv",
        filters: Optional[ExportFilterDict] = None,
        include_metadata: bool = False,
    ) -> Tuple[str, bytes]:
        """
        Export projections in various formats (CSV, JSON).

        Args:
            format: Export format (csv, json)
            filters: Optional filters to apply
            include_metadata: Whether to include metadata fields

        Returns:
            Tuple of (filename, file_content as bytes)
        """
        try:
            # Build the query
            query = self.db.query(Projection).join(Player)

            # Apply filters if provided
            if filters:
                if "player_ids" in filters and filters["player_ids"]:
                    player_ids = filters["player_ids"]
                    query = query.filter(Projection.player_id.in_(player_ids))
                
                if "team" in filters and filters["team"]:
                    team = filters["team"]
                    query = query.filter(Player.team == team)
                
                if "position" in filters and filters["position"]:
                    position = filters["position"]
                    # Handle both string and list of positions
                    if isinstance(position, list):
                        query = query.filter(Player.position.in_(position))
                    else:
                        query = query.filter(Player.position == position)
                
                if "season" in filters and filters["season"]:
                    season = filters["season"]
                    query = query.filter(Projection.season == season)
                
                if "scenario_id" in filters and filters["scenario_id"]:
                    scenario_id = filters["scenario_id"]
                    query = query.filter(Projection.scenario_id == scenario_id)

            # Execute query
            projections = query.all()

            # Generate timestamp for filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Export based on format
            if format.lower() == "csv":
                return await self._export_to_csv(projections, timestamp, include_metadata)
            elif format.lower() == "json":
                return await self._export_to_json(projections, timestamp, include_metadata)
            else:
                raise ValueError(f"Unsupported export format: {format}")

        except Exception as e:
            logger.error(f"Error exporting projections: {str(e)}")
            raise

    async def _export_to_csv(
        self, projections: List[Projection], timestamp: str, include_metadata: bool
    ) -> Tuple[str, bytes]:
        """Export projections to CSV format."""
        # Determine which fields to include
        basic_fields: List[str] = ["player_id", "name", "team", "position", "season", "games", "half_ppr"]

        # Position-specific stat fields
        position_fields: Dict[str, List[str]] = {
            "QB": [
                "pass_attempts",
                "completions",
                "pass_yards",
                "pass_td",
                "interceptions",
                "rush_attempts",
                "rush_yards",
                "rush_td",
            ],
            "RB": [
                "rush_attempts",
                "rush_yards",
                "rush_td",
                "targets",
                "receptions",
                "rec_yards",
                "rec_td",
            ],
            "WR": [
                "targets",
                "receptions",
                "rec_yards",
                "rec_td",
                "rush_attempts",
                "rush_yards",
                "rush_td",
            ],
            "TE": ["targets", "receptions", "rec_yards", "rec_td"],
        }

        # Add efficiency metrics if requested
        efficiency_fields: List[str] = [
            "comp_pct",
            "yards_per_att",
            "yards_per_carry",
            "catch_pct",
            "yards_per_target",
        ]

        # Add metadata fields if requested
        metadata_fields: List[str] = ["projection_id", "scenario_id", "created_at", "updated_at"]

        # Create CSV file in memory
        output = io.StringIO()
        csv_writer = csv.writer(output)

        # Write header row
        all_fields: List[str] = basic_fields.copy()

        # Add all possible stat fields
        for pos_fields in position_fields.values():
            for field in pos_fields:
                if field not in all_fields:
                    all_fields.append(field)

        # Add efficiency and metadata if requested
        all_fields.extend(efficiency_fields)
        if include_metadata:
            all_fields.extend(metadata_fields)

        csv_writer.writerow(all_fields)

        # Write data rows
        for proj in projections:
            row_data: List[Any] = []

            # Add player info
            row_data.append(proj.player_id)
            row_data.append(proj.player.name if hasattr(proj, 'player') and proj.player else None)
            row_data.append(proj.player.team if hasattr(proj, 'player') and proj.player else None)
            row_data.append(proj.player.position if hasattr(proj, 'player') and proj.player else None)
            row_data.append(proj.season)
            row_data.append(proj.games)
            row_data.append(proj.half_ppr)

            # Add position stats - safely handle potentially missing fields
            position = proj.player.position if hasattr(proj, 'player') and proj.player else ""
            pos_fields = position_fields.get(position, [])
            
            for field in position_fields.get("QB", []):
                value = getattr(proj, field, None) if field in pos_fields else None
                row_data.append(value)

            for field in position_fields.get("RB", []):
                if field not in position_fields.get("QB", []):
                    value = getattr(proj, field, None) if field in pos_fields else None
                    row_data.append(value)

            # Add efficiency metrics
            for field in efficiency_fields:
                row_data.append(getattr(proj, field, None))

            # Add metadata if requested
            if include_metadata:
                row_data.append(proj.projection_id)
                row_data.append(proj.scenario_id)
                row_data.append(proj.created_at.isoformat() if proj.created_at else None)
                row_data.append(proj.updated_at.isoformat() if proj.updated_at else None)

            csv_writer.writerow(row_data)

        # Generate filename
        filename = f"projections_{timestamp}.csv"

        # Get bytes content
        content = output.getvalue().encode("utf-8")
        output.close()

        return filename, content

    async def _export_to_json(
        self, projections: List[Projection], timestamp: str, include_metadata: bool
    ) -> Tuple[str, bytes]:
        """Export projections to JSON format."""
        result: List[Dict[str, Any]] = []

        for proj in projections:
            # Create basic projection data with safe attribute access
            proj_data: Dict[str, Any] = {
                "player_id": proj.player_id,
                "name": proj.player.name if hasattr(proj, 'player') and proj.player else None,
                "team": proj.player.team if hasattr(proj, 'player') and proj.player else None,
                "position": proj.player.position if hasattr(proj, 'player') and proj.player else None,
                "season": proj.season,
                "games": proj.games,
                "half_ppr": proj.half_ppr,
            }

            # Safely get player position
            position = proj.player.position if hasattr(proj, 'player') and proj.player else ""

            # Add position-specific stats with type safety
            if position == "QB":
                # Use rush_attempts instead of rush_attempts for standardization
                rush_attempts = getattr(proj, "rush_attempts", None)
                pass_attempts = getattr(proj, "pass_attempts", None)
                completions = getattr(proj, "completions", None)
                pass_yards = getattr(proj, "pass_yards", None)
                pass_td = getattr(proj, "pass_td", None)
                interceptions = getattr(proj, "interceptions", None)
                rush_yards = getattr(proj, "rush_yards", None)
                rush_td = getattr(proj, "rush_td", None)
                
                proj_data.update(
                    {
                        "pass_attempts": pass_attempts,
                        "completions": completions,
                        "pass_yards": pass_yards,
                        "pass_td": pass_td,
                        "interceptions": interceptions,
                        "rush_attempts": rush_attempts,
                        "rush_yards": rush_yards,
                        "rush_td": rush_td,
                    }
                )
            elif position in ["RB", "WR", "TE"]:
                # Use rush_attempts instead of rush_attempts for standardization
                rush_attempts = getattr(proj, "rush_attempts", None)
                if rush_attempts is not None:
                    rush_yards = getattr(proj, "rush_yards", None)
                    rush_td = getattr(proj, "rush_td", None)
                    
                    proj_data.update(
                        {
                            "rush_attempts": rush_attempts,
                            "rush_yards": rush_yards,
                            "rush_td": rush_td,
                        }
                    )
                
                targets = getattr(proj, "targets", None)
                if targets is not None:
                    receptions = getattr(proj, "receptions", None)
                    rec_yards = getattr(proj, "rec_yards", None)
                    rec_td = getattr(proj, "rec_td", None)
                    
                    proj_data.update(
                        {
                            "targets": targets,
                            "receptions": receptions,
                            "rec_yards": rec_yards,
                            "rec_td": rec_td,
                        }
                    )

            # Add efficiency metrics with type safety
            efficiency: Dict[str, Any] = {}
            
            comp_pct = getattr(proj, "comp_pct", None)
            if comp_pct is not None:
                efficiency["comp_pct"] = comp_pct
                
            yards_per_att = getattr(proj, "yards_per_att", None)
            if yards_per_att is not None:
                efficiency["yards_per_att"] = yards_per_att
                
            yards_per_carry = getattr(proj, "yards_per_carry", None)
            if yards_per_carry is not None:
                efficiency["yards_per_carry"] = yards_per_carry
                
            catch_pct = getattr(proj, "catch_pct", None)
            if catch_pct is not None:
                efficiency["catch_pct"] = catch_pct
                
            yards_per_target = getattr(proj, "yards_per_target", None)
            if yards_per_target is not None:
                efficiency["yards_per_target"] = yards_per_target

            if efficiency:
                proj_data["efficiency"] = efficiency

            # Add metadata if requested
            if include_metadata:
                proj_data["projection_id"] = proj.projection_id
                
                scenario_id = getattr(proj, "scenario_id", None)
                if scenario_id:
                    proj_data["scenario_id"] = scenario_id
                    
                created_at = getattr(proj, "created_at", None)
                if created_at:
                    proj_data["created_at"] = created_at.isoformat()
                    
                updated_at = getattr(proj, "updated_at", None)
                if updated_at:
                    proj_data["updated_at"] = updated_at.isoformat()

            result.append(proj_data)

        # Generate filename
        filename = f"projections_{timestamp}.json"

        # Convert to JSON and get bytes
        content = json.dumps(result, indent=2).encode("utf-8")

        return filename, content

    # Scenario template type
    class ScenarioTemplate(TypedDict, total=False):
        name: str
        description: Optional[str]
        base_scenario_id: Optional[str]
        adjustments: AdjustmentDict
        player_adjustments: Dict[str, AdjustmentDict]
    
    async def batch_create_scenarios(
        self, scenario_templates: List[ScenarioTemplate]
    ) -> BatchResultDict:
        """
        Create multiple scenarios at once.

        Args:
            scenario_templates: List of scenario templates with:
                - name: Scenario name
                - description: Optional description
                - base_scenario_id: Optional base scenario to clone
                - adjustments: Dict of global adjustments
                - player_adjustments: Dict of player-specific adjustments

        Returns:
            Dict with success/failure counts and created scenario IDs
        """
        result: BatchResultDict = {
            "success": 0, 
            "failure": 0, 
            "failed_scenarios": [], 
            "scenario_ids": {}
        }

        try:
            for template in scenario_templates:
                try:
                    # Type validation with safe accesses
                    if "name" not in template:
                        # Skip templates without names
                        result["failure"] = result.get("failure", 0) + 1
                        if "failed_scenarios" not in result:
                            result["failed_scenarios"] = []
                        result["failed_scenarios"].append(
                            {"name": "Unknown", "reason": "Missing required 'name' field"}
                        )
                        continue
                    
                    # Create the scenario
                    name = template["name"]
                    description = template.get("description")
                    base_scenario_id = template.get("base_scenario_id")
                    
                    scenario_id = await self.projection_service.create_scenario(
                        name=name,
                        description=description,
                        base_scenario_id=base_scenario_id,
                    )

                    if not scenario_id:
                        result["failure"] = result.get("failure", 0) + 1
                        if "failed_scenarios" not in result:
                            result["failed_scenarios"] = []
                        result["failed_scenarios"].append(
                            {"name": name, "reason": "Failed to create scenario"}
                        )
                        continue

                    # Apply global adjustments if provided
                    if "adjustments" in template and template["adjustments"]:
                        # Get all projections for this scenario
                        projections = (
                            self.db.query(Projection)
                            .filter(Projection.scenario_id == scenario_id)
                            .all()
                        )

                        adjustments = template["adjustments"]
                        for proj in projections:
                            await self.projection_service.update_projection(
                                projection_id=proj.projection_id,
                                adjustments=adjustments,
                            )

                    # Apply player-specific adjustments if provided
                    if "player_adjustments" in template and template["player_adjustments"]:
                        player_adjustments = template["player_adjustments"]
                        for player_id, adjustments in player_adjustments.items():
                            # Find the player's projection in this scenario
                            proj = (
                                self.db.query(Projection)
                                .filter(
                                    and_(
                                        Projection.player_id == player_id,
                                        Projection.scenario_id == scenario_id,
                                    )
                                )
                                .first()
                            )

                            if proj:
                                await self.projection_service.update_projection(
                                    projection_id=proj.projection_id, adjustments=adjustments
                                )

                    # Add to successful results
                    result["success"] = result.get("success", 0) + 1
                    if "scenario_ids" not in result:
                        result["scenario_ids"] = {}
                    result["scenario_ids"][name] = scenario_id

                except Exception as e:
                    result["failure"] = result.get("failure", 0) + 1
                    if "failed_scenarios" not in result:
                        result["failed_scenarios"] = []
                    result["failed_scenarios"].append(
                        {"name": template.get("name", "Unknown"), "reason": str(e)}
                    )

            # Commit all changes
            self.db.commit()
            return result

        except Exception as e:
            logger.error(f"Error in batch scenario creation: {str(e)}")
            self.db.rollback()
            error_result: BatchResultDict = {
                "success": 0, 
                "failure": len(scenario_templates), 
                "error": str(e),
                "failed_scenarios": [],
                "scenario_ids": {}
            }
            return error_result
