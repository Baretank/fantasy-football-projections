#!/usr/bin/env python3
"""
Database Dashboard Script

This script provides a more comprehensive view of the database state,
showing statistics about imported data, counts by position, and validation status.
"""

import sys
from pathlib import Path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)

import argparse
from typing import Dict, List, Any, Optional
from datetime import datetime
from tabulate import tabulate

from backend.database.database import SessionLocal
from backend.database.models import Player, ImportLog, BaseStat, GameStats, TeamStat

def get_db_stats(db) -> Dict[str, Any]:
    """Get comprehensive database statistics."""
    stats = {}
    
    # Player stats
    stats['total_players'] = db.query(Player).count()
    
    # Position breakdown
    stats['players_by_position'] = {}
    for position in ['QB', 'RB', 'WR', 'TE']:
        count = db.query(Player).filter(Player.position == position).count()
        stats['players_by_position'][position] = count
    
    # Stats breakdown
    stats['total_base_stats'] = db.query(BaseStat).count()
    stats['total_game_stats'] = db.query(GameStats).count()
    stats['total_team_stats'] = db.query(TeamStat).count()
    
    # Season breakdown
    stats['seasons'] = []
    seasons = db.query(BaseStat.season).distinct().order_by(BaseStat.season.desc()).all()
    for (season,) in seasons:
        season_stats = {
            'year': season,
            'players_with_stats': db.query(Player).join(
                BaseStat, Player.player_id == BaseStat.player_id
            ).filter(BaseStat.season == season).distinct().count(),
            'players_with_games': db.query(Player).join(
                GameStats, Player.player_id == GameStats.player_id
            ).filter(GameStats.season == season).distinct().count(),
            'total_games': db.query(GameStats).filter(GameStats.season == season).count(),
            'teams_with_stats': db.query(TeamStat).filter(TeamStat.season == season).count()
        }
        stats['seasons'].append(season_stats)
    
    # Import status
    stats['import_stats'] = get_import_stats(db)
    
    return stats

def get_import_stats(db) -> Dict[str, Any]:
    """Get statistics from import logs."""
    stats = {}
    
    # Get latest import time
    latest_import = db.query(ImportLog).order_by(ImportLog.created_at.desc()).first()
    stats['latest_import'] = latest_import.created_at if latest_import else None
    
    # Get counts by operation type
    operation_counts = {}
    operations = db.query(ImportLog.operation).distinct().all()
    for (operation,) in operations:
        count = db.query(ImportLog).filter(ImportLog.operation == operation).count()
        operation_counts[operation] = count
    stats['operation_counts'] = operation_counts
    
    # Get counts by status
    status_counts = {}
    statuses = db.query(ImportLog.status).distinct().all()
    for (status,) in statuses:
        count = db.query(ImportLog).filter(ImportLog.status == status).count()
        status_counts[status] = count
    stats['status_counts'] = status_counts
    
    # Get error rate
    total_logs = db.query(ImportLog).count()
    error_logs = db.query(ImportLog).filter(ImportLog.status == 'error').count()
    stats['error_rate'] = (error_logs / total_logs * 100) if total_logs > 0 else 0
    
    return stats

def print_db_stats(stats: Dict[str, Any]) -> None:
    """Print database statistics in a formatted way."""
    print(f"\n{'='*60}")
    print(f"DATABASE DASHBOARD - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    # Overall counts
    print("\nOVERALL COUNTS:")
    print(f"Total Players: {stats['total_players']}")
    print(f"Total Base Stats: {stats['total_base_stats']}")
    print(f"Total Game Stats: {stats['total_game_stats']}")
    print(f"Total Team Stats: {stats['total_team_stats']}")
    
    # Players by position
    print("\nPLAYERS BY POSITION:")
    for position, count in stats['players_by_position'].items():
        print(f"{position}: {count}")
    
    # Season breakdown
    if stats['seasons']:
        print("\nSEASON BREAKDOWN:")
        season_data = []
        for season in stats['seasons']:
            season_data.append([
                season['year'],
                season['players_with_stats'],
                season['players_with_games'],
                season['total_games'],
                season['teams_with_stats']
            ])
        print(tabulate(
            season_data,
            headers=['Season', 'Players w/Stats', 'Players w/Games', 'Total Games', 'Teams'],
            tablefmt='simple'
        ))
    
    # Import stats
    print("\nIMPORT STATISTICS:")
    import_stats = stats['import_stats']
    print(f"Latest Import: {import_stats['latest_import']}")
    print(f"Error Rate: {import_stats['error_rate']:.2f}%")
    
    print("\nIMPORT OPERATIONS:")
    for operation, count in import_stats['operation_counts'].items():
        print(f"{operation}: {count}")
    
    print("\nIMPORT STATUSES:")
    for status, count in import_stats['status_counts'].items():
        print(f"{status}: {count}")

def check_data_consistency(db, season: Optional[int] = None) -> Dict[str, Any]:
    """Check data consistency between game stats and base stats."""
    results = {
        'total_checked': 0,
        'mismatches_found': 0,
        'positions_checked': {}
    }
    
    # Apply season filter if provided
    season_filter = BaseStat.season == season if season else True
    
    # For each player with base stats, check if their calculated stats match
    players = db.query(Player).join(
        BaseStat, Player.player_id == BaseStat.player_id
    ).filter(season_filter).distinct().all()
    
    for player in players:
        # Initialize position stats if not already present
        if player.position not in results['positions_checked']:
            results['positions_checked'][player.position] = {
                'total': 0,
                'mismatches': 0
            }
        
        # Get all seasons for this player
        seasons = db.query(BaseStat.season).filter(
            BaseStat.player_id == player.player_id
        ).distinct().all()
        
        for (player_season,) in seasons:
            # Skip if specific season filter doesn't match
            if season and player_season != season:
                continue
                
            results['total_checked'] += 1
            results['positions_checked'][player.position]['total'] += 1
            
            # Get base stats for this player and season
            base_stats = db.query(BaseStat).filter(
                BaseStat.player_id == player.player_id,
                BaseStat.season == player_season
            ).all()
            
            # Get game stats for this player and season
            game_stats = db.query(GameStats).filter(
                GameStats.player_id == player.player_id,
                GameStats.season == player_season
            ).all()
            
            # Check game count consistency
            games_stat = next((s for s in base_stats if s.stat_type == 'games'), None)
            actual_games = len(game_stats)
            
            if games_stat and games_stat.value != actual_games:
                results['mismatches_found'] += 1
                results['positions_checked'][player.position]['mismatches'] += 1
                break
            
            # Check other stats based on position
            if player.position == 'QB':
                fields = ['pass_attempts', 'completions', 'pass_yards', 'pass_td', 
                         'interceptions', 'rush_attempts', 'rush_yards', 'rush_td']
            elif player.position == 'RB':
                fields = ['rush_attempts', 'rush_yards', 'rush_td', 
                         'targets', 'receptions', 'rec_yards', 'rec_td']
            elif player.position == 'WR':
                fields = ['targets', 'receptions', 'rec_yards', 'rec_td',
                         'rush_attempts', 'rush_yards', 'rush_td']
            else:  # TE
                fields = ['targets', 'receptions', 'rec_yards', 'rec_td']
            
            for field in fields:
                base_stat = next((s for s in base_stats if s.stat_type == field), None)
                if not base_stat:
                    continue
                
                # Calculate from game stats
                field_total = sum(g.stats.get(field, 0) for g in game_stats)
                
                # Check for significant difference (allowing for minor rounding)
                if abs(base_stat.value - field_total) > 0.1:
                    results['mismatches_found'] += 1
                    results['positions_checked'][player.position]['mismatches'] += 1
                    break
    
    return results

def print_consistency_check(results: Dict[str, Any]) -> None:
    """Print data consistency check results."""
    print(f"\n{'='*60}")
    print(f"DATA CONSISTENCY CHECK")
    print(f"{'='*60}")
    
    print(f"Total Players Checked: {results['total_checked']}")
    print(f"Mismatches Found: {results['mismatches_found']}")
    print(f"Consistency Rate: {((results['total_checked'] - results['mismatches_found']) / results['total_checked'] * 100):.2f}% OK")
    
    print("\nBREAKDOWN BY POSITION:")
    position_data = []
    for position, stats in results['positions_checked'].items():
        consistency = ((stats['total'] - stats['mismatches']) / stats['total'] * 100) if stats['total'] > 0 else 0
        position_data.append([
            position,
            stats['total'],
            stats['mismatches'],
            f"{consistency:.2f}%"
        ])
    
    print(tabulate(
        position_data,
        headers=['Position', 'Checked', 'Mismatches', 'Consistency'],
        tablefmt='simple'
    ))

def main():
    """Main function to run the database dashboard."""
    parser = argparse.ArgumentParser(description='Database dashboard for NFL data')
    parser.add_argument('--season', type=int, help='Filter by specific season (e.g., 2023)')
    parser.add_argument('--check-consistency', action='store_true', help='Run data consistency check')
    
    args = parser.parse_args()
    
    try:
        import tabulate
    except ImportError:
        print("Installing tabulate package for better output formatting...")
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "tabulate"])
        from tabulate import tabulate
    
    # Connect to the database
    db = SessionLocal()
    try:
        # Get and print basic database stats
        stats = get_db_stats(db)
        print_db_stats(stats)
        
        # Run consistency check if requested
        if args.check_consistency:
            consistency_results = check_data_consistency(db, args.season)
            print_consistency_check(consistency_results)
            
    finally:
        db.close()

if __name__ == "__main__":
    main()