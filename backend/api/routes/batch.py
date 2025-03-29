from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any

from backend.database.database import get_db
from backend.services.batch_service import BatchService
from backend.services.cache_service import get_cache
from backend.api.schemas import (
    BatchProjectionCreateRequest,
    BatchProjectionAdjustRequest,
    BatchResponse,
    BatchScenarioCreateRequest,
    ExportFiltersRequest
)

router = APIRouter(
    prefix="/batch",
    tags=["batch operations"]
)

@router.post("/projections/create", response_model=BatchResponse)
async def batch_create_projections(
    request: BatchProjectionCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Create projections for multiple players in a single operation.
    
    Efficient batch operation for creating baseline projections
    for multiple players at once.
    """
    service = BatchService(db)
    result = await service.batch_create_projections(
        player_ids=request.player_ids,
        season=request.season,
        scenario_id=request.scenario_id
    )
    
    if result["success"] == 0 and result["failure"] > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to create any projections. {result.get('error', '')}"
        )
        
    return result

@router.post("/projections/adjust", response_model=BatchResponse)
async def batch_adjust_projections(
    request: BatchProjectionAdjustRequest,
    db: Session = Depends(get_db)
):
    """
    Apply adjustments to multiple projections in a single operation.
    
    Efficient batch operation for adjusting multiple projections
    at once with different adjustment values.
    """
    service = BatchService(db)
    result = await service.batch_adjust_projections(
        adjustments=request.adjustments
    )
    
    if result["success"] == 0 and result["failure"] > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to adjust any projections. {result.get('error', '')}"
        )
        
    return result

@router.post("/scenarios/create", response_model=BatchResponse)
async def batch_create_scenarios(
    request: BatchScenarioCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Create multiple projection scenarios in a single operation.
    
    Efficient batch operation for creating multiple scenarios
    with different settings and adjustments.
    """
    service = BatchService(db)
    result = await service.batch_create_scenarios(
        scenario_templates=request.scenarios
    )
    
    if result["success"] == 0 and result["failure"] > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to create any scenarios. {result.get('error', '')}"
        )
        
    return result

@router.post("/export")
async def export_projections(
    request: ExportFiltersRequest,
    format: str = Query("csv", regex="^(csv|json)$"),
    include_metadata: bool = False,
    db: Session = Depends(get_db)
):
    """
    Export projections in CSV or JSON format.
    
    Advanced export functionality with filtering capabilities.
    Supports CSV and JSON formats with optional metadata.
    """
    service = BatchService(db)
    
    try:
        filename, content = await service.export_projections(
            format=format,
            filters=request.filters,
            include_metadata=include_metadata
        )
        
        # Set the appropriate media type
        media_type = "text/csv" if format.lower() == "csv" else "application/json"
        
        # Return the file as a downloadable response
        return StreamingResponse(
            iter([content]),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to export projections: {str(e)}"
        )

@router.get("/cache/stats")
async def get_cache_stats(
    db: Session = Depends(get_db)
):
    """
    Get cache statistics (admin only).
    
    Returns statistics about the application's cache usage.
    """
    cache = get_cache()
    return cache.get_stats()

@router.post("/cache/clear")
async def clear_cache(
    pattern: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Clear all or part of the cache (admin only).
    
    Clears the application cache, optionally only entries
    matching the specified pattern.
    """
    cache = get_cache()
    
    if pattern:
        count = cache.clear_pattern(pattern)
        return {"status": "success", "cleared_entries": count}
    else:
        cache.clear()
        return {"status": "success", "message": "Cache cleared"}