#!/usr/bin/env python3
"""
Check Import Script

This script checks the contents of the database after imports to verify
data has been imported correctly. It displays summary information about
players and import logs.
"""

import sys
from pathlib import Path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)

import argparse
from typing import Optional, List, Dict, Any
import logging

from backend.database.database import SessionLocal
from backend.database.models import Player, ImportLog, BaseStat, GameStats, TeamStat

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def check_players(db, position: Optional[str] = None, team: Optional[str] = None, limit: int = 5) -> None:
    """Check players in the database with optional filtering."""
    query = db.query(Player)
    
    # Apply filters if provided
    if position:
        query = query.filter(Player.position == position)
    if team:
        query = query.filter(Player.team == team)
    
    # Count total players matching criteria
    total_count = query.count()
    
    # Get sample of players
    players = query.limit(limit).all()
    
    print(f"\n{'='*50}")
    print(f"PLAYERS IN DATABASE: {total_count}")
    print(f"{'='*50}")
    
    if position:
        print(f"Filtered by position: {position}")
    if team:
        print(f"Filtered by team: {team}")
    
    print(f"\nSample of {len(players)} players:")
    for player in players:
        print(f"- {player.name} ({player.position}, {player.team})")

def check_import_logs(db, limit: int = 5) -> None:
    """Check recent import logs."""
    logs = db.query(ImportLog).order_by(ImportLog.created_at.desc()).limit(limit).all()
    
    print(f"\n{'='*50}")
    print(f"RECENT IMPORT LOGS")
    print(f"{'='*50}")
    
    if not logs:
        print("No import logs found.")
        return
    
    for log in logs:
        print(f"- {log.created_at}: {log.operation} - {log.status} - {log.message}")

def check_player_stats(db, player_name: Optional[str] = None, season: Optional[int] = None) -> None:
    """Check stats for a specific player or get stats summary for a season."""
    if player_name:
        # Find player by name (using case-insensitive LIKE)
        player = db.query(Player).filter(Player.name.ilike(f"%{player_name}%")).first()
        
        if not player:
            print(f"\nNo player found matching: {player_name}")
            return
        
        print(f"\n{'='*50}")
        print(f"STATS FOR: {player.name} ({player.position}, {player.team})")
        print(f"{'='*50}")
        
        # Get base stats for player
        season_filter = BaseStat.season == season if season else True
        base_stats = db.query(BaseStat).filter(
            BaseStat.player_id == player.player_id,
            season_filter
        ).all()
        
        if not base_stats:
            print(f"No stats found for this player{' in season '+str(season) if season else ''}.")
            return
        
        # Group stats by season
        stats_by_season = {}
        for stat in base_stats:
            if stat.season not in stats_by_season:
                stats_by_season[stat.season] = []
            stats_by_season[stat.season].append(stat)
        
        # Print stats by season
        for season, stats in sorted(stats_by_season.items(), reverse=True):
            print(f"\nSeason {season}:")
            
            # Get games played
            games = next((s.value for s in stats if s.stat_type == 'games'), 0)
            print(f"Games played: {games}")
            
            # Get fantasy points
            fantasy_points = next((s.value for s in stats if s.stat_type == 'half_ppr'), 0)
            print(f"Half PPR points: {fantasy_points}")
            
            # Get position-specific stats
            if player.position == 'QB':
                print_stat(stats, 'pass_attempts', 'Pass Attempts')
                print_stat(stats, 'completions', 'Completions')
                print_stat(stats, 'pass_yards', 'Pass Yards')
                print_stat(stats, 'pass_td', 'Pass TDs')
                print_stat(stats, 'interceptions', 'Interceptions')
                print_stat(stats, 'rush_attempts', 'Rush Attempts')
                print_stat(stats, 'rush_yards', 'Rush Yards')
                print_stat(stats, 'rush_td', 'Rush TDs')
            elif player.position == 'RB':
                print_stat(stats, 'rush_attempts', 'Rush Attempts')
                print_stat(stats, 'rush_yards', 'Rush Yards')
                print_stat(stats, 'rush_td', 'Rush TDs')
                print_stat(stats, 'targets', 'Targets')
                print_stat(stats, 'receptions', 'Receptions')
                print_stat(stats, 'rec_yards', 'Receiving Yards')
                print_stat(stats, 'rec_td', 'Receiving TDs')
            elif player.position == 'WR' or player.position == 'TE':
                print_stat(stats, 'targets', 'Targets')
                print_stat(stats, 'receptions', 'Receptions')
                print_stat(stats, 'rec_yards', 'Receiving Yards')
                print_stat(stats, 'rec_td', 'Receiving TDs')
                if player.position == 'WR':
                    print_stat(stats, 'rush_attempts', 'Rush Attempts')
                    print_stat(stats, 'rush_yards', 'Rush Yards')
                    print_stat(stats, 'rush_td', 'Rush TDs')
    else:
        # Show summary stats by position for a specific season
        if not season:
            print("\nPlease specify a season to get stats summary.")
            return
        
        print(f"\n{'='*50}")
        print(f"STATS SUMMARY FOR SEASON: {season}")
        print(f"{'='*50}")
        
        for position in ['QB', 'RB', 'WR', 'TE']:
            # Count players with stats for this position
            players_with_stats = db.query(Player).join(
                BaseStat, Player.player_id == BaseStat.player_id
            ).filter(
                Player.position == position,
                BaseStat.season == season
            ).distinct().count()
            
            print(f"\n{position}: {players_with_stats} players with stats")
            
            # Get top 3 players by fantasy points
            top_players = db.query(Player, BaseStat.value).join(
                BaseStat, Player.player_id == BaseStat.player_id
            ).filter(
                Player.position == position,
                BaseStat.season == season,
                BaseStat.stat_type == 'half_ppr'
            ).order_by(BaseStat.value.desc()).limit(3).all()
            
            if top_players:
                print("Top players by fantasy points:")
                for player, points in top_players:
                    print(f"- {player.name} ({player.team}): {points:.1f} points")

def print_stat(stats: List[BaseStat], stat_type: str, label: str) -> None:
    """Helper function to print a specific stat with its label."""
    value = next((s.value for s in stats if s.stat_type == stat_type), 0)
    if value > 0:
        print(f"{label}: {value}")

def check_team_stats(db, season: Optional[int] = None, team: Optional[str] = None) -> None:
    """Check team stats in the database."""
    query = db.query(TeamStat)
    
    # Apply filters
    if season:
        query = query.filter(TeamStat.season == season)
    if team:
        query = query.filter(TeamStat.team == team)
    
    team_stats = query.all()
    
    print(f"\n{'='*50}")
    print(f"TEAM STATS: {len(team_stats)} records")
    print(f"{'='*50}")
    
    if not team_stats:
        print("No team stats found with the specified criteria.")
        return
    
    # Group by season
    stats_by_season = {}
    for stat in team_stats:
        if stat.season not in stats_by_season:
            stats_by_season[stat.season] = []
        stats_by_season[stat.season].append(stat)
    
    # Print by season
    for season, stats in sorted(stats_by_season.items(), reverse=True):
        print(f"\nSeason {season}: {len(stats)} teams")
        
        if team:
            # Detailed stats for specific team
            team_stat = next((s for s in stats if s.team == team), None)
            if team_stat:
                print(f"\n{team} Team Stats:")
                print(f"Plays: {team_stat.plays}")
                print(f"Pass %: {team_stat.pass_percentage:.1f}%")
                print(f"Pass Attempts: {team_stat.pass_attempts}")
                print(f"Pass Yards: {team_stat.pass_yards}")
                print(f"Pass TDs: {team_stat.pass_td}")
                print(f"Pass TD Rate: {team_stat.pass_td_rate:.2f}%")
                print(f"Rush Attempts: {team_stat.rush_attempts}")
                print(f"Rush Yards: {team_stat.rush_yards}")
                print(f"Yards/Carry: {team_stat.rush_yards_per_carry:.2f}")
                print(f"Rush TDs: {team_stat.rush_td}")
        else:
            # Just list teams
            for team_stat in stats[:5]:  # Show first 5
                print(f"- {team_stat.team}: Rank {team_stat.rank}, Pass %: {team_stat.pass_percentage:.1f}%, YPC: {team_stat.rush_yards_per_carry:.2f}")
            
            if len(stats) > 5:
                print(f"... and {len(stats) - 5} more teams")

def main():
    """Main function to check database contents."""
    parser = argparse.ArgumentParser(description='Check database import status')
    parser.add_argument('--position', help='Filter players by position (QB, RB, WR, TE)')
    parser.add_argument('--team', help='Filter by team abbreviation (e.g., KC, DAL)')
    parser.add_argument('--season', type=int, help='Filter by season year (e.g., 2023)')
    parser.add_argument('--player', help='Check stats for a specific player (partial name match)')
    parser.add_argument('--limit', type=int, default=5, help='Limit number of items to display')
    parser.add_argument('--logs', action='store_true', help='Show import logs')
    parser.add_argument('--team-stats', action='store_true', help='Show team stats')
    
    args = parser.parse_args()
    
    # Connect to the database
    db = SessionLocal()
    try:
        # Always show player count
        check_players(db, args.position, args.team, args.limit)
        
        # Show import logs if requested
        if args.logs:
            check_import_logs(db, args.limit)
        
        # Check player stats if requested
        if args.player or args.season:
            check_player_stats(db, args.player, args.season)
        
        # Check team stats if requested
        if args.team_stats:
            check_team_stats(db, args.season, args.team)
            
    finally:
        db.close()

if __name__ == "__main__":
    main()