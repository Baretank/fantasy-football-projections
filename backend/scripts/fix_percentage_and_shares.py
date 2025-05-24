#!/usr/bin/env python3
"""
Script to fix percentage calculations and add missing share calculations in projections.

This script will:
1. Fix completion percentages that are over 100% (they were calculated correctly but stored incorrectly)
2. Fix catch percentages that are over 100%
3. Calculate missing rush_share and target_share values for all projections
4. Ensure all shares are properly bounded between 0 and 1

Usage:
    cd backend && python scripts/fix_percentage_and_shares.py
"""

import sys
import os
import logging
from typing import Dict, Any, List
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)

from backend.database.database import SessionLocal
from backend.database.models import Projection, Player, TeamStat
from sqlalchemy import and_
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def fix_percentage_calculations(db) -> Dict[str, Any]:
    """Fix percentage calculations that are over 100%."""
    try:
        logger.info("Starting percentage calculation fixes...")
        
        # Query all projections with percentages over 100%
        bad_comp_pct = db.query(Projection).filter(Projection.comp_pct > 100).all()
        bad_catch_pct = db.query(Projection).filter(Projection.catch_pct > 100).all()
        
        logger.info(f"Found {len(bad_comp_pct)} projections with comp_pct > 100%")
        logger.info(f"Found {len(bad_catch_pct)} projections with catch_pct > 100%")
        
        comp_fixed = 0
        catch_fixed = 0
        
        # Fix completion percentages
        for projection in bad_comp_pct:
            if (projection.pass_attempts and projection.pass_attempts > 0 and 
                projection.completions is not None):
                # Recalculate correctly
                new_comp_pct = (projection.completions / projection.pass_attempts) * 100
                logger.debug(f"Fixing comp_pct: {projection.comp_pct} -> {new_comp_pct}")
                projection.comp_pct = new_comp_pct
                comp_fixed += 1
        
        # Fix catch percentages
        for projection in bad_catch_pct:
            if (projection.targets and projection.targets > 0 and 
                projection.receptions is not None):
                # Recalculate correctly
                new_catch_pct = (projection.receptions / projection.targets) * 100
                logger.debug(f"Fixing catch_pct: {projection.catch_pct} -> {new_catch_pct}")
                projection.catch_pct = new_catch_pct
                catch_fixed += 1
        
        db.commit()
        
        return {
            "success": True,
            "comp_pct_fixed": comp_fixed,
            "catch_pct_fixed": catch_fixed,
            "message": f"Fixed {comp_fixed} completion percentages and {catch_fixed} catch percentages"
        }
        
    except Exception as e:
        logger.error(f"Error fixing percentage calculations: {str(e)}")
        db.rollback()
        return {
            "success": False,
            "message": f"Error fixing percentage calculations: {str(e)}"
        }


def calculate_missing_shares(db) -> Dict[str, Any]:
    """Calculate missing rush_share and target_share values."""
    try:
        logger.info("Starting share calculation fixes...")
        
        # Get all projections that need share calculations
        projections = db.query(Projection).join(Player).all()
        
        shares_calculated = 0
        error_count = 0
        
        for projection in projections:
            try:
                player = projection.player
                if not player:
                    continue
                
                # Get team stats for this team and season
                team_stats = (
                    db.query(TeamStat)
                    .filter(and_(
                        TeamStat.team == player.team,
                        TeamStat.season == projection.season
                    ))
                    .first()
                )
                
                if not team_stats:
                    logger.warning(f"No team stats found for {player.team} in {projection.season}")
                    continue
                
                shares_updated = False
                
                # Calculate shares based on position
                if player.position == "QB":
                    # QB rush share (usually small)
                    if (team_stats.rush_attempts and team_stats.rush_attempts > 0 and 
                        projection.rush_attempts and projection.rush_attempts > 0):
                        new_rush_share = projection.rush_attempts / team_stats.rush_attempts
                        if projection.rush_share != new_rush_share:
                            projection.rush_share = max(0.0, min(1.0, new_rush_share))
                            shares_updated = True
                    else:
                        if projection.rush_share != 0.0:
                            projection.rush_share = 0.0
                            shares_updated = True
                
                elif player.position == "RB":
                    # RB rush share
                    if (team_stats.rush_attempts and team_stats.rush_attempts > 0 and 
                        projection.rush_attempts and projection.rush_attempts > 0):
                        new_rush_share = projection.rush_attempts / team_stats.rush_attempts
                        if projection.rush_share != new_rush_share:
                            projection.rush_share = max(0.0, min(1.0, new_rush_share))
                            shares_updated = True
                    else:
                        if projection.rush_share != 0.0:
                            projection.rush_share = 0.0
                            shares_updated = True
                    
                    # RB target share
                    if (team_stats.targets and team_stats.targets > 0 and 
                        projection.targets and projection.targets > 0):
                        new_target_share = projection.targets / team_stats.targets
                        if projection.target_share != new_target_share:
                            projection.target_share = max(0.0, min(1.0, new_target_share))
                            shares_updated = True
                    else:
                        if projection.target_share != 0.0:
                            projection.target_share = 0.0
                            shares_updated = True
                
                elif player.position in ["WR", "TE"]:
                    # WR/TE target share
                    if (team_stats.targets and team_stats.targets > 0 and 
                        projection.targets and projection.targets > 0):
                        new_target_share = projection.targets / team_stats.targets
                        if projection.target_share != new_target_share:
                            projection.target_share = max(0.0, min(1.0, new_target_share))
                            shares_updated = True
                    else:
                        if projection.target_share != 0.0:
                            projection.target_share = 0.0
                            shares_updated = True
                    
                    # WR rush share (usually minimal)
                    if (player.position == "WR" and team_stats.rush_attempts and 
                        team_stats.rush_attempts > 0 and projection.rush_attempts and 
                        projection.rush_attempts > 0):
                        new_rush_share = projection.rush_attempts / team_stats.rush_attempts
                        if projection.rush_share != new_rush_share:
                            projection.rush_share = max(0.0, min(1.0, new_rush_share))
                            shares_updated = True
                    else:
                        if projection.rush_share != 0.0:
                            projection.rush_share = 0.0
                            shares_updated = True
                
                if shares_updated:
                    projection.updated_at = datetime.utcnow()
                    shares_calculated += 1
                    
                    if shares_calculated % 100 == 0:
                        logger.info(f"Processed {shares_calculated} projections...")
                        
            except Exception as e:
                logger.error(f"Error processing projection {projection.projection_id}: {str(e)}")
                error_count += 1
                continue
        
        db.commit()
        
        return {
            "success": True,
            "shares_calculated": shares_calculated,
            "errors": error_count,
            "message": f"Calculated shares for {shares_calculated} projections with {error_count} errors"
        }
        
    except Exception as e:
        logger.error(f"Error calculating shares: {str(e)}")
        db.rollback()
        return {
            "success": False,
            "message": f"Error calculating shares: {str(e)}"
        }


def validate_fixes(db) -> Dict[str, Any]:
    """Validate that the fixes worked correctly."""
    try:
        logger.info("Validating fixes...")
        
        # Check for any remaining bad percentages
        bad_comp_pct = db.query(Projection).filter(Projection.comp_pct > 100).count()
        bad_catch_pct = db.query(Projection).filter(Projection.catch_pct > 100).count()
        
        # Check for shares outside valid range
        bad_rush_share = db.query(Projection).filter(
            (Projection.rush_share < 0) | (Projection.rush_share > 1)
        ).count()
        bad_target_share = db.query(Projection).filter(
            (Projection.target_share < 0) | (Projection.target_share > 1)
        ).count()
        
        # Count total projections with shares
        total_with_rush_share = db.query(Projection).filter(
            Projection.rush_share.is_not(None)
        ).count()
        total_with_target_share = db.query(Projection).filter(
            Projection.target_share.is_not(None)
        ).count()
        
        return {
            "bad_comp_pct": bad_comp_pct,
            "bad_catch_pct": bad_catch_pct,
            "bad_rush_share": bad_rush_share,
            "bad_target_share": bad_target_share,
            "total_with_rush_share": total_with_rush_share,
            "total_with_target_share": total_with_target_share,
            "validation_passed": (bad_comp_pct == 0 and bad_catch_pct == 0 and 
                                 bad_rush_share == 0 and bad_target_share == 0)
        }
        
    except Exception as e:
        logger.error(f"Error validating fixes: {str(e)}")
        return {
            "validation_passed": False,
            "error": str(e)
        }


def main():
    """Main function to run all fixes."""
    logger.info("Starting percentage and share calculation fixes...")
    
    db = SessionLocal()
    
    try:
        # 1. Fix percentage calculations
        logger.info("=" * 50)
        logger.info("Step 1: Fixing percentage calculations")
        logger.info("=" * 50)
        
        percentage_results = fix_percentage_calculations(db)
        logger.info(f"Percentage fix results: {percentage_results}")
        
        if not percentage_results["success"]:
            logger.error("Percentage fixes failed, aborting")
            return
        
        # 2. Calculate missing shares
        logger.info("=" * 50)
        logger.info("Step 2: Calculating missing share values")
        logger.info("=" * 50)
        
        share_results = calculate_missing_shares(db)
        logger.info(f"Share calculation results: {share_results}")
        
        if not share_results["success"]:
            logger.error("Share calculations failed, aborting")
            return
        
        # 3. Validate fixes
        logger.info("=" * 50)
        logger.info("Step 3: Validating fixes")
        logger.info("=" * 50)
        
        validation_results = validate_fixes(db)
        logger.info(f"Validation results: {validation_results}")
        
        if validation_results["validation_passed"]:
            logger.info("✅ All fixes applied successfully!")
            logger.info(f"Summary:")
            logger.info(f"  - Fixed {percentage_results['comp_pct_fixed']} completion percentages")
            logger.info(f"  - Fixed {percentage_results['catch_pct_fixed']} catch percentages")
            logger.info(f"  - Calculated shares for {share_results['shares_calculated']} projections")
            logger.info(f"  - {validation_results['total_with_rush_share']} projections now have rush_share")
            logger.info(f"  - {validation_results['total_with_target_share']} projections now have target_share")
        else:
            logger.error("❌ Some fixes failed validation")
            if "error" in validation_results:
                logger.error(f"Validation error: {validation_results['error']}")
            else:
                logger.error(f"Remaining issues:")
                logger.error(f"  - Bad completion percentages: {validation_results['bad_comp_pct']}")
                logger.error(f"  - Bad catch percentages: {validation_results['bad_catch_pct']}")
                logger.error(f"  - Bad rush shares: {validation_results['bad_rush_share']}")
                logger.error(f"  - Bad target shares: {validation_results['bad_target_share']}")
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()