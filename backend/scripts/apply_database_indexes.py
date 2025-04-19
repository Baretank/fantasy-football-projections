#!/usr/bin/env python
"""
Script to apply database performance optimizations and indices.
"""
import os
import sys
import logging
import sqlite3
import argparse
from time import time

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Define database paths
DEFAULT_DB_PATH = os.path.join("data", "fantasy_football.db")
TEST_DB_PATH = os.path.join("backend", "tests", "data", "test.db")


def get_existing_indexes(conn):
    """Get list of existing indices in the database."""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index';")
    indexes = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return indexes


def create_indexes(conn, force=False):
    """Create database indices for performance optimization."""
    cursor = conn.cursor()
    existing_indexes = get_existing_indexes(conn) if not force else []
    indexes = [
        # Player table indexes
        ("CREATE INDEX IF NOT EXISTS ix_players_name ON players(name);", "ix_players_name"),
        ("CREATE INDEX IF NOT EXISTS ix_players_team ON players(team);", "ix_players_team"),
        (
            "CREATE INDEX IF NOT EXISTS ix_players_position ON players(position);",
            "ix_players_position",
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_players_position_team ON players(position, team);",
            "ix_players_position_team",
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_players_position_status ON players(position, status);",
            "ix_players_position_status",
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_players_fantasy_relevant ON players(position, status, team);",
            "ix_players_fantasy_relevant",
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_players_team_position ON players(team, position);",
            "ix_players_team_position",
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_players_draft_status ON players(draft_status);",
            "ix_players_draft_status",
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_players_is_rookie ON players(is_rookie);",
            "ix_players_is_rookie",
        ),
        # Game stats indexes
        (
            "CREATE INDEX IF NOT EXISTS ix_game_stats_player_id ON game_stats(player_id);",
            "ix_game_stats_player_id",
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_game_stats_season ON game_stats(season);",
            "ix_game_stats_season",
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_game_stats_week ON game_stats(week);",
            "ix_game_stats_week",
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_game_stats_player_season ON game_stats(player_id, season);",
            "ix_game_stats_player_season",
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_game_stats_season_week ON game_stats(season, week);",
            "ix_game_stats_season_week",
        ),
        # Projection indexes
        (
            "CREATE INDEX IF NOT EXISTS ix_projections_player_id ON projections(player_id);",
            "ix_projections_player_id",
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_projections_scenario_id ON projections(scenario_id);",
            "ix_projections_scenario_id",
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_projections_season ON projections(season);",
            "ix_projections_season",
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_projections_half_ppr ON projections(half_ppr);",
            "ix_projections_half_ppr",
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_projections_player_season ON projections(player_id, season);",
            "ix_projections_player_season",
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_projections_scenario_season ON projections(scenario_id, season);",
            "ix_projections_scenario_season",
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_projections_season_half_ppr ON projections(season, half_ppr);",
            "ix_projections_season_half_ppr",
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_projections_player_scenario ON projections(player_id, scenario_id);",
            "ix_projections_player_scenario",
        ),
        # Team stats indexes
        (
            "CREATE INDEX IF NOT EXISTS ix_team_stats_team ON team_stats(team);",
            "ix_team_stats_team",
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_team_stats_season ON team_stats(season);",
            "ix_team_stats_season",
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_team_stats_team_season ON team_stats(team, season);",
            "ix_team_stats_team_season",
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_team_stats_season_rank ON team_stats(season, rank);",
            "ix_team_stats_season_rank",
        ),
        # Base stats indexes
        (
            "CREATE INDEX IF NOT EXISTS ix_base_stats_player_id ON base_stats(player_id);",
            "ix_base_stats_player_id",
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_base_stats_season ON base_stats(season);",
            "ix_base_stats_season",
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_base_stats_stat_type ON base_stats(stat_type);",
            "ix_base_stats_stat_type",
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_base_stats_player_season ON base_stats(player_id, season);",
            "ix_base_stats_player_season",
        ),
        # Scenario indexes
        (
            "CREATE INDEX IF NOT EXISTS ix_scenarios_season ON scenarios(season);",
            "ix_scenarios_season",
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_scenarios_is_baseline ON scenarios(is_baseline);",
            "ix_scenarios_is_baseline",
        ),
        # Override indexes
        (
            "CREATE INDEX IF NOT EXISTS ix_stat_overrides_player_id ON stat_overrides(player_id);",
            "ix_stat_overrides_player_id",
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_stat_overrides_projection_id ON stat_overrides(projection_id);",
            "ix_stat_overrides_projection_id",
        ),
    ]

    created_count = 0
    for sql, index_name in indexes:
        if index_name in existing_indexes and not force:
            logger.info(f"Index {index_name} already exists, skipping...")
            continue

        logger.info(f"Creating index: {index_name}")
        start_time = time()
        try:
            cursor.execute(sql)
            created_count += 1
            logger.info(f"Created index {index_name} in {time() - start_time:.2f} seconds")
        except sqlite3.OperationalError as e:
            logger.error(f"Error creating index {index_name}: {str(e)}")

    # Analyze the database for query optimization
    logger.info("Analyzing database for query optimization...")
    cursor.execute("ANALYZE;")

    cursor.close()
    conn.commit()
    return created_count


def optimize_database(conn):
    """Run general database optimizations."""
    cursor = conn.cursor()

    # Enable WAL mode for better concurrency
    logger.info("Enabling WAL mode...")
    cursor.execute("PRAGMA journal_mode = WAL;")

    # Set recommended pragmas for performance
    logger.info("Configuring performance pragmas...")
    cursor.execute("PRAGMA synchronous = NORMAL;")
    cursor.execute("PRAGMA temp_store = MEMORY;")
    cursor.execute("PRAGMA mmap_size = 30000000000;")
    cursor.execute("PRAGMA cache_size = 10000;")

    # Optimize database
    logger.info("Running VACUUM to optimize database...")
    start_time = time()
    cursor.execute("VACUUM;")
    logger.info(f"Completed VACUUM in {time() - start_time:.2f} seconds")

    cursor.close()
    conn.commit()


def validate_database(conn):
    """Run integrity check on database."""
    cursor = conn.cursor()

    logger.info("Running integrity check...")
    cursor.execute("PRAGMA integrity_check;")
    integrity_result = cursor.fetchone()[0]

    if integrity_result == "ok":
        logger.info("Database integrity check passed")
    else:
        logger.error(f"Database integrity check failed: {integrity_result}")

    cursor.close()
    return integrity_result == "ok"


def run_query_tests(conn):
    """Run test queries to validate index performance."""
    cursor = conn.cursor()

    query_tests = [
        {
            "name": "Players by position",
            "query": "SELECT * FROM players WHERE position = 'QB';",
        },
        {
            "name": "Fantasy-relevant players",
            "query": "SELECT * FROM players WHERE position IN ('QB', 'RB', 'WR', 'TE') AND status = 'Active' AND team IS NOT NULL AND team != '' AND team != 'FA';",
        },
        {
            "name": "Projections by player and season",
            "query": "SELECT * FROM projections WHERE player_id IN (SELECT player_id FROM players WHERE position = 'QB') AND season = 2024;",
        },
        {
            "name": "Team stats by team and season",
            "query": "SELECT * FROM team_stats WHERE team = 'KC' AND season = 2024;",
        },
        {
            "name": "Top projections by fantasy points",
            "query": "SELECT p.*, pl.name, pl.position, pl.team FROM projections p JOIN players pl ON p.player_id = pl.player_id WHERE p.season = 2024 ORDER BY p.half_ppr DESC LIMIT 20;",
        },
    ]

    results = []
    for test in query_tests:
        logger.info(f"Running query test: {test['name']}")

        # First run with timer
        start_time = time()
        cursor.execute(test["query"])
        rows = cursor.fetchall()
        execution_time = time() - start_time

        results.append({"name": test["name"], "rows": len(rows), "time": execution_time})

        logger.info(f"Query returned {len(rows)} rows in {execution_time:.4f} seconds")

    cursor.close()
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Apply database performance optimizations and indexes"
    )
    parser.add_argument("--db_path", help="Path to database file", default=DEFAULT_DB_PATH)
    parser.add_argument("--test", action="store_true", help="Run on test database")
    parser.add_argument("--force", action="store_true", help="Force recreation of indices")
    parser.add_argument(
        "--validate_only", action="store_true", help="Only run validation without creating indices"
    )
    parser.add_argument("--optimize", action="store_true", help="Run additional optimizations")
    args = parser.parse_args()

    # Determine database path
    db_path = TEST_DB_PATH if args.test else args.db_path

    # Check if database exists
    if not os.path.exists(db_path):
        logger.error(f"Database file not found: {db_path}")
        return 1

    logger.info(f"Opening database at {db_path}")
    conn = sqlite3.connect(db_path)

    try:
        # Run validation if requested
        if args.validate_only:
            is_valid = validate_database(conn)
            run_query_tests(conn)
            return 0 if is_valid else 1

        # Create indexes
        created_count = create_indexes(conn, args.force)
        logger.info(f"Created {created_count} new indexes")

        # Run additional optimizations if requested
        if args.optimize:
            optimize_database(conn)

        # Validate database and run query tests
        is_valid = validate_database(conn)
        run_query_tests(conn)

        if not is_valid:
            logger.error("Database validation failed after index creation")
            return 1

        logger.info("Database optimization completed successfully")
        return 0

    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
