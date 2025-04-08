#!/usr/bin/env python3
"""
Script to import NFL data by position to limit runtime and manage resources better.

This script extends the import_nfl_data.py functionality by focusing on one position at a time.
"""

import asyncio
import argparse
import logging
import os
import sys
import traceback
from typing import List, Optional

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database.database import get_db
from backend.database.models import Player
from backend.services.nfl_data_import_service import NFLDataImportService

# Configure logging
import os

# Ensure logs directory exists
logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(logs_dir, exist_ok=True)

log_file = os.path.join(logs_dir, "position_import.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("position_import")

async def import_position(season: int, position: str) -> None:
    """
    Import data for a specific position for a season.
    
    Args:
        season: NFL season year (e.g., 2024)
        position: Player position (QB, RB, WR, TE)
    """
    logger.info(f"Starting import for position {position} in season {season}")
    
    # Get database session
    db = next(get_db())
    
    try:
        # Initialize service
        service = NFLDataImportService(db)
        
        # Step 1: Import player data
        logger.info(f"Step 1: Importing {position} players for season {season}")
        player_results = await service.import_players(season)
        
        # Get IDs of players with the specified position
        position_players = db.query(Player).filter(Player.position == position).all()
        position_player_ids = [p.player_id for p in position_players]
        logger.info(f"Found {len(position_player_ids)} {position} players")
        
        # Step 2: Import weekly stats for these players only
        logger.info(f"Step 2: Importing weekly stats for {position} players in season {season}")
        
        # Modified to work with specific position players only
        # This approach uses the existing player_limit parameter but with our filtered players
        weekly_results = await import_position_weekly_stats(service, season, position_player_ids)
        
        # Step 3: Calculate season totals (for this position only)
        logger.info(f"Step 3: Calculating season totals for {position} players in season {season}")
        totals_results = await calculate_position_totals(service, season, position)
        
        # Step 4: Validate data (for this position only)
        logger.info(f"Step 4: Validating data for {position} players in season {season}")
        validation_results = await validate_position_data(service, season, position)
        
        results = {
            "position": position,
            "players": len(position_player_ids),
            "weekly_stats": weekly_results,
            "season_totals": totals_results,
            "validation": validation_results
        }
        
        logger.info(f"Completed import for position {position} in season {season}")
        logger.info(f"Results: {results}")
        
        return results
        
    except Exception as e:
        logger.error(f"Error importing position {position} for season {season}: {str(e)}")
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        raise
    finally:
        db.close()

async def import_position_weekly_stats(service: NFLDataImportService, season: int, player_ids: List[str]) -> dict:
    """Import weekly stats for specific player IDs."""
    try:
        db = service.db
        # Import all weekly stats first
        weekly_data = await service.nfl_data_adapter.get_weekly_stats(season)
        service.metrics["requests_made"] += 1
        
        # Get game schedules for additional context
        schedules = await service.nfl_data_adapter.get_schedules(season)
        service.metrics["requests_made"] += 1
        
        # Filter to just our position's players
        weekly_data = weekly_data[weekly_data['player_id'].isin(player_ids)]
        logger.info(f"Filtered weekly stats to {len(weekly_data)} records for specified players")
        
        # Create a lookup for game information (same as in original service)
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
        
        # Process data (similar to original service but with our filtered data)
        stats_added = 0
        errors = 0
        
        # Now process each weekly stat row
        for _, row in weekly_data.iterrows():
            # Skip rows with missing player_id
            if pd.isna(row.get('player_id')):
                continue
                
            # Check if player exists
            player = db.query(Player).filter(
                Player.player_id == row['player_id']
            ).first()
            
            if not player:
                continue  # Skip if player not in database
                
            # Extract week and team
            week = int(row['week']) if not pd.isna(row.get('week')) else 0
            team = row.get('recent_team') if not pd.isna(row.get('recent_team')) else player.team
            
            # Same processing as original method
            # Check if weekly stat already exists
            existing_stat = db.query(GameStats).filter(
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
            for our_name, nfl_name in service.stat_mappings.get(position, {}).items():
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
                
                db.add(game_stat)
                stats_added += 1
                service.metrics["game_stats_processed"] += 1
                
                # Commit in batches to avoid memory issues
                if stats_added % 100 == 0:
                    db.commit()
                    
            except Exception as e:
                logger.error(f"Error processing game stat for {player.name} week {week}: {str(e)}")
                logger.debug(f"Stack trace: {traceback.format_exc()}")
                errors += 1
        
        # Final commit
        db.commit()
        
        results = {
            "weekly_stats_added": stats_added,
            "errors": errors
        }
        
        return results
        
    except Exception as e:
        db.rollback()
        service.metrics["errors"] += 1
        logger.error(f"Error importing weekly stats: {str(e)}")
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        raise Exception(f"Error importing weekly stats: {str(e)}")

async def calculate_position_totals(service: NFLDataImportService, season: int, position: str) -> dict:
    """Calculate season totals for a specific position."""
    try:
        db = service.db
        # Get all players with the specified position and game stats
        players = db.query(Player).join(
            GameStats, Player.player_id == GameStats.player_id
        ).filter(
            GameStats.season == season,
            Player.position == position
        ).distinct().all()
        
        logger.info(f"Found {len(players)} {position} players with game stats")
        
        # Then use the service's existing method to calculate totals for each player
        totals_created = 0
        
        for player in players:
            # Get all game stats for this player and season
            game_stats = db.query(GameStats).filter(
                GameStats.player_id == player.player_id,
                GameStats.season == season
            ).all()
            
            if not game_stats:
                continue
                
            # Count games and aggregate stats
            games_played = len(game_stats)
            
            # Initialize totals dictionary using the position-specific stats
            totals = {}
            
            # Aggregate stats based on position (using the same logic as in the service)
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
                if totals["pass_attempts"] > 0:
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
                if totals["rush_attempts"] > 0:
                    totals["yards_per_carry"] = round(totals["rush_yards"] / totals["rush_attempts"], 1)
                if totals["targets"] > 0:
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
                if totals["targets"] > 0:
                    totals["catch_rate"] = round(totals["receptions"] / totals["targets"] * 100, 1)
                    totals["yards_per_target"] = round(totals["rec_yards"] / totals["targets"], 1)
                if totals["receptions"] > 0:
                    totals["yards_per_reception"] = round(totals["rec_yards"] / totals["receptions"], 1)
            
            # Calculate half-PPR fantasy points
            fantasy_points = service._calculate_fantasy_points(totals, position)
            
            # Create or update BaseStat records using service's helper methods
            existing_stats = service._get_player_base_stats(player.player_id, season)
            
            # Update base stats in database
            if existing_stats:
                # Update existing base stats
                for stat_name, value in totals.items():
                    service._update_base_stat(existing_stats, stat_name, value)
                    
                # Update games and half_ppr
                games_stat = next((s for s in existing_stats if s.stat_type == "games"), None)
                if games_stat:
                    games_stat.value = games_played
                else:
                    service._create_base_stat(player.player_id, season, "games", games_played)
                    
                half_ppr_stat = next((s for s in existing_stats if s.stat_type == "half_ppr"), None)
                if half_ppr_stat:
                    half_ppr_stat.value = fantasy_points
                else:
                    service._create_base_stat(player.player_id, season, "half_ppr", fantasy_points)
            else:
                # Create new base stats for all values
                for stat_name, value in totals.items():
                    service._create_base_stat(player.player_id, season, stat_name, value)
                
                # Add games and half_ppr
                service._create_base_stat(player.player_id, season, "games", games_played)
                service._create_base_stat(player.player_id, season, "half_ppr", fantasy_points)
                
                totals_created += 1
        
        # Commit changes
        db.commit()
        
        results = {
            "totals_created": totals_created,
            "players_processed": len(players)
        }
        
        return results
        
    except Exception as e:
        db.rollback()
        service.metrics["errors"] += 1
        logger.error(f"Error calculating season totals for {position}: {str(e)}")
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        raise Exception(f"Error calculating season totals for {position}: {str(e)}")

async def validate_position_data(service: NFLDataImportService, season: int, position: str) -> dict:
    """Validate data for a specific position."""
    try:
        db = service.db
        issues_found = 0
        issues_fixed = 0
        
        # Get players of the specified position with base stats
        players = db.query(Player).join(
            BaseStat, Player.player_id == BaseStat.player_id
        ).filter(
            BaseStat.season == season,
            Player.position == position
        ).distinct().all()
        
        logger.info(f"Validating data for {len(players)} {position} players")
        
        # Then use logic similar to the original validation but for our filtered players
        for player in players:
            # Get all base stats for this player
            player_base_stats = service._get_player_base_stats(player.player_id, season)
            if not player_base_stats:
                continue
            
            # Get game stats for validation
            game_stats = db.query(GameStats).filter(
                GameStats.player_id == player.player_id,
                GameStats.season == season
            ).all()
            
            # Validate games played count
            games_stat = next((s for s in player_base_stats if s.stat_type == "games"), None)
            actual_games = len(game_stats)
            
            if games_stat and games_stat.value != actual_games:
                issues_found += 1
                logger.debug(
                    f"Games count mismatch for {player.name}: recorded {games_stat.value}, "
                    f"actual {actual_games}"
                )
                games_stat.value = actual_games
                issues_fixed += 1
            
            # Get position-specific fields to check
            if position == "QB":
                field_checks = ["pass_attempts", "completions", "pass_yards", "pass_td", 
                               "interceptions", "rush_attempts", "rush_yards", "rush_td"]
            elif position == "RB":
                field_checks = ["rush_attempts", "rush_yards", "rush_td", 
                               "targets", "receptions", "rec_yards", "rec_td"]
            else:  # WR and TE
                field_checks = ["targets", "receptions", "rec_yards", "rec_td"]
                if position == "WR":
                    field_checks.extend(["rush_attempts", "rush_yards", "rush_td"])
            
            # Validate each field
            for field in field_checks:
                # Get base stat value
                base_stat = next((s for s in player_base_stats if s.stat_type == field), None)
                if not base_stat:
                    # Stat doesn't exist, create it
                    field_total = sum(g.stats.get(field, 0) for g in game_stats)
                    service._create_base_stat(player.player_id, season, field, field_total)
                    issues_found += 1
                    issues_fixed += 1
                    continue
                
                # Calculate actual total from game stats
                field_total = sum(g.stats.get(field, 0) for g in game_stats)
                
                # If there's a mismatch, update the base stat
                if abs(base_stat.value - field_total) > 0.1:  # Allow for rounding differences
                    issues_found += 1
                    logger.debug(
                        f"Stat mismatch for {player.name} {field}: recorded {base_stat.value}, "
                        f"calculated {field_total}"
                    )
                    base_stat.value = field_total
                    issues_fixed += 1
            
            # Validate fantasy points
            fantasy_points_stat = next((s for s in player_base_stats if s.stat_type == "half_ppr"), None)
            
            # Gather stats for fantasy points calculation
            stat_values = {}
            for field in field_checks:
                stat = next((s for s in player_base_stats if s.stat_type == field), None)
                stat_values[field] = stat.value if stat else 0
            
            # Calculate fantasy points
            calculated_points = service._calculate_fantasy_points(stat_values, position)
            
            if fantasy_points_stat:
                if abs(fantasy_points_stat.value - calculated_points) > 0.5:  # Allow for minor differences
                    issues_found += 1
                    logger.debug(
                        f"Fantasy points mismatch for {player.name}: recorded {fantasy_points_stat.value}, "
                        f"calculated {calculated_points}"
                    )
                    fantasy_points_stat.value = calculated_points
                    issues_fixed += 1
            else:
                # Create fantasy points stat
                service._create_base_stat(player.player_id, season, "half_ppr", calculated_points)
                issues_found += 1
                issues_fixed += 1
        
        # Commit fixes
        if issues_fixed > 0:
            db.commit()
            
        results = {
            "issues_found": issues_found,
            "issues_fixed": issues_fixed,
            "players_validated": len(players)
        }
        
        return results
        
    except Exception as e:
        db.rollback()
        service.metrics["errors"] += 1
        logger.error(f"Error validating {position} data: {str(e)}")
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        raise Exception(f"Error validating {position} data: {str(e)}")

async def import_team_stats(season: int) -> None:
    """Import team statistics for a season."""
    logger.info(f"Starting team stats import for season {season}")
    
    # Get database session
    db = next(get_db())
    
    try:
        # Initialize service
        service = NFLDataImportService(db)
        
        # Import team stats
        results = await service.import_team_stats(season)
        
        logger.info(f"Completed team stats import for season {season}")
        logger.info(f"Results: {results}")
        
        return results
    except Exception as e:
        logger.error(f"Error importing team stats for season {season}: {str(e)}")
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        raise
    finally:
        db.close()

async def main():
    """Main entry point for the position-based import script."""
    parser = argparse.ArgumentParser(description='Import NFL data by position to limit runtime')
    parser.add_argument('--season', type=int, required=True, help='Season to import (e.g., 2024)')
    parser.add_argument('--position', choices=['QB', 'RB', 'WR', 'TE', 'team', 'all'], 
                        required=True, help='Position to import or "team" for team stats or "all" for all positions')
    
    args = parser.parse_args()
    
    try:
        if args.position == 'all':
            # Import all positions sequentially
            logger.info(f"Starting import for all positions in season {args.season}")
            
            # First import players
            db = next(get_db())
            service = NFLDataImportService(db)
            await service.import_players(args.season)
            db.close()
            
            # Then import team stats
            await import_team_stats(args.season)
            
            # Then import each position
            for position in ['QB', 'RB', 'WR', 'TE']:
                await import_position(args.season, position)
                
            logger.info(f"Completed import for all positions in season {args.season}")
        elif args.position == 'team':
            # Import team stats only
            await import_team_stats(args.season)
        else:
            # Import specific position
            await import_position(args.season, args.position)
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        sys.exit(1)

# Add missing imports
import uuid
import pandas as pd
from backend.database.models import GameStats, BaseStat

if __name__ == "__main__":
    asyncio.run(main())