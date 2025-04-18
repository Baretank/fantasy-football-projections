from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
import time
import datetime
import psutil
import platform
import os
import gc
import json

from backend.database.database import get_db
from backend.services.cache_service import get_cache
from backend.database.models import Player, Projection, BaseStat, TeamStat

router = APIRouter()


@router.get("/metrics")
async def get_performance_metrics(db: Session = Depends(get_db)):
    """
    Get system performance metrics including database size, cache status, and memory usage.
    """
    start_time = time.time()

    # Get database metrics
    db_metrics = {}

    # Get table counts
    player_count = db.query(Player).count()
    projection_count = db.query(Projection).count()
    stats_count = db.query(BaseStat).count()
    team_stats_count = db.query(TeamStat).count()

    db_metrics["tables"] = {
        "players": player_count,
        "projections": projection_count,
        "stats": stats_count,
        "team_stats": team_stats_count,
    }
    db_metrics["total_records"] = sum(db_metrics["tables"].values())

    # Get system metrics
    system_metrics = {
        "platform": platform.platform(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "cpu_count": os.cpu_count(),
    }

    # Get memory metrics
    memory = psutil.virtual_memory()
    memory_metrics = {
        "total_memory_mb": memory.total / (1024 * 1024),
        "available_memory_mb": memory.available / (1024 * 1024),
        "used_memory_mb": memory.used / (1024 * 1024),
        "memory_percent": memory.percent,
    }

    # Get process metrics
    process = psutil.Process(os.getpid())
    process_metrics = {
        "process_memory_mb": process.memory_info().rss / (1024 * 1024),
        "process_cpu_percent": process.cpu_percent(),
        "process_threads": process.num_threads(),
        "process_open_files": len(process.open_files()),
    }

    # Get cache metrics
    cache = get_cache()
    cache_metrics = cache.get_stats()

    # Calculate response time
    end_time = time.time()
    response_time = end_time - start_time

    return {
        "timestamp": datetime.datetime.now().isoformat(),
        "database": db_metrics,
        "system": system_metrics,
        "memory": memory_metrics,
        "process": process_metrics,
        "cache": cache_metrics,
        "response_time_seconds": response_time,
    }


@router.post("/cache/clear")
async def clear_cache():
    """Clear the application cache."""
    cache = get_cache()
    entries_cleared = cache.clear()
    return {"success": True, "entries_cleared": entries_cleared}


@router.post("/cache/cleanup")
async def clean_cache():
    """Remove expired entries from the cache."""
    cache = get_cache()
    removed = cache.cleanup()
    return {"success": True, "entries_removed": removed}


@router.post("/gc")
async def run_garbage_collection():
    """Run Python garbage collection manually."""
    start_time = time.time()
    collected = gc.collect()
    end_time = time.time()

    return {
        "success": True,
        "objects_collected": collected,
        "execution_time_seconds": end_time - start_time,
    }


@router.get("/query-time")
async def measure_query_time(
    table: str = Query(..., pattern="^(players|projections|base_stats|team_stats)$"),
    limit: int = Query(100, ge=1, le=1000),
    filter_type: Optional[str] = Query(None, pattern="^(position|team|season)$"),
    filter_value: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Measure query execution time for different tables and filters.

    Parameters:
    - table: Table to query (players, projections, base_stats, team_stats)
    - limit: Maximum number of records to retrieve
    - filter_type: Optional filter type (position, team, season)
    - filter_value: Value for the filter

    Returns:
    - Query execution metrics
    """
    start_time = time.time()

    # Build query based on selected table
    if table == "players":
        query = db.query(Player)

        if filter_type == "position":
            query = query.filter(Player.position == filter_value)
        elif filter_type == "team":
            query = query.filter(Player.team == filter_value)

    elif table == "projections":
        query = db.query(Projection)

        if filter_type == "season":
            query = query.filter(Projection.season == int(filter_value))

    elif table == "base_stats":
        query = db.query(BaseStat)

        if filter_type == "season":
            query = query.filter(BaseStat.season == int(filter_value))

    elif table == "team_stats":
        query = db.query(TeamStat)

        if filter_type == "season":
            query = query.filter(TeamStat.season == int(filter_value))
        elif filter_type == "team":
            query = query.filter(TeamStat.team == filter_value)

    # Apply limit
    query = query.limit(limit)

    # Execute query and measure time
    query_start = time.time()
    results = query.all()
    query_end = time.time()

    # Calculate times
    query_time = query_end - query_start
    full_time = time.time() - start_time

    return {
        "table": table,
        "filter": {"type": filter_type, "value": filter_value},
        "limit": limit,
        "record_count": len(results),
        "query_time_seconds": query_time,
        "total_time_seconds": full_time,
    }


@router.get("/cached-query-comparison")
async def compare_cached_vs_uncached(
    table: str = Query(..., pattern="^(players|projections)$"),
    filter_type: Optional[str] = Query(None, pattern="^(position|team|season)$"),
    filter_value: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Compare performance between cached and uncached queries.

    Parameters:
    - table: Table to query (players, projections)
    - filter_type: Optional filter type (position, team, season)
    - filter_value: Value for the filter

    Returns:
    - Performance comparison between cached and uncached queries
    """
    cache = get_cache()

    # Generate a unique cache key for this query
    cache_key = f"perf_test_{table}_{filter_type}_{filter_value}"

    # Clear this specific entry if it exists
    cache.delete(cache_key)

    # First run: uncached
    uncached_start = time.time()

    # Build query based on selected table
    if table == "players":
        query = db.query(Player)

        if filter_type == "position":
            query = query.filter(Player.position == filter_value)
        elif filter_type == "team":
            query = query.filter(Player.team == filter_value)

    elif table == "projections":
        query = db.query(Projection)

        if filter_type == "season":
            query = query.filter(Projection.season == int(filter_value))

    # Execute uncached query
    uncached_results = query.all()
    uncached_time = time.time() - uncached_start

    # Store in cache
    cache.set(cache_key, [obj.__dict__ for obj in uncached_results])

    # Second run: should use cache
    cached_start = time.time()
    cached_results = cache.get(cache_key)
    cached_time = time.time() - cached_start

    # Calculate improvement
    time_diff = uncached_time - cached_time
    if uncached_time > 0:
        improvement_percent = (time_diff / uncached_time) * 100
    else:
        improvement_percent = 0

    return {
        "table": table,
        "filter": {"type": filter_type, "value": filter_value},
        "record_count": len(uncached_results),
        "uncached_time_seconds": uncached_time,
        "cached_time_seconds": cached_time,
        "time_difference_seconds": time_diff,
        "improvement_percent": improvement_percent,
        "speedup_factor": uncached_time / max(cached_time, 0.0001),  # Avoid division by zero
    }


@router.get("/database-index-analysis")
async def analyze_database_indexes(db: Session = Depends(get_db)):
    """
    Analyze database table sizes and suggest indexes.

    Returns:
    - Analysis of database tables and suggested indexes
    """
    # Get table sizes
    tables = {
        "players": db.query(Player).count(),
        "projections": db.query(Projection).count(),
        "base_stats": db.query(BaseStat).count(),
        "team_stats": db.query(TeamStat).count(),
    }

    # Common query patterns by table
    query_patterns = {
        "players": [
            "Player.position (equality)",
            "Player.team (equality)",
            "Player.name (LIKE/search)",
            "Player.player_id (primary key lookup)",
        ],
        "projections": [
            "Projection.player_id (equality)",
            "Projection.scenario_id (equality)",
            "Projection.season (equality)",
            "Projection.half_ppr (range)",
            "Projection.player_id + Projection.season (composite)",
        ],
        "base_stats": [
            "BaseStat.player_id (equality)",
            "BaseStat.season (equality)",
            "BaseStat.stat_type (equality)",
            "BaseStat.player_id + BaseStat.stat_type (composite)",
        ],
        "team_stats": [
            "TeamStat.team (equality)",
            "TeamStat.season (equality)",
            "TeamStat.team + TeamStat.season (composite)",
        ],
    }

    # Suggested indexes based on table size
    suggested_indexes = {}

    for table, count in tables.items():
        if count > 1000:
            # For larger tables, recommend more indexes
            suggested_indexes[table] = query_patterns[table]
        elif count > 100:
            # For medium tables, recommend primary lookup patterns
            suggested_indexes[table] = query_patterns[table][:2]
        else:
            # For small tables, primary key is usually sufficient
            suggested_indexes[table] = ["Primary key only"]

    return {
        "table_sizes": tables,
        "total_records": sum(tables.values()),
        "common_query_patterns": query_patterns,
        "suggested_indexes": suggested_indexes,
    }
