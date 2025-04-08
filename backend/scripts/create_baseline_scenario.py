#!/usr/bin/env python3
"""
Create Baseline Scenarios Script

This script creates baseline scenarios for fantasy football projections
based on imported NFL data. It creates default scenarios that can be used
as starting points for user projections.
"""

import sys
from pathlib import Path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)

import argparse
import logging
import uuid
from typing import Dict, Any, List, Optional
import json

from backend.database.database import SessionLocal
from backend.database.models import Scenario, Player, BaseStat, TeamStat

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def create_baseline_scenario(db, name: str, season: int, description: str = None) -> Scenario:
    """Create a new baseline scenario."""
    # Check if scenario already exists
    existing = db.query(Scenario).filter(Scenario.name == name).first()
    if existing:
        logger.info(f"Scenario '{name}' already exists with ID {existing.scenario_id}")
        return existing
    
    # Create new scenario
    scenario = Scenario(
        scenario_id=str(uuid.uuid4()),
        name=name,
        description=description or f"Baseline scenario for {season} season",
        is_baseline=True,
        season=season,
        parameters={}
    )
    
    db.add(scenario)
    db.commit()
    
    logger.info(f"Created new baseline scenario '{name}' with ID {scenario.scenario_id}")
    return scenario

def create_average_baseline(db, season: int) -> Dict[str, Any]:
    """Create a baseline scenario using league averages."""
    # Create the scenario
    scenario = create_baseline_scenario(
        db, 
        f"League Average {season}", 
        season,
        f"Baseline projections based on league averages for {season}"
    )
    
    # Set parameters based on league averages
    scenario.parameters = {
        "source": "league_average",
        "description": f"Based on league averages for {season}",
        "created_at": str(scenario.created_at),
        "stats_multipliers": {
            "QB": {
                "pass_yards": 1.0,
                "pass_td": 1.0,
                "interceptions": 1.0,
                "rush_yards": 1.0,
                "rush_td": 1.0
            },
            "RB": {
                "rush_yards": 1.0,
                "rush_td": 1.0,
                "receptions": 1.0,
                "rec_yards": 1.0,
                "rec_td": 1.0
            },
            "WR": {
                "receptions": 1.0,
                "rec_yards": 1.0,
                "rec_td": 1.0,
                "rush_yards": 1.0,
                "rush_td": 1.0
            },
            "TE": {
                "receptions": 1.0,
                "rec_yards": 1.0,
                "rec_td": 1.0
            }
        }
    }
    
    db.commit()
    
    return {
        "scenario_id": scenario.scenario_id,
        "name": scenario.name,
        "season": season
    }

def create_optimistic_baseline(db, season: int) -> Dict[str, Any]:
    """Create an optimistic baseline scenario with boosted stats."""
    # Create the scenario
    scenario = create_baseline_scenario(
        db, 
        f"Optimistic {season}", 
        season,
        f"Optimistic projections with boosted stats for {season}"
    )
    
    # Set parameters with optimistic multipliers
    scenario.parameters = {
        "source": "optimistic",
        "description": f"Optimistic projections with boosted offensive stats for {season}",
        "created_at": str(scenario.created_at),
        "stats_multipliers": {
            "QB": {
                "pass_yards": 1.1,
                "pass_td": 1.15,
                "interceptions": 0.9,
                "rush_yards": 1.05,
                "rush_td": 1.1
            },
            "RB": {
                "rush_yards": 1.1,
                "rush_td": 1.15,
                "receptions": 1.05,
                "rec_yards": 1.1,
                "rec_td": 1.1
            },
            "WR": {
                "receptions": 1.08,
                "rec_yards": 1.12,
                "rec_td": 1.15,
                "rush_yards": 1.05,
                "rush_td": 1.1
            },
            "TE": {
                "receptions": 1.1,
                "rec_yards": 1.1,
                "rec_td": 1.15
            }
        }
    }
    
    db.commit()
    
    return {
        "scenario_id": scenario.scenario_id,
        "name": scenario.name,
        "season": season
    }

def create_conservative_baseline(db, season: int) -> Dict[str, Any]:
    """Create a conservative baseline scenario with reduced stats."""
    # Create the scenario
    scenario = create_baseline_scenario(
        db, 
        f"Conservative {season}", 
        season,
        f"Conservative projections with reduced stats for {season}"
    )
    
    # Set parameters with conservative multipliers
    scenario.parameters = {
        "source": "conservative",
        "description": f"Conservative projections with reduced offensive stats for {season}",
        "created_at": str(scenario.created_at),
        "stats_multipliers": {
            "QB": {
                "pass_yards": 0.95,
                "pass_td": 0.9,
                "interceptions": 1.05,
                "rush_yards": 0.95,
                "rush_td": 0.9
            },
            "RB": {
                "rush_yards": 0.95,
                "rush_td": 0.9,
                "receptions": 0.95,
                "rec_yards": 0.95,
                "rec_td": 0.9
            },
            "WR": {
                "receptions": 0.95,
                "rec_yards": 0.95,
                "rec_td": 0.9,
                "rush_yards": 0.95,
                "rush_td": 0.9
            },
            "TE": {
                "receptions": 0.95,
                "rec_yards": 0.95,
                "rec_td": 0.9
            }
        }
    }
    
    db.commit()
    
    return {
        "scenario_id": scenario.scenario_id,
        "name": scenario.name,
        "season": season
    }

def create_team_adjusted_baseline(db, season: int) -> Dict[str, Any]:
    """Create a baseline scenario that accounts for team tendencies."""
    # Create the scenario
    scenario = create_baseline_scenario(
        db, 
        f"Team Adjusted {season}", 
        season,
        f"Projections adjusted based on team tendencies for {season}"
    )
    
    # Get team stats for adjustments
    team_stats = db.query(TeamStat).filter(TeamStat.season == season).all()
    team_adjustments = {}
    
    # Create team-specific adjustments based on statistics
    for team_stat in team_stats:
        team = team_stat.team
        
        # Calculate pass vs rush tendencies compared to league average
        pass_multiplier = 1.0
        rush_multiplier = 1.0
        
        # Simplistic example: teams with higher pass percentage get pass boost
        # This is a simple example - in a real system you'd use more sophisticated calculations
        if team_stat.pass_percentage > 55:  # Higher than average pass tendency
            pass_multiplier = 1.05
            rush_multiplier = 0.95
        elif team_stat.pass_percentage < 45:  # Higher than average rush tendency
            pass_multiplier = 0.95
            rush_multiplier = 1.05
            
        # Store adjustments for this team
        team_adjustments[team] = {
            "pass_multiplier": pass_multiplier,
            "rush_multiplier": rush_multiplier,
            "rec_multiplier": pass_multiplier,  # Receiving tied to passing
            "td_multiplier": 1.0  # Default - could adjust based on red zone efficiency
        }
    
    # Set parameters with team adjustments
    scenario.parameters = {
        "source": "team_adjusted",
        "description": f"Projections adjusted based on team tendencies for {season}",
        "created_at": str(scenario.created_at),
        "team_adjustments": team_adjustments,
        "stats_multipliers": {
            "QB": {
                "pass_yards": 1.0,
                "pass_td": 1.0,
                "interceptions": 1.0,
                "rush_yards": 1.0,
                "rush_td": 1.0
            },
            "RB": {
                "rush_yards": 1.0,
                "rush_td": 1.0,
                "receptions": 1.0,
                "rec_yards": 1.0,
                "rec_td": 1.0
            },
            "WR": {
                "receptions": 1.0,
                "rec_yards": 1.0,
                "rec_td": 1.0,
                "rush_yards": 1.0,
                "rush_td": 1.0
            },
            "TE": {
                "receptions": 1.0,
                "rec_yards": 1.0,
                "rec_td": 1.0
            }
        }
    }
    
    db.commit()
    
    return {
        "scenario_id": scenario.scenario_id,
        "name": scenario.name,
        "season": season
    }

def main():
    """Main function to create baseline scenarios."""
    parser = argparse.ArgumentParser(description='Create baseline scenarios for projections')
    parser.add_argument('--season', type=int, required=True, help='Season year (e.g., 2023)')
    parser.add_argument('--type', choices=['all', 'average', 'optimistic', 'conservative', 'team'], 
                      default='all', help='Type of baseline scenario to create')
    
    args = parser.parse_args()
    
    # Connect to the database
    db = SessionLocal()
    try:
        results = []
        
        if args.type == 'all' or args.type == 'average':
            results.append(create_average_baseline(db, args.season))
            
        if args.type == 'all' or args.type == 'optimistic':
            results.append(create_optimistic_baseline(db, args.season))
            
        if args.type == 'all' or args.type == 'conservative':
            results.append(create_conservative_baseline(db, args.season))
            
        if args.type == 'all' or args.type == 'team':
            results.append(create_team_adjusted_baseline(db, args.season))
        
        # Print results
        print(f"\nCreated {len(results)} baseline scenarios for season {args.season}:")
        for result in results:
            print(f"- {result['name']} (ID: {result['scenario_id']})")
            
    finally:
        db.close()

if __name__ == "__main__":
    main()