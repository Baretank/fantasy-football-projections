# Active Player Service Integration

## Overview
The `ActivePlayerService` is a service that filters players based on an active roster stored in a CSV file. This service is used to ensure that projections and player data only include players who are currently active in the NFL, improving the accuracy and relevance of fantasy football projections.

## Implementation Status
The core implementation of the ActivePlayerService is complete. The service:
1. Loads a list of active players from `data/active_players.csv`
2. Provides a `filter_active()` method that filters pandas DataFrames based on player name and team
3. Is currently used in the `NFLDataImportService` to filter out inactive players during import

## Integration Tests
Three types of tests have been implemented to verify the service works correctly:
1. **Unit tests** - Testing the core functionality of the service
2. **Integration tests** - Testing the service's interaction with the NFL data import pipeline
3. **System tests** - Testing the end-to-end flow including active player filtering

## Requirements for Full Integration

### 1. Ensure active_players.csv is Up-to-Date
- The `data/active_players.csv` file should be regularly updated with the current NFL roster
- Required columns: `name`, `team`, `position`, `player_id` (optional but recommended)
- Suggested updates: before each NFL season and after major roster changes

### 2. NFLDataImportService Integration
- ✅ The `NFLDataImportService` already incorporates the `ActivePlayerService` in its import_players method
- Ensure proper error handling when active player filtering fails (already implemented)
- Add logging to track how many players are filtered out

### 3. Query Service Integration
- Update the `QueryService` to only return active players in query results
- Implement a parameter to optionally include inactive players when needed

### 4. Projection Service Integration
- Ensure `ProjectionService` only generates projections for active players
- Adjust fill player logic to only use active players

### 5. Update Documentation
- Document the purpose and usage of the `ActivePlayerService`
- Add instructions for maintaining the `active_players.csv` file
- Document the format and required fields for the CSV

### 6. Future Improvements
- Implement a mechanism to automatically update the active players list
- Add an API endpoint to view and manage the active player list
- Extend the service to handle player status changes during the season

## Implementation Checklist
- [x] Create `ActivePlayerService` class with CSV loading functionality
- [x] Add `filter_active()` method to filter DataFrames
- [x] Integrate with `NFLDataImportService`
- [x] Create unit tests for core functionality
- [x] Create integration tests with import pipeline
- [x] Create system tests for end-to-end verification
- [ ] Update `QueryService` to respect active player filtering
- [ ] Update `ProjectionService` to only include active players
- [ ] Add documentation about maintaining the active_players.csv file
- [ ] Implement CLI tool to update active_players.csv

## Running the Tests
To run the unit tests for the ActivePlayerService:
```bash
cd backend
python -m pytest "tests/unit/test_active_player_service.py" -v
```

To run the integration tests:
```bash
cd backend
python -m pytest "tests/integration/test_active_player_integration.py" -v
```

To run the system tests:
```bash
cd backend
python -m pytest "tests/system/test_active_player_system.py" -v
```