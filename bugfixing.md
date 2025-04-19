# Bug Fixes

## 1. Rookies Not Iterable - Fixed

**Issue:**
- Error in draftdaytool.tsx: "rookies is not iterable" at line 189
- Caused by the getRookies API function not correctly handling the backend API response format and potential errors

**Solution:**
- Updated the `getRookies` method in api.ts to properly handle the backend API response structure
- Added defensive response handling to check for different possible response formats (array, object with players array, etc.)
- Added proper fallback to empty array instead of throwing errors
- This maintains consistent behavior with other similar API methods like getPlayers

**Changes:**
- Modified `/frontend/src/services/api.ts` to properly handle the response and prevent "rookies is not iterable" errors
- Ensured full error handling and proper empty array returns for API request failures

## 2. Backend Startup Error - Fixed

**Issue:**
- Error when starting the backend with uvicorn
- TypeError in typing_pandas.py: "Cannot create a consistent method resolution order (MRO) for bases Generic, Sized"
- This is a Python inheritance conflict with multiple inheritance using Generic[T] and Sized

**Solution:**
- Simplified the TypedDataFrame class definition in typing_pandas.py
- Removed unnecessary Sized class inheritance since __len__ method is implemented directly
- Python's Method Resolution Order (MRO) requires a consistent inheritance hierarchy

**Changes:**
- Modified `/backend/services/typing_pandas.py` to fix the inheritance issue
- Removed custom Sized Protocol and the explicit inheritance from it
- The class now only inherits from Generic[T] which resolves the MRO conflict

## 3. Missing Batch Router Import - Fixed

**Issue:**
- Error when starting the backend with uvicorn after fixing the MRO issue
- ImportError: cannot import name 'batch_router' from 'backend.api.routes'
- The batch.py file exists but wasn't being exported from routes/__init__.py

**Solution:**
- Added the missing import and export for the batch router in routes/__init__.py
- This ensures the router is properly exported and available for import in api/__init__.py

**Changes:**
- Modified `/backend/api/routes/__init__.py` to import and export the batch_router
- Added `from backend.api.routes.batch import router as batch_router` to the imports
- Added "batch_router" to the __all__ list to properly export it

## 4. Scenario Cloning Functionality - Fixed

**Issue:**
- The scenario cloning functionality had an issue where the base_scenario_id wasn't being set correctly
- The issue was in the ScenarioService.clone_scenario method where the base_scenario_id was set after scenario creation

**Solution:**
- Modified the clone_scenario method to include the base_scenario_id during the initial scenario creation
- This ensures the proper parent-child relationship between scenarios is established from the start

**Changes:**
- Modified `/backend/services/scenario_service.py` to pass the base_scenario_id directly during scenario creation
- Removed redundant code that was setting the base_scenario_id after creating the scenario

## 5. Target Share and Usage Calculations - Fixed

**Issue:**
- There were inconsistencies in how target_share values were applied across different player positions
- For WR/TE players, the target_share was stored directly as the adjustment factor value
- For other positions, the target_share was used as a multiplier, creating inconsistent behavior
- Tests were failing with TypeError due to None values in calculations: "'>' not supported between instances of 'NoneType' and 'int'"

**Solution:**
- Standardized the approach to target_share and rush_share adjustments across all positions
- Added a helper method _safe_calculate_share_factor to safely calculate relative multipliers
- Implemented proper min/max bounds to ensure values stay within reasonable ranges
- Added comprehensive null-safety checks throughout the adjustment methods
- Fixed potential division by zero errors and type errors in calculations

**Changes:**
- Modified `/backend/services/projection_service.py` to standardize target_share handling:
  - Added _safe_calculate_share_factor helper function for safe share calculations
  - Updated the update_projection method for WR/TE adjustments
  - Updated the update_projection method for RB adjustments
  - Updated the _adjust_receiver_stats and _adjust_rb_stats methods for consistency
  - Added proper null-safety checks and min/max bounds
  - Improved calculation of derived statistics like catch_pct and yards_per_target
  - Enhanced error handling throughout to prevent TypeErrors and ZeroDivisionErrors


## 6. Players.filter is not a function - Fixed

**Issue:**
- Error in dashboard.tsx: "players.filter is not a function" at line 107
- This occurred because the API was returning an object with a players property instead of an array directly
- In the dashboard component, the code was trying to filter the response directly, but it wasn't an array

**Solution:**
- Modified the getPlayers method in api.ts to always return an array, regardless of the API response format
- Added defensive checks to handle different response formats (object with players array, direct array, etc.)
- Updated the getFilteredAndSortedPlayers function in dashboard.tsx to validate that players is an array before filtering
- Added null safety checks for player properties to prevent errors when filtering and sorting

**Changes:**
- Modified `/frontend/src/services/api.ts` to standardize the return value of getPlayers to always be an array
- Modified `/frontend/src/components/dashboard.tsx` to add additional array type checking before filtering
- Added additional null safety checks for player properties during filtering and sorting operations
- Improved error handling for scenario and projection loading to ensure consistent state

## 7. Player Data Filtering - Fixed

**Issue:**
- Dashboard showing "No players found" when using the getPlayersOverview method
- API was returning an empty player list when filtering by 'Active' status
- Database inspection revealed that the database uses different status codes ('ACT', 'RET', etc.) instead of 'Active'
- Logs showed empty result sets when filtering by 'Active' status

**Solution:**
- Removed the automatic status filtering since database uses different status codes than expected
- Implemented client-side filtering for fantasy-relevant positions (QB, RB, WR, TE)
- Added improved debugging and data inspection in the dashboard component
- Made the status parameter in API requests optional to avoid incorrect filtering

**Changes:**
- Modified `/frontend/src/services/api.ts` to make status parameter optional
- Updated dashboard component to filter fantasy-relevant positions client-side
- Added comprehensive debugging to identify where and why players were being filtered out
- Discovered database status codes: 'ACT' (active), 'RET' (retired), etc. that didn't match our 'Active' filter

## Current Issues

