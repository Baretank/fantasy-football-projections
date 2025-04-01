# Fantasy Football Projections Testing Plan

## Test Results Summary (April 2025)
Total tests: 410
Passing: 409
Failing: 1 (test_season_upload.py::TestDataImport::test_full_import_pipeline - missing fixture)

## Testing Structure
- **Unit Tests**: Individual components in isolation
- **Integration Tests**: Interactions between components
- **System Tests**: Complete workflows end-to-end

## Core Service Test Status (All Passing ✓)
- **Data Service** - Player data retrieval, stat aggregation
- **NFL Data Import Service** - Adapter integration, data processing
- **Projection Service** - Projection calculation, position-specific stats
- **Team Stat Service** - Team adjustments, player share calculations
- **Scenario Service** - Scenario creation and application
- **Override Service** - Player stat overrides, cascade effects
- **Cache Service** - Cache hit/miss behavior, invalidation

## API Routes Integration Tests (All Passing ✓)
- **Players Routes** - Player retrieval, filtering, search
- **Projections Routes** - Calculation, filtering, aggregation
- **Scenarios Routes** - Creation/modification, application
- **Overrides Routes** - Application, validation, removal
- **Batch Routes** - Import functionality, progress tracking

## System Tests
- **Export Processes** (✓) - 4/4 tests passing
- **End-to-End Flows** (✓) - 5/5 tests passing
- **Import/Projection Flow** (✓) - 9/9 tests passing
- **Draft Day Tools** (⟳) - Test framework created, needs implementation
- **Performance Testing** (⟳) - Test framework created, needs implementation

## Component Test Status
1. ✓ Veteran player projection tests - 5/5 tests passing
2. ✓ Rookie projection tests - 5/5 tests passing
3. ✓ Team adjustment tests - 5/5 tests passing
4. ✓ Scenario tests - 5/5 tests passing
5. ✓ Override tests - 6/6 tests passing
6. ✓ NFL data import tests - 9/9 tests passing
7. ✓ Export processes - 4/4 tests passing

## Running Tests
Use the provided bash script for specific test categories:
```bash
./tests/system/run_tests.sh veteran   # Run veteran projection tests
./tests/system/run_tests.sh rookie    # Run rookie projection tests
./tests/system/run_tests.sh team      # Run team adjustment tests
./tests/system/run_tests.sh scenario  # Run scenario tests
./tests/system/run_tests.sh override  # Run override tests
./tests/system/run_tests.sh components # Run all component tests
./tests/system/run_tests.sh pipeline  # Run complete pipeline test
./tests/system/run_tests.sh e2e       # Run end-to-end flow tests
./tests/system/run_tests.sh import    # Run import/export tests
```

## Standardization Efforts
- **Fantasy Point Fields** (✓) - Using half_ppr consistently
- **Rush Attempts Standardization** (✓) - Using rush_attempts consistently

## Known Technical Debt
- **FastAPI Deprecation Warnings**:
  - Replace `regex` with `pattern` in Query parameters
  - Replace `on_event` with lifespan event handlers
- **SQLAlchemy Legacy Warnings**:
  - Replace Query.get() with Session.get()
- **Pydantic Deprecation Warnings**:
  - Replace class-based `config` with ConfigDict
  - Use `json_schema_extra` instead of extra keyword arguments on Field

## Next Steps
1. Implement Draft Day Tool API endpoints
2. Implement Performance Testing endpoints
3. Fix the failing test in test_season_upload.py
4. Address technical debt and deprecation warnings