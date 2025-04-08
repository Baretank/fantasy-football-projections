from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_
import asyncio
import pandas as pd
import numpy as np
import logging
import uuid
from datetime import datetime
import uuid

from backend.database.models import Player, BaseStat, TeamStat, GameStats, ImportLog
from backend.services.adapters.nfl_data_py_adapter import NFLDataPyAdapter
from backend.services.adapters.nfl_api_adapter import NFLApiAdapter

logger = logging.getLogger(__name__)

class NFLDataImportService:
    """
    Service for importing NFL data from multiple sources.
    
    This service coordinates data import from nfl-data-py and the NFL API,
    processes the data, and stores it in the database.
    """
    
    def __init__(self, db: Session, logger=None):
        """
        Initialize the NFL data import service.
        
        Args:
            db: SQLAlchemy database session
            logger: Optional logger instance
        """
        self.db = db
        self.logger = logger or logging.getLogger(__name__)
        self.nfl_data_adapter = NFLDataPyAdapter()
        self.nfl_api_adapter = NFLApiAdapter()
        
        # Metrics tracking
        self.metrics = {
            "requests_made": 0,
            "rate_limits_hit": 0,
            "errors": 0,
            "players_processed": 0,
            "game_stats_processed": 0,
            "start_time": None,
            "end_time": None
        }
        
        # Position-specific stat mappings
        self.stat_mappings = {
            'QB': {
                'pass_attempts': 'attempts',
                'completions': 'completions',
                'pass_yards': 'passing_yards',
                'pass_td': 'passing_tds',
                'interceptions': 'interceptions',
                'rush_attempts': 'rushing_attempts',
                'rush_yards': 'rushing_yards',
                'rush_td': 'rushing_tds'
            },
            'RB': {
                'rush_attempts': 'rushing_attempts',
                'rush_yards': 'rushing_yards',
                'rush_td': 'rushing_tds',
                'targets': 'targets',
                'receptions': 'receptions',
                'rec_yards': 'receiving_yards',
                'rec_td': 'receiving_tds'
            },
            'WR': {
                'targets': 'targets',
                'receptions': 'receptions',
                'rec_yards': 'receiving_yards',
                'rec_td': 'receiving_tds',
                'rush_attempts': 'rushing_attempts',
                'rush_yards': 'rushing_yards',
                'rush_td': 'rushing_tds'
            },
            'TE': {
                'targets': 'targets',
                'receptions': 'receptions',
                'rec_yards': 'receiving_yards',
                'rec_td': 'receiving_tds'
            }
        }
    
    def start_monitoring(self):
        """Start the monitoring session."""
        self.metrics["start_time"] = datetime.now()
        self.logger.info(f"Started import operation at {self.metrics['start_time']}")
        
    def end_monitoring(self):
        """End the monitoring session and report metrics."""
        self.metrics["end_time"] = datetime.now()
        duration = (self.metrics["end_time"] - self.metrics["start_time"]).total_seconds()
        
        self.logger.info(f"Import operation completed in {duration:.2f} seconds")
        self.logger.info(f"Metrics: {self.metrics}")
        
        # Log detailed stats
        if self.metrics["requests_made"] > 0:
            error_rate = self.metrics["errors"] / self.metrics["requests_made"] * 100
            self.logger.info(f"Error rate: {error_rate:.2f}%")
            
        if self.metrics["rate_limits_hit"] > 0:
            self.logger.warning(f"Rate limit hit {self.metrics['rate_limits_hit']} times")
            
        return {
            "duration_seconds": duration,
            "metrics": self.metrics
        }
        
    async def import_season(self, season: int) -> Dict[str, Any]:
        """
        Import complete season data from all sources.
        
        Args:
            season: NFL season year (e.g., 2023)
            
        Returns:
            Dictionary containing import results
        """
        self.start_monitoring()
        
        try:
            # Log the start of import
            self._log_import("season_import_start", "info", f"Starting import for season {season}")
            
            # Step 1: Import player data
            self.logger.info(f"Step 1: Importing player data for season {season}")
            player_results = await self.import_players(season)
            
            # Step 2: Import weekly stats
            self.logger.info(f"Step 2: Importing weekly stats for season {season}")
            weekly_results = await self.import_weekly_stats(season)
            
            # Step 3: Import team stats
            self.logger.info(f"Step 3: Importing team stats for season {season}")
            team_results = await self.import_team_stats(season)
            
            # Step 4: Calculate season totals
            self.logger.info(f"Step 4: Calculating season totals for season {season}")
            totals_results = await self.calculate_season_totals(season)
            
            # Step 5: Validate and fix data
            self.logger.info(f"Step 5: Validating data for season {season}")
            validation_results = await self.validate_data(season)
            
            # Log successful completion
            self._log_import("season_import_complete", "success", 
                           f"Completed import for season {season}", 
                           {
                               "player_results": player_results,
                               "weekly_results": weekly_results,
                               "team_results": team_results,
                               "totals_results": totals_results,
                               "validation_results": validation_results
                           })
            
            # Return combined results
            results = {
                "players": player_results,
                "weekly_stats": weekly_results,
                "team_stats": team_results,
                "season_totals": totals_results,
                "validation": validation_results
            }
            
            return {**results, **self.end_monitoring()}
            
        except Exception as e:
            # Log error and end monitoring
            self.metrics["errors"] += 1
            self.logger.error(f"Error importing season {season}: {str(e)}")
            self._log_import("season_import_error", "error", 
                           f"Error importing season {season}: {str(e)}")
            
            # Re-raise the exception after logging
            raise
        finally:
            # Close API adapter session
            await self.nfl_api_adapter.close()
    
    async def import_players(self, season: int, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Import player data for the specified season.
        
        Args:
            season: NFL season year (e.g., 2023)
            limit: Optional limit of players to import (for testing purposes)
            
        Returns:
            Dictionary containing import results
        """
        try:
            # Get player data from nfl-data-py
            self.logger.info(f"Importing players for season {season}")
            player_data = await self.nfl_data_adapter.get_players(season)
            self.metrics["requests_made"] += 1
            
            # Apply limit if specified (for testing with small batches)
            if limit:
                self.logger.info(f"Test mode: limiting import to {limit} players")
                player_data = player_data.head(limit)
            
            # Process and transform data
            players_added = 0
            players_updated = 0
            
            for _, row in player_data.iterrows():
                # Use GSIS ID if available, otherwise use other unique identifiers
                player_id = None
                if not pd.isna(row.get('gsis_id')):
                    player_id = row['gsis_id']
                elif not pd.isna(row.get('smart_id')):
                    player_id = row['smart_id']
                elif not pd.isna(row.get('esb_id')):
                    player_id = row['esb_id']
                else:
                    # If no ID is available, generate a unique ID
                    self.logger.warning(f"No player ID found for {row.get('display_name', 'Unknown')}. Skipping.")
                    continue
                    
                # Check if player exists
                existing_player = self.db.query(Player).filter(
                    Player.player_id == player_id
                ).first()
                
                # Convert height
                height_inches = None
                if not pd.isna(row.get('height')) and isinstance(row['height'], str) and '-' in row['height']:
                    feet, inches = row['height'].split('-')
                    height_inches = int(feet) * 12 + int(inches)
                
                # Get team information - team_abbr is the field in the API
                team = row.get('team_abbr') if not pd.isna(row.get('team_abbr')) else "UNK"
                
                # Prepare player data with default for status field to avoid NULL constraint error
                player_data = {
                    "player_id": player_id,
                    "name": row['display_name'] if not pd.isna(row.get('display_name')) else "Unknown",
                    "position": row['position'] if not pd.isna(row.get('position')) else "UNK",
                    "team": team,
                    "status": row.get('status') if not pd.isna(row.get('status')) else "Unknown",
                    "height": height_inches,
                    "weight": row.get('weight') if not pd.isna(row.get('weight')) else None
                }
                
                if existing_player:
                    # Update existing player
                    for key, value in player_data.items():
                        setattr(existing_player, key, value)
                    players_updated += 1
                else:
                    # Create new player
                    new_player = Player(**player_data)
                    self.db.add(new_player)
                    players_added += 1
                
                self.metrics["players_processed"] += 1
                
                # Commit every 100 players to avoid memory issues with large datasets
                if self.metrics["players_processed"] % 100 == 0:
                    self.db.commit()
            
            # Final commit
            self.db.commit()
            
            results = {
                "players_added": players_added,
                "players_updated": players_updated,
                "total_processed": players_added + players_updated
            }
            
            # Log success
            self._log_import("player_import", "success", 
                           f"Successfully imported players for season {season}", 
                           results)
            
            return results
            
        except Exception as e:
            self.db.rollback()
            self.metrics["errors"] += 1
            self.logger.error(f"Error importing player data: {str(e)}")
            import traceback
            self.logger.debug(f"Stack trace: {traceback.format_exc()}")
            self._log_import("player_import", "error", 
                           f"Error importing player data: {str(e)}")
            raise Exception(f"Error importing player data: {str(e)}")
    
    async def import_weekly_stats(self, season: int, player_limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Import weekly statistics for the specified season.
        
        Args:
            season: NFL season year (e.g., 2023)
            player_limit: Optional limit on number of players to process (for testing)
            
        Returns:
            Dictionary containing import results
        """
        try:
            self.logger.info(f"Importing weekly stats for season {season}")
            weekly_data = await self.nfl_data_adapter.get_weekly_stats(season)
            self.metrics["requests_made"] += 1
            
            # Get game schedules for additional context
            schedules = await self.nfl_data_adapter.get_schedules(season)
            self.metrics["requests_made"] += 1
            
            # Create a lookup for game information
            game_info = {}
            for _, game in schedules.iterrows():
                if not pd.isna(game.get('game_id')):
                    week = game.get('week', 0)
                    game_info[f"{game['home_team']}_{week}"] = {
                        'opponent': game.get('away_team'),
                        'location': 'home',
                        'result': 'W' if game.get('home_score', 0) > game.get('away_score', 0) else 'L',
                        'team_score': game.get('home_score', 0),
                        'opponent_score': game.get('away_score', 0)
                    }
                    game_info[f"{game['away_team']}_{week}"] = {
                        'opponent': game.get('home_team'),
                        'location': 'away',
                        'result': 'W' if game.get('away_score', 0) > game.get('home_score', 0) else 'L',
                        'team_score': game.get('away_score', 0),
                        'opponent_score': game.get('home_score', 0)
                    }
            
            # Process and transform data
            stats_added = 0
            errors = 0
            
            # If player_limit is specified, get only limited players
            if player_limit:
                self.logger.info(f"Limiting weekly stats import to {player_limit} players")
                players = self.db.query(Player).filter(
                    Player.position.in_(["QB", "RB", "WR", "TE"])
                ).limit(player_limit).all()
                player_ids = [p.player_id for p in players]
                self.logger.info(f"Selected {len(player_ids)} players for limited import")
                # Filter weekly_data to only include these players
                weekly_data = weekly_data[weekly_data['player_id'].isin(player_ids)]
            
            for _, row in weekly_data.iterrows():
                # Skip rows with missing player_id
                if pd.isna(row.get('player_id')):
                    continue
                    
                # Check if player exists
                player = self.db.query(Player).filter(
                    Player.player_id == row['player_id']
                ).first()
                
                if not player:
                    continue  # Skip if player not in database
                    
                # Extract week and team
                week = int(row['week']) if not pd.isna(row.get('week')) else 0
                team = row.get('recent_team') if not pd.isna(row.get('recent_team')) else player.team
                
                # Check if weekly stat already exists
                existing_stat = self.db.query(GameStats).filter(
                    GameStats.player_id == row['player_id'],
                    GameStats.season == season,
                    GameStats.week == week
                ).first()
                
                if existing_stat:
                    continue  # Skip if already imported
                
                # Get game context data
                game_key = f"{team}_{week}"
                game_context = game_info.get(game_key, {
                    'opponent': "UNK",
                    'location': "home",
                    'result': "U",
                    'team_score': 0,
                    'opponent_score': 0
                })
                
                # Use position-specific stat mappings
                position = player.position
                stats = {}
                
                # Import all available stat columns for this position
                for our_name, nfl_name in self.stat_mappings.get(position, {}).items():
                    if nfl_name in row and not pd.isna(row[nfl_name]):
                        stats[our_name] = float(row[nfl_name])
                
                # Create new game stat
                try:
                    game_stat = GameStats(
                        game_stat_id=str(uuid.uuid4()),
                        player_id=row['player_id'],
                        season=season,
                        week=week,
                        opponent=game_context['opponent'],
                        game_location=game_context['location'],
                        result=game_context['result'],
                        team_score=game_context['team_score'],
                        opponent_score=game_context['opponent_score'],
                        stats=stats
                    )
                    
                    self.db.add(game_stat)
                    stats_added += 1
                    self.metrics["game_stats_processed"] += 1
                    
                    # Commit in batches to avoid memory issues
                    if stats_added % 100 == 0:
                        self.db.commit()
                        
                except Exception as e:
                    self.logger.error(f"Error processing game stat for {player.name} week {week}: {str(e)}")
                    import traceback
                    self.logger.debug(f"Stack trace: {traceback.format_exc()}")
                    errors += 1
            
            # Final commit
            self.db.commit()
            
            results = {
                "weekly_stats_added": stats_added,
                "errors": errors
            }
            
            # Log success
            self._log_import("weekly_stats_import", "success", 
                           f"Successfully imported weekly stats for season {season}", 
                           results)
            
            return results
            
        except Exception as e:
            self.db.rollback()
            self.metrics["errors"] += 1
            self.logger.error(f"Error importing weekly stats: {str(e)}")
            import traceback
            self.logger.debug(f"Stack trace: {traceback.format_exc()}")
            self._log_import("weekly_stats_import", "error", 
                           f"Error importing weekly stats: {str(e)}")
            raise Exception(f"Error importing weekly stats: {str(e)}")
    
    async def import_team_stats(self, season: int) -> Dict[str, Any]:
        """
        Import team statistics for the specified season.
        
        Args:
            season: NFL season year (e.g., 2023)
            
        Returns:
            Dictionary containing import results
        """
        try:
            self.logger.info(f"Importing team stats for season {season}")
            team_data = await self.nfl_data_adapter.get_team_stats(season)
            self.metrics["requests_made"] += 1
            
            teams_processed = 0
            
            for _, row in team_data.iterrows():
                team_abbr = row.get('team')
                if pd.isna(team_abbr):
                    continue
                    
                # Check if team stats already exist
                existing_stats = self.db.query(TeamStat).filter(
                    TeamStat.team == team_abbr,
                    TeamStat.season == season
                ).first()
                
                # The data already contains the calculated fields from our adapter
                # Just prepare team stat data for our model
                team_stat_data = {
                    "team": team_abbr,
                    "season": season,
                    "plays": float(row.get('plays', 0)) if not pd.isna(row.get('plays')) else 0,
                    "pass_percentage": float(row.get('pass_percentage', 0)) if not pd.isna(row.get('pass_percentage')) else 0,
                    "pass_attempts": float(row.get('pass_attempts', 0)) if not pd.isna(row.get('pass_attempts')) else 0,
                    "pass_yards": float(row.get('pass_yards', 0)) if not pd.isna(row.get('pass_yards')) else 0,
                    "pass_td": float(row.get('pass_td', 0)) if not pd.isna(row.get('pass_td')) else 0,
                    "pass_td_rate": float(row.get('pass_td_rate', 0)) if not pd.isna(row.get('pass_td_rate')) else 0,
                    "rush_attempts": float(row.get('rush_attempts', 0)) if not pd.isna(row.get('rush_attempts')) else 0,
                    "rush_yards": float(row.get('rush_yards', 0)) if not pd.isna(row.get('rush_yards')) else 0,
                    "rush_td": float(row.get('rush_td', 0)) if not pd.isna(row.get('rush_td')) else 0,
                    "rush_yards_per_carry": float(row.get('rush_yards_per_carry', 0)) if not pd.isna(row.get('rush_yards_per_carry')) else 0,
                    "targets": float(row.get('targets', 0)) if not pd.isna(row.get('targets')) else 0,
                    "receptions": float(row.get('receptions', 0)) if not pd.isna(row.get('receptions')) else 0,
                    "rec_yards": float(row.get('rec_yards', 0)) if not pd.isna(row.get('rec_yards')) else 0,
                    "rec_td": float(row.get('rec_td', 0)) if not pd.isna(row.get('rec_td')) else 0,
                    "rank": int(row.get('rank', 0)) if not pd.isna(row.get('rank')) else 0
                }
                
                if existing_stats:
                    # Update existing stats
                    for key, value in team_stat_data.items():
                        setattr(existing_stats, key, value)
                else:
                    # Create new team stat
                    new_team_stat = TeamStat(
                        team_stat_id=str(uuid.uuid4()),
                        **team_stat_data
                    )
                    self.db.add(new_team_stat)
                    
                teams_processed += 1
            
            self.db.commit()
            
            results = {
                "teams_processed": teams_processed
            }
            
            # Log success
            self._log_import("team_stats_import", "success", 
                           f"Successfully imported team stats for season {season}", 
                           results)
            
            return results
            
        except Exception as e:
            self.db.rollback()
            self.metrics["errors"] += 1
            self.logger.error(f"Error importing team stats: {str(e)}")
            self._log_import("team_stats_import", "error", 
                           f"Error importing team stats: {str(e)}")
            raise Exception(f"Error importing team stats: {str(e)}")
    
    async def calculate_season_totals(self, season: int) -> Dict[str, Any]:
        """
        Calculate season totals from weekly data.
        
        Args:
            season: NFL season year (e.g., 2023)
            
        Returns:
            Dictionary containing calculation results
        """
        try:
            self.logger.info(f"Calculating season totals for {season}")
            
            # Get all players with game stats for this season
            players = self.db.query(Player).join(
                GameStats, Player.player_id == GameStats.player_id
            ).filter(
                GameStats.season == season
            ).distinct().all()
            
            self.logger.info(f"Found {len(players)} players with game stats for season {season}")
            
            totals_created = 0
            
            for player in players:
                # Get all game stats for this player and season
                game_stats = self.db.query(GameStats).filter(
                    GameStats.player_id == player.player_id,
                    GameStats.season == season
                ).all()
                
                if not game_stats:
                    continue
                    
                # Count games and aggregate stats
                games_played = len(game_stats)
                position = player.position
                
                # Initialize totals dictionary
                totals = {}
                
                # Aggregate stats based on position
                if position == "QB":
                    # Aggregate QB stats
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
                    
                    # Calculate efficiency metrics
                    if "pass_attempts" in totals and totals["pass_attempts"] > 0:
                        totals["comp_pct"] = round(totals["completions"] / totals["pass_attempts"] * 100, 1)
                        totals["yards_per_att"] = round(totals["pass_yards"] / totals["pass_attempts"], 1)
                        totals["pass_td_rate"] = round(totals["pass_td"] / totals["pass_attempts"] * 100, 1)
                        totals["int_rate"] = round(totals["interceptions"] / totals["pass_attempts"] * 100, 1)
                        
                elif position == "RB":
                    # Aggregate RB stats
                    totals = {
                        "rush_attempts": sum(g.stats.get("rush_attempts", 0) for g in game_stats),
                        "rush_yards": sum(g.stats.get("rush_yards", 0) for g in game_stats),
                        "rush_td": sum(g.stats.get("rush_td", 0) for g in game_stats),
                        "targets": sum(g.stats.get("targets", 0) for g in game_stats),
                        "receptions": sum(g.stats.get("receptions", 0) for g in game_stats),
                        "rec_yards": sum(g.stats.get("rec_yards", 0) for g in game_stats),
                        "rec_td": sum(g.stats.get("rec_td", 0) for g in game_stats),
                    }
                    
                    # Calculate efficiency metrics
                    if "rush_attempts" in totals and totals["rush_attempts"] > 0:
                        totals["yards_per_carry"] = round(totals["rush_yards"] / totals["rush_attempts"], 1)
                    if "targets" in totals and totals["targets"] > 0:
                        totals["catch_rate"] = round(totals["receptions"] / totals["targets"] * 100, 1)
                    
                else:  # WR and TE
                    # Aggregate WR/TE stats
                    totals = {
                        "targets": sum(g.stats.get("targets", 0) for g in game_stats),
                        "receptions": sum(g.stats.get("receptions", 0) for g in game_stats),
                        "rec_yards": sum(g.stats.get("rec_yards", 0) for g in game_stats),
                        "rec_td": sum(g.stats.get("rec_td", 0) for g in game_stats),
                    }
                    
                    # Add rushing stats for WRs
                    if position == "WR":
                        totals.update({
                            "rush_attempts": sum(g.stats.get("rush_attempts", 0) for g in game_stats),
                            "rush_yards": sum(g.stats.get("rush_yards", 0) for g in game_stats),
                            "rush_td": sum(g.stats.get("rush_td", 0) for g in game_stats),
                        })
                    
                    # Calculate efficiency metrics
                    if "targets" in totals and totals["targets"] > 0:
                        totals["catch_rate"] = round(totals["receptions"] / totals["targets"] * 100, 1)
                        totals["yards_per_target"] = round(totals["rec_yards"] / totals["targets"], 1)
                    if "receptions" in totals and totals["receptions"] > 0:
                        totals["yards_per_reception"] = round(totals["rec_yards"] / totals["receptions"], 1)
                
                # Calculate half-PPR fantasy points
                fantasy_points = self._calculate_fantasy_points(totals, position)
                
                # Create or update BaseStat records
                existing_stats = self._get_player_base_stats(player.player_id, season)
                
                # Update base stats in database
                # Check if existing_stats has elements
                if existing_stats and len(existing_stats) > 0:
                    # Update existing base stats
                    for stat_name, value in totals.items():
                        self._update_base_stat(existing_stats, stat_name, value)
                        
                    # Update games and half_ppr
                    games_stat = next((s for s in existing_stats if s.stat_type == "games"), None)
                    if games_stat:
                        games_stat.value = games_played
                    else:
                        self._create_base_stat(player.player_id, season, "games", games_played)
                        
                    half_ppr_stat = next((s for s in existing_stats if s.stat_type == "half_ppr"), None)
                    if half_ppr_stat:
                        half_ppr_stat.value = fantasy_points
                    else:
                        self._create_base_stat(player.player_id, season, "half_ppr", fantasy_points)
                else:
                    # Create new base stats for all values
                    for stat_name, value in totals.items():
                        self._create_base_stat(player.player_id, season, stat_name, value)
                    
                    # Add games and half_ppr
                    self._create_base_stat(player.player_id, season, "games", games_played)
                    self._create_base_stat(player.player_id, season, "half_ppr", fantasy_points)
                    
                    totals_created += 1
            
            # Commit changes
            self.db.commit()
            
            results = {
                "totals_created": totals_created,
                "players_processed": len(players)
            }
            
            # Log success
            self._log_import("season_totals_calculation", "success", 
                           f"Successfully calculated season totals for {season}", 
                           results)
            
            return results
            
        except Exception as e:
            self.db.rollback()
            self.metrics["errors"] += 1
            self.logger.error(f"Error calculating season totals: {str(e)}")
            self._log_import("season_totals_calculation", "error", 
                           f"Error calculating season totals: {str(e)}")
            raise Exception(f"Error calculating season totals: {str(e)}")
    
    async def validate_data(self, season: int) -> Dict[str, Any]:
        """
        Validate imported data for consistency and completeness.
        
        Args:
            season: NFL season year (e.g., 2023)
            
        Returns:
            Dictionary containing validation results
        """
        try:
            self.logger.info(f"Validating data for season {season}")
            issues_found = 0
            issues_fixed = 0
            
            # Validation 1: Verify player count matches between game stats and base stats
            player_with_game_stats = self.db.query(Player).join(
                GameStats, Player.player_id == GameStats.player_id
            ).filter(
                GameStats.season == season
            ).distinct().count()
            
            player_with_base_stats = self.db.query(Player).join(
                BaseStat, Player.player_id == BaseStat.player_id
            ).filter(
                BaseStat.season == season
            ).distinct().count()
            
            if player_with_game_stats != player_with_base_stats:
                issues_found += 1
                self.logger.warning(
                    f"Player count mismatch: {player_with_game_stats} players with game stats, "
                    f"{player_with_base_stats} with base stats"
                )
                # Can't automatically fix this - needs data recalculation
            
            # Validation 2: Check each player's stats for consistency
            players = self.db.query(Player).join(
                BaseStat, Player.player_id == BaseStat.player_id
            ).filter(
                BaseStat.season == season
            ).distinct().all()
            
            for player in players:
                # Get all base stats for this player
                player_base_stats = self._get_player_base_stats(player.player_id, season)
                if not player_base_stats:
                    continue
                
                # Get game stats for validation
                game_stats = self.db.query(GameStats).filter(
                    GameStats.player_id == player.player_id,
                    GameStats.season == season
                ).all()
                
                # 2.1 Validate games played count
                games_stat = next((s for s in player_base_stats if s.stat_type == "games"), None)
                actual_games = len(game_stats)
                
                if games_stat and games_stat.value != actual_games:
                    issues_found += 1
                    self.logger.debug(
                        f"Games count mismatch for {player.name}: recorded {games_stat.value}, "
                        f"actual {actual_games}"
                    )
                    games_stat.value = actual_games
                    issues_fixed += 1
                
                # 2.2 Validate position-specific stats by recalculating from game logs
                position = player.position
                
                if position == "QB":
                    # Check QB stats
                    field_checks = ["pass_attempts", "completions", "pass_yards", "pass_td", 
                                   "interceptions", "rush_attempts", "rush_yards", "rush_td"]
                elif position == "RB":
                    # Check RB stats
                    field_checks = ["rush_attempts", "rush_yards", "rush_td", 
                                   "targets", "receptions", "rec_yards", "rec_td"]
                else:  # WR and TE
                    # Check WR/TE stats
                    field_checks = ["targets", "receptions", "rec_yards", "rec_td"]
                    if position == "WR":
                        field_checks.extend(["rush_attempts", "rush_yards", "rush_td"])
                
                # For each stat field, validate against game logs
                for field in field_checks:
                    # Get base stat value
                    base_stat = next((s for s in player_base_stats if s.stat_type == field), None)
                    if not base_stat:
                        # Stat doesn't exist, create it
                        field_total = sum(g.stats.get(field, 0) for g in game_stats)
                        self._create_base_stat(player.player_id, season, field, field_total)
                        issues_found += 1
                        issues_fixed += 1
                        continue
                    
                    # Calculate actual total from game stats
                    field_total = sum(g.stats.get(field, 0) for g in game_stats)
                    
                    # If there's a mismatch, update the base stat
                    if abs(base_stat.value - field_total) > 0.1:  # Allow for rounding differences
                        issues_found += 1
                        self.logger.debug(
                            f"Stat mismatch for {player.name} {field}: recorded {base_stat.value}, "
                            f"calculated {field_total}"
                        )
                        base_stat.value = field_total
                        issues_fixed += 1
                
                # 2.3 Validate fantasy points
                fantasy_points_stat = next((s for s in player_base_stats if s.stat_type == "half_ppr"), None)
                
                # Gather stats for fantasy points calculation
                stat_values = {}
                for field in field_checks:
                    stat = next((s for s in player_base_stats if s.stat_type == field), None)
                    stat_values[field] = stat.value if stat else 0
                
                # Calculate fantasy points
                calculated_points = self._calculate_fantasy_points(stat_values, position)
                
                if fantasy_points_stat:
                    if abs(fantasy_points_stat.value - calculated_points) > 0.5:  # Allow for minor differences
                        issues_found += 1
                        self.logger.debug(
                            f"Fantasy points mismatch for {player.name}: recorded {fantasy_points_stat.value}, "
                            f"calculated {calculated_points}"
                        )
                        fantasy_points_stat.value = calculated_points
                        issues_fixed += 1
                else:
                    # Create fantasy points stat
                    self._create_base_stat(player.player_id, season, "half_ppr", calculated_points)
                    issues_found += 1
                    issues_fixed += 1
            
            # Commit fixes
            if issues_fixed > 0:
                self.db.commit()
                
            results = {
                "issues_found": issues_found,
                "issues_fixed": issues_fixed,
                "players_validated": len(players)
            }
            
            # Log success
            self._log_import("data_validation", "success", 
                           f"Validated data for season {season}", 
                           results)
            
            return results
            
        except Exception as e:
            self.db.rollback()
            self.metrics["errors"] += 1
            self.logger.error(f"Error validating data: {str(e)}")
            self._log_import("data_validation", "error", 
                           f"Error validating data: {str(e)}")
            raise Exception(f"Error validating data: {str(e)}")
            
    def _get_player_base_stats(self, player_id: str, season: int) -> List[BaseStat]:
        """Get all base stats for a player in a season."""
        return self.db.query(BaseStat).filter(
            BaseStat.player_id == player_id,
            BaseStat.season == season
        ).all()
        
    def _update_base_stat(self, stats: List[BaseStat], stat_type: str, value: float) -> None:
        """Update a specific base stat for a player."""
        stat = next((s for s in stats if s.stat_type == stat_type), None)
        if stat:
            stat.value = value
        else:
            player_id = stats[0].player_id if stats else None
            season = stats[0].season if stats else None
            if player_id and season:
                self._create_base_stat(player_id, season, stat_type, value)
                
    def _create_base_stat(self, player_id: str, season: int, stat_type: str, value: float) -> None:
        """Create a new base stat for a player."""
        new_stat = BaseStat(
            stat_id=str(uuid.uuid4()),
            player_id=player_id,
            season=season,
            stat_type=stat_type,
            value=value
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
        points += stats.get("pass_yards", 0) * 0.04  # 1 point per 25 yards
        points += stats.get("pass_td", 0) * 4        # 4 points per passing TD
        points -= stats.get("interceptions", 0) * 1  # -1 point per interception
        
        # Rushing points
        points += stats.get("rush_yards", 0) * 0.1   # 1 point per 10 yards
        points += stats.get("rush_td", 0) * 6        # 6 points per rushing TD
        
        # Receiving points
        points += stats.get("rec_yards", 0) * 0.1    # 1 point per 10 yards
        points += stats.get("rec_td", 0) * 6         # 6 points per receiving TD
        points += stats.get("receptions", 0) * 0.5   # 0.5 points per reception (half-PPR)
        
        return round(points, 1)
        
    async def import_player_data(self, player_id: str, season: int) -> bool:
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
            self.logger.info(f"Importing data for player {player.name} (ID: {player_id}) for season {season}")
            
            # Get weekly stats for this player
            weekly_data = await self.nfl_data_adapter.get_player_weekly_stats(player_id, season)
            if weekly_data is None or weekly_data.empty:
                self.logger.warning(f"No weekly stats found for player {player.name}")
                return False
                
            # Process weekly stats
            for _, row in weekly_data.iterrows():
                # Skip if week is missing
                if pd.isna(row.get('week')):
                    continue
                    
                week = int(row['week'])
                
                # Check if weekly stat already exists
                existing_stat = self.db.query(GameStats).filter(
                    GameStats.player_id == player_id,
                    GameStats.season == season,
                    GameStats.week == week
                ).first()
                
                if existing_stat:
                    continue  # Skip if already imported
                
                # Get position-specific stats
                position = player.position
                stats = {}
                
                # Import all available stat columns for this position
                for our_name, nfl_name in self.stat_mappings.get(position, {}).items():
                    if nfl_name in row and not pd.isna(row[nfl_name]):
                        stats[our_name] = float(row[nfl_name])
                
                # Create new game stat
                game_stat = GameStats(
                    game_stat_id=str(uuid.uuid4()),
                    player_id=player_id,
                    season=season,
                    week=week,
                    opponent="UNK",  # We don't have this from player weekly stats
                    game_location="unknown",
                    result="unknown",
                    team_score=0,
                    opponent_score=0,
                    stats=stats
                )
                
                self.db.add(game_stat)
                self.metrics["game_stats_processed"] += 1
            
            # Commit all new game stats
            self.db.commit()
            
            # Now calculate season totals for this player
            # Get all game stats
            game_stats = self.db.query(GameStats).filter(
                GameStats.player_id == player_id,
                GameStats.season == season
            ).all()
            
            if not game_stats:
                return True  # No game stats to process
                
            # Count games and aggregate stats
            games_played = len(game_stats)
            position = player.position
            
            # Initialize totals dictionary
            totals = {}
            
            # Aggregate stats based on position (code similar to calculate_season_totals)
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
                    totals.update({
                        "rush_attempts": sum(g.stats.get("rush_attempts", 0) for g in game_stats),
                        "rush_yards": sum(g.stats.get("rush_yards", 0) for g in game_stats),
                        "rush_td": sum(g.stats.get("rush_td", 0) for g in game_stats),
                    })
            
            # Calculate half-PPR fantasy points
            fantasy_points = self._calculate_fantasy_points(totals, position)
            
            # Create or update BaseStat records
            existing_stats = self._get_player_base_stats(player_id, season)
            
            # Update base stats in database
            if existing_stats and len(existing_stats) > 0:
                # Update existing base stats
                for stat_name, value in totals.items():
                    self._update_base_stat(existing_stats, stat_name, value)
                    
                # Update games and half_ppr
                games_stat = next((s for s in existing_stats if s.stat_type == "games"), None)
                if games_stat:
                    games_stat.value = games_played
                else:
                    self._create_base_stat(player_id, season, "games", games_played)
                    
                half_ppr_stat = next((s for s in existing_stats if s.stat_type == "half_ppr"), None)
                if half_ppr_stat:
                    half_ppr_stat.value = fantasy_points
                else:
                    self._create_base_stat(player_id, season, "half_ppr", fantasy_points)
            else:
                # Create new base stats for all values
                for stat_name, value in totals.items():
                    self._create_base_stat(player_id, season, stat_name, value)
                
                # Add games and half_ppr
                self._create_base_stat(player_id, season, "games", games_played)
                self._create_base_stat(player_id, season, "half_ppr", fantasy_points)
            
            # Commit changes
            self.db.commit()
            
            # Log success
            self._log_import("player_data_import", "success", 
                           f"Successfully imported data for player {player.name} (ID: {player_id})", 
                           {"season": season, "games": games_played})
            
            return True
            
        except Exception as e:
            self.db.rollback()
            self.metrics["errors"] += 1
            self.logger.error(f"Error importing player data for {player_id}: {str(e)}")
            self._log_import("player_data_import", "error", 
                           f"Error importing player data for {player_id}: {str(e)}")
            return False
    
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
                details=details
            )
            self.db.add(log_entry)
            self.db.commit()
        except Exception as e:
            self.logger.error(f"Error logging import operation: {str(e)}")
            # Don't raise - this is a non-critical operation