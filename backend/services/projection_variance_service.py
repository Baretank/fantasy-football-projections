from typing import Dict, List, Optional, Tuple, Any, Union, cast
from sqlalchemy.orm import Session
from sqlalchemy import and_
import numpy as np
import pandas as pd
import logging
import uuid
from datetime import datetime
import math

from backend.database.models import Player, Projection, BaseStat, GameStats, Scenario
from backend.services.typing import (
    StatsDict, PlayerDict, safe_float, safe_dict_get, safe_calculate, 
    VarianceCoefficientDict, ConfidenceIntervalDict, IntervalsByConfidenceDict,
    StatVarianceDict, VarianceResultDict, ProjectionRangeDict
)

logger = logging.getLogger(__name__)


class ProjectionVarianceService:
    """Service for calculating projection variance and confidence intervals."""

    def __init__(self, db: Session):
        self.db = db
        # Define base variance coefficients by position and stat
        self.variance_coefficients = {
            "QB": {
                "pass_attempts": 0.12,
                "completions": 0.15,
                "pass_yards": 0.18,
                "pass_td": 0.25,
                "interceptions": 0.35,
                "rush_attempts": 0.30,
                "rush_yards": 0.35,
                "rush_td": 0.50,
            },
            "RB": {
                "rush_attempts": 0.18,
                "rush_yards": 0.22,
                "rush_td": 0.40,
                "targets": 0.25,
                "receptions": 0.28,
                "rec_yards": 0.32,
                "rec_td": 0.45,
            },
            "WR": {
                "targets": 0.20,
                "receptions": 0.25,
                "rec_yards": 0.30,
                "rec_td": 0.45,
                "rush_attempts": 0.50,
                "rush_yards": 0.50,
                "rush_td": 0.70,
            },
            "TE": {
                "targets": 0.25,
                "receptions": 0.30,
                "rec_yards": 0.35,
                "rec_td": 0.50,
                "rush_attempts": 0.80,
                "rush_yards": 0.80,
                "rush_td": 0.95,
            },
        }

        # Confidence interval z-scores
        self.confidence_z = {
            0.50: 0.674,  # 50% confidence interval
            0.80: 1.282,  # 80% confidence interval
            0.90: 1.645,  # 90% confidence interval
            0.95: 1.960,  # 95% confidence interval
            0.99: 2.576,  # 99% confidence interval
        }

    async def calculate_variance(
        self, projection_id: str, adjust_for_games: bool = True, use_historical: bool = True
    ) -> VarianceResultDict:
        """
        Calculate variance for all stats in a projection.

        Args:
            projection_id: The projection to analyze
            adjust_for_games: Whether to adjust variance for projected games
            use_historical: Whether to use historical game-to-game variance

        Returns:
            Dictionary of stat variances and confidence intervals
        """
        try:
            # Get the projection
            projection = self.db.query(Projection).get(projection_id)
            if not projection:
                logger.error(f"Projection {projection_id} not found")
                return {}

            # Get player
            player = projection.player
            if not player:
                logger.error(f"Player not found for projection {projection_id}")
                return {}

            # Build variance model
            if use_historical:
                variance_model = await self._build_historical_variance(
                    player.player_id, projection.season
                )
            else:
                variance_model = cast(VarianceCoefficientDict, 
                    self.variance_coefficients.get(player.position, {}))

            # Calculate confidence intervals for each stat
            result: VarianceResultDict = {}

            # Get all relevant stat fields based on position
            stat_fields = self._get_stat_fields(player.position)

            for stat_name in stat_fields:
                # Get the projected value
                value = getattr(projection, stat_name, None)
                if value is None or safe_float(value) <= 0:
                    continue

                # Get variance coefficient
                default_coef = safe_dict_get(
                    self.variance_coefficients.get(player.position, {}),
                    stat_name, 
                    0.3
                )
                coef = safe_dict_get(variance_model, stat_name, default_coef)

                # Calculate standard deviation
                std_dev = safe_float(value) * safe_float(coef)

                # Adjust for games if needed
                if adjust_for_games and hasattr(projection, "games"):
                    # Variance scales with sqrt(n) for independent events
                    games = safe_float(projection.games)
                    if games > 0:
                        std_dev = std_dev / math.sqrt(games) * math.sqrt(17.0)

                # Calculate confidence intervals
                intervals: IntervalsByConfidenceDict = {}
                for conf_level, z_score in self.confidence_z.items():
                    lower = max(0, safe_float(value) - z_score * std_dev)
                    upper = safe_float(value) + z_score * std_dev
                    intervals[f"{conf_level:.2f}"] = {
                        "lower": round(lower, 2),
                        "upper": round(upper, 2),
                    }

                # Add to results
                result[stat_name] = {
                    "mean": safe_float(value),
                    "std_dev": round(std_dev, 2),
                    "coef_var": round(safe_float(coef), 3),
                    "intervals": intervals,
                }

            # Calculate fantasy point variance
            fp_variance = await self._calculate_fantasy_point_variance(
                projection, result, player.position
            )

            result["half_ppr"] = fp_variance

            return result

        except Exception as e:
            logger.error(f"Error calculating variance: {str(e)}")
            return {}


    async def generate_projection_range(
        self, projection_id: str, confidence: float = 0.80, scenarios: bool = False
    ) -> ProjectionRangeDict:
        """
        Generate low, median, and high projections at the given confidence level.

        Args:
            projection_id: The base projection ID
            confidence: Confidence level (0.0-1.0)
            scenarios: If True, create scenario projections for each range

        Returns:
            Dictionary with low, median, and high projection values
        """
        try:
            # Get variance data
            variance_data = await self.calculate_variance(projection_id)
            if not variance_data:
                return cast(ProjectionRangeDict, {})

            # Get the projection
            projection = self.db.query(Projection).get(projection_id)
            if not projection:
                return cast(ProjectionRangeDict, {})

            # Choose closest confidence level
            conf_level = min(self.confidence_z.keys(), key=lambda x: abs(x - safe_float(confidence)))

            # Create range projections
            projection_range: ProjectionRangeDict = {
                "base": {
                    "projection_id": projection_id,
                    "half_ppr": safe_float(getattr(projection, "half_ppr", 0.0))
                },
                "low": cast(Dict[str, float], {}),
                "median": cast(Dict[str, float], {}),
                "high": cast(Dict[str, float], {}),
            }

            # Get all relevant stat fields
            stat_fields = self._get_stat_fields(projection.player.position)

            # For each stat, get the interval values
            for stat in stat_fields:
                if stat in variance_data:
                    value = getattr(projection, stat, None)
                    if value is None:
                        continue

                    # Get intervals for this confidence level
                    conf_key = f"{conf_level:.2f}"
                    if conf_key in variance_data[stat]["intervals"]:
                        interval = variance_data[stat]["intervals"][conf_key]

                        # Low projection
                        projection_range["low"][stat] = safe_float(interval["lower"])

                        # Median projection (same as base)
                        projection_range["median"][stat] = safe_float(value)

                        # High projection
                        projection_range["high"][stat] = safe_float(interval["upper"])

            # Add fantasy points
            if "half_ppr" in variance_data:
                conf_key = f"{conf_level:.2f}"
                if conf_key in variance_data["half_ppr"]["intervals"]:
                    interval = variance_data["half_ppr"]["intervals"][conf_key]
                    projection_range["low"]["half_ppr"] = safe_float(interval["lower"])
                    projection_range["median"]["half_ppr"] = safe_float(getattr(projection, "half_ppr", 0.0))
                    projection_range["high"]["half_ppr"] = safe_float(interval["upper"])

            # Create scenario projections if requested
            if scenarios:
                scenario_ids = await self._create_range_scenarios(
                    projection, projection_range, confidence
                )
                if scenario_ids:
                    projection_range["scenario_ids"] = scenario_ids

            return projection_range

        except Exception as e:
            logger.error(f"Error generating projection range: {str(e)}")
            return cast(ProjectionRangeDict, {})

    async def _build_historical_variance(self, player_id: str, season: int) -> VarianceCoefficientDict:
        """
        Build variance coefficients using historical game-to-game variance.
        """
        try:
            # Get player
            player = self.db.query(Player).get(player_id)
            if not player:
                return {}

            # Get game stats for previous seasons (up to 3 years)
            game_stats = (
                self.db.query(GameStats)
                .filter(
                    and_(
                        GameStats.player_id == player_id,
                        GameStats.season >= season - 3,
                        GameStats.season < season,
                    )
                )
                .all()
            )

            if not game_stats:
                # No historical data, use default coefficients
                return cast(VarianceCoefficientDict, self.variance_coefficients.get(player.position, {}))

            # Build variance model based on position
            variance_model: VarianceCoefficientDict = {}

            if player.position == "QB":
                # Calculate variance for QB stats
                pass_attempts = [
                    float(g.stats.get("att", 0)) for g in game_stats if "att" in g.stats
                ]
                completions = [float(g.stats.get("cmp", 0)) for g in game_stats if "cmp" in g.stats]
                pass_yards = [
                    float(g.stats.get("pass_yds", 0)) for g in game_stats if "pass_yds" in g.stats
                ]
                pass_td = [
                    float(g.stats.get("pass_td", 0)) for g in game_stats if "pass_td" in g.stats
                ]
                interceptions = [
                    float(g.stats.get("int", 0)) for g in game_stats if "int" in g.stats
                ]
                rush_attempts = [
                    float(g.stats.get("rush_att", 0)) for g in game_stats if "rush_att" in g.stats
                ]
                rush_yards = [
                    float(g.stats.get("rush_yds", 0)) for g in game_stats if "rush_yds" in g.stats
                ]
                rush_td = [
                    float(g.stats.get("rush_td", 0)) for g in game_stats if "rush_td" in g.stats
                ]

                # Calculate coefficient of variation (std_dev / mean) for each stat if we have enough data
                if pass_attempts and len(pass_attempts) >= 8:
                    variance_model["pass_attempts"] = np.std(pass_attempts) / max(
                        1, np.mean(pass_attempts)
                    )
                if completions and len(completions) >= 8:
                    variance_model["completions"] = np.std(completions) / max(
                        1, np.mean(completions)
                    )
                if pass_yards and len(pass_yards) >= 8:
                    variance_model["pass_yards"] = np.std(pass_yards) / max(1, np.mean(pass_yards))
                if pass_td and len(pass_td) >= 8:
                    variance_model["pass_td"] = np.std(pass_td) / max(1, np.mean(pass_td))
                if interceptions and len(interceptions) >= 8:
                    variance_model["interceptions"] = np.std(interceptions) / max(
                        1, np.mean(interceptions)
                    )
                if rush_attempts and len(rush_attempts) >= 8:
                    variance_model["rush_attempts"] = np.std(rush_attempts) / max(
                        1, np.mean(rush_attempts)
                    )
                if rush_yards and len(rush_yards) >= 8:
                    variance_model["rush_yards"] = np.std(rush_yards) / max(1, np.mean(rush_yards))
                if rush_td and len(rush_td) >= 8:
                    variance_model["rush_td"] = np.std(rush_td) / max(1, np.mean(rush_td))

            elif player.position in ["RB", "WR", "TE"]:
                # Calculate variance for RB/WR/TE stats
                rush_attempts = [
                    float(g.stats.get("rush_att", 0)) for g in game_stats if "rush_att" in g.stats
                ]
                rush_yards = [
                    float(g.stats.get("rush_yds", 0)) for g in game_stats if "rush_yds" in g.stats
                ]
                rush_td = [
                    float(g.stats.get("rush_td", 0)) for g in game_stats if "rush_td" in g.stats
                ]
                targets = [float(g.stats.get("tgt", 0)) for g in game_stats if "tgt" in g.stats]
                receptions = [float(g.stats.get("rec", 0)) for g in game_stats if "rec" in g.stats]
                rec_yards = [
                    float(g.stats.get("rec_yds", 0)) for g in game_stats if "rec_yds" in g.stats
                ]
                rec_td = [
                    float(g.stats.get("rec_td", 0)) for g in game_stats if "rec_td" in g.stats
                ]

                # Calculate coefficient of variation for each stat if we have enough data
                if rush_attempts and len(rush_attempts) >= 8:
                    variance_model["rush_attempts"] = np.std(rush_attempts) / max(
                        1, np.mean(rush_attempts)
                    )
                if rush_yards and len(rush_yards) >= 8:
                    variance_model["rush_yards"] = np.std(rush_yards) / max(1, np.mean(rush_yards))
                if rush_td and len(rush_td) >= 8:
                    variance_model["rush_td"] = np.std(rush_td) / max(1, np.mean(rush_td))
                if targets and len(targets) >= 8:
                    variance_model["targets"] = np.std(targets) / max(1, np.mean(targets))
                if receptions and len(receptions) >= 8:
                    variance_model["receptions"] = np.std(receptions) / max(1, np.mean(receptions))
                if rec_yards and len(rec_yards) >= 8:
                    variance_model["rec_yards"] = np.std(rec_yards) / max(1, np.mean(rec_yards))
                if rec_td and len(rec_td) >= 8:
                    variance_model["rec_td"] = np.std(rec_td) / max(1, np.mean(rec_td))

            # Fill in gaps with default coefficients
            default_coefs = self.variance_coefficients.get(player.position, {})
            for stat, coef in default_coefs.items():
                if stat not in variance_model:
                    variance_model[stat] = coef

            return variance_model

        except Exception as e:
            logger.error(f"Error building historical variance: {str(e)}")
            return cast(VarianceCoefficientDict, self.variance_coefficients.get(player.position, {}))

    async def _calculate_fantasy_point_variance(
        self, projection: Projection, stat_variances: VarianceResultDict, position: str
    ) -> StatVarianceDict:
        """
        Calculate variance for fantasy points based on component stat variances.
        This accounts for correlations between stats.
        """
        # Define fantasy point weights in half PPR
        fp_weights = {
            "pass_yards": 0.04,  # 1 per 25 yards
            "pass_td": 4.0,
            "interceptions": -2.0,
            "rush_yards": 0.1,  # 1 per 10 yards
            "rush_td": 6.0,
            "receptions": 0.5,  # Half PPR
            "rec_yards": 0.1,  # 1 per 10 yards
            "rec_td": 6.0,
        }

        # Base fantasy point calculation
        fp_base = projection.half_ppr

        # Calculate variance components and correlations
        variance_sum = 0.0

        # Define correlation matrix based on position
        correlations = self._get_stat_correlations(position)

        # Add variance contribution from each stat
        for stat1, weight1 in fp_weights.items():
            if stat1 not in stat_variances:
                continue

            var1 = stat_variances[stat1]["std_dev"] ** 2
            variance_sum += (weight1**2) * var1

            # Add covariance terms
            for stat2, weight2 in fp_weights.items():
                if stat1 >= stat2 or stat2 not in stat_variances:
                    continue

                # Get correlation between stat1 and stat2
                corr = correlations.get((stat1, stat2), 0.0)

                # Calculate covariance term
                std_dev1 = safe_float(stat_variances[stat1]["std_dev"])
                std_dev2 = safe_float(stat_variances[stat2]["std_dev"])
                covariance = corr * std_dev1 * std_dev2

                # Add to variance sum (twice for each pair)
                variance_sum += 2 * safe_float(weight1) * safe_float(weight2) * covariance

        # Calculate standard deviation of fantasy points
        fp_std_dev = math.sqrt(max(0, variance_sum))

        # Calculate confidence intervals
        intervals: IntervalsByConfidenceDict = {}
        for conf_level, z_score in self.confidence_z.items():
            lower = max(0, safe_float(fp_base) - safe_float(z_score) * fp_std_dev)
            upper = safe_float(fp_base) + safe_float(z_score) * fp_std_dev
            intervals[f"{conf_level:.2f}"] = {
                "lower": round(lower, 2), 
                "upper": round(upper, 2)
            }

        # Return variance info
        return {
            "mean": safe_float(fp_base),
            "std_dev": round(fp_std_dev, 2),
            "coef_var": round(safe_calculate(fp_std_dev, fp_base, 0.0), 3),
            "intervals": intervals,
        }

    async def _create_range_scenarios(
        self,
        projection: Projection,
        projection_range: ProjectionRangeDict,
        confidence: float,
    ) -> Dict[str, str]:
        """
        Create scenario projections for low, median, and high ranges.
        """
        try:
            # Create description with confidence level
            conf_pct = int(confidence * 100)
            description = f"{conf_pct}% confidence interval range"

            # Create scenarios
            scenario_ids = {}

            # Create low scenario
            low_scenario = Scenario(
                scenario_id=str(uuid.uuid4()),
                name=f"{projection.player.name} Low Projection",
                description=f"Low-end projection ({description})",
                base_scenario_id=projection.scenario_id,
            )
            self.db.add(low_scenario)
            self.db.flush()

            # Create low projection as copy of base with adjusted values
            low_proj = self._copy_projection(projection)
            low_proj.scenario_id = low_scenario.scenario_id

            # Update values from range
            for stat, value in projection_range["low"].items():
                if hasattr(low_proj, stat):
                    setattr(low_proj, stat, value)

            self.db.add(low_proj)
            scenario_ids["low"] = low_scenario.scenario_id

            # Create high scenario
            high_scenario = Scenario(
                scenario_id=str(uuid.uuid4()),
                name=f"{projection.player.name} High Projection",
                description=f"High-end projection ({description})",
                base_scenario_id=projection.scenario_id,
            )
            self.db.add(high_scenario)
            self.db.flush()

            # Create high projection
            high_proj = self._copy_projection(projection)
            high_proj.scenario_id = high_scenario.scenario_id

            # Update values from range
            for stat, value in projection_range["high"].items():
                if hasattr(high_proj, stat):
                    setattr(high_proj, stat, value)

            self.db.add(high_proj)
            scenario_ids["high"] = high_scenario.scenario_id

            # Commit changes
            self.db.commit()

            return scenario_ids

        except Exception as e:
            logger.error(f"Error creating range scenarios: {str(e)}")
            self.db.rollback()
            return {}

    def _copy_projection(self, projection: Projection) -> Projection:
        """Create a copy of a projection with a new ID."""
        return Projection(
            projection_id=str(uuid.uuid4()),
            player_id=projection.player_id,
            season=projection.season,
            games=projection.games,
            half_ppr=projection.half_ppr,
            pass_attempts=projection.pass_attempts,
            completions=projection.completions,
            pass_yards=projection.pass_yards,
            pass_td=projection.pass_td,
            interceptions=projection.interceptions,
            rush_attempts=projection.rush_attempts,
            rush_yards=projection.rush_yards,
            rush_td=projection.rush_td,
            targets=projection.targets,
            receptions=projection.receptions,
            rec_yards=projection.rec_yards,
            rec_td=projection.rec_td,
            snap_share=projection.snap_share,
            target_share=projection.target_share,
            rush_share=projection.rush_share,
            redzone_share=projection.redzone_share,
            comp_pct=projection.comp_pct,
            yards_per_att=projection.yards_per_att,
            yards_per_carry=projection.yards_per_carry,
            catch_pct=projection.catch_pct,
            yards_per_target=projection.yards_per_target,
        )

    def _get_stat_fields(self, position: str) -> List[str]:
        """Get the relevant stat fields for a position."""
        base_fields = ["games", "half_ppr"]

        if position == "QB":
            return base_fields + [
                "pass_attempts",
                "completions",
                "pass_yards",
                "pass_td",
                "interceptions",
                "rush_attempts",
                "rush_yards",
                "rush_td",
            ]
        elif position in ["RB", "WR", "TE"]:
            fields = base_fields + [
                "rush_attempts",
                "rush_yards",
                "rush_td",
                "targets",
                "receptions",
                "rec_yards",
                "rec_td",
            ]

            # Add usage metrics if relevant
            if position in ["WR", "TE"]:
                fields.extend(["target_share", "snap_share"])
            if position == "RB":
                fields.extend(["rush_share"])

            return fields

        return base_fields

    def _get_stat_correlations(self, position: str) -> Dict[Tuple[str, str], float]:
        """
        Get correlation coefficients between stats for a position.
        These values are empirically derived from historical data.
        """
        if position == "QB":
            return {
                ("pass_attempts", "completions"): 0.97,
                ("pass_attempts", "pass_yards"): 0.92,
                ("pass_attempts", "pass_td"): 0.75,
                ("pass_attempts", "interceptions"): 0.65,
                ("completions", "pass_yards"): 0.94,
                ("completions", "pass_td"): 0.78,
                ("pass_yards", "pass_td"): 0.80,
                ("rush_yards", "rush_td"): 0.60,
                ("rush_attempts", "rush_yards"): 0.95,
                ("rush_attempts", "rush_td"): 0.55,
            }
        elif position == "RB":
            return {
                ("rush_attempts", "rush_yards"): 0.98,
                ("rush_attempts", "rush_td"): 0.75,
                ("rush_yards", "rush_td"): 0.70,
                ("targets", "receptions"): 0.95,
                ("receptions", "rec_yards"): 0.97,
                ("receptions", "rec_td"): 0.60,
                ("rec_yards", "rec_td"): 0.65,
                ("rush_attempts", "targets"): -0.20,  # Slight negative correlation
                ("rush_yards", "rec_yards"): -0.15,
            }
        elif position in ["WR", "TE"]:
            return {
                ("targets", "receptions"): 0.97,
                ("targets", "rec_yards"): 0.92,
                ("targets", "rec_td"): 0.75,
                ("receptions", "rec_yards"): 0.95,
                ("receptions", "rec_td"): 0.70,
                ("rec_yards", "rec_td"): 0.75,
                ("rush_attempts", "rush_yards"): 0.90,
                ("rush_yards", "rush_td"): 0.60,
            }

        return {}
