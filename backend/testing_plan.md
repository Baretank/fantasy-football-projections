# Fantasy Football Projections Testing Plan

## Testing Philosophy
- Test-driven development where possible
- Aim for high coverage of core business logic
- Prioritize testing critical data flows and user journeys

## Test Structure
- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test interactions between components
- **System Tests**: Test complete workflows end-to-end

## Recommended Testing Order
1. **Unit Tests**
   - ✓ Data Service Tests (foundation for all other services)
   - ✓ Data Import/Validation Services (ensures data quality)
   - ✓ Projection Service (core business logic)
   - ✓ Team Stat Service (team-level adjustments)
   - ✓ Scenario Service (depends on projection service)
   - ✓ Override Service (affects projections and scenarios)
   - Cache Service (performance optimization)
   
2. **Integration Tests**
   - API Route Integration Tests ✓
     - ✓ Players Routes tests
     - ✓ Projections Routes tests
     - ✓ Scenarios Routes tests
     - ✓ Overrides Routes tests
     - ✓ Batch Routes tests
   - Projection Pipeline (core data flow) ✓
   - ✓ Override and Projection Integration
   - ✓ Rookie and Veteran Player Integration

3. **System Tests**
   - ⟳ Import/Export Processes (data foundation)
   - ⟳ End-to-End Flows (user journeys)
   - Performance Testing (optimization)

## Unit Testing Plan

### Service Layer Tests
  
- **Data Service** ✓
  - Player data retrieval and filtering
  - Stat aggregation and calculation
  - Data transformation functions

- **Data Import/Validation Services** ✓
  - CSV/JSON parsing accuracy
  - Data validation rules
  - Error handling for malformed data
  - Rate limiting functionality

- **Projection Service** ✓
  - Accurate calculation of projections
  - Proper handling of position-specific stats
  - Variance calculations and range projections
  
- **Team Stat Service** ✓
  - Team statistics import and validation
  - Team adjustment calculation
  - Applying team-level adjustments to player projections
  
- **Scenario Service** ✓
  - Scenario creation and application
  - Impact calculations on projections
  - Scenario comparison functionality

- **Override Service** ✓
  - Player stat overrides
  - Override cascade effects
  - Override conflict resolution
  - Fantasy point recalculation after overrides

- **Cache Service**
  - Cache hit/miss behavior
  - Cache invalidation
  - Memory management

## Integration Testing Plan

### API Routes Integration Tests
- **Players Routes** ✓
  - Player retrieval endpoints
  - Player filtering and search
  - Response schema validation

- **Projections Routes** ✓
  - Projection calculation endpoints
  - Filtering and aggregation
  - Performance with large datasets

- **Scenarios Routes** ✓
  - Scenario creation/modification
  - Scenario application
  - Response validation

- **Overrides Routes** ✓
  - Override application endpoints
  - Validation of override inputs
  - Override removal functionality

- **Batch Routes** ✓
  - Batch import functionality
  - Progress tracking
  - Error handling and reporting

### Service Interactions
- **Projection Pipeline** ✓
  - Data flow from import → processing → projections
  - Service communication and data handoffs
  - Error propagation between services
  - Team stat adjustments integration with player projections

- **Override and Projection Integration** ✓
  - Override effects on projection calculations
  - Performance under multiple overrides
  - Position-specific stat recalculation with overrides

- **Rookie and Veteran Player Integration** ✓
  - Unified player database operations
  - Template application for rookies

### Database Interactions
- Service to database operations
- Transaction integrity across services
- Race condition handling

## System Testing Plan

### End-to-End Flows
- **Player Data Management**
  - Import → View → Update → Project workflow
  - Performance with full dataset

- **Projection Generation**
  - Generate all player projections
  - Apply scenarios
  - Export results

- **Draft Day Tools**
  - Real-time projection updates
  - Draft tracking functionality

### Import/Export Processes
- **Season Data Upload**
  - Full season data import
  - Data validation
  - Performance with large datasets

- **Projection Export**
  - Format correctness
  - Completeness of data

## Performance Testing
- Response times under load
- Database query optimization
- Caching effectiveness
- Memory usage monitoring

## Test Coverage Goals
- 90%+ coverage for core services
- 80%+ coverage for API routes
- 75%+ coverage for edge cases and error handling

## Progress Update (Current Status)
- ✓ Fixed Data Service tests and implementation
- ✓ Fixed Data Validation tests and implementation
- ✓ Fixed Projection Service tests and implementation
- ✓ Fixed Team Stat Service tests and implementation
- ✓ Fixed Scenario Service tests and implementation
- ✓ Fixed Override Service tests and implementation
- ✓ Added Override-Projection integration tests
- ✓ Created individual API Route test files
- ✓ Implemented API integration test framework 
  - ✓ Created test fixtures for database and test data
  - ✓ Fixed players route integration tests
  - ✓ Fixed projections route integration tests
  - ✓ Fixed scenarios route integration tests
  - ✓ Fixed overrides route integration tests
  - ✓ Fixed batch route integration tests
- ✓ Fixed Projection Pipeline integration tests
- ✓ Completed Integration tests for player imports
  - ✓ Implemented tests for Rookie Import (CSV, JSON)
  - ✓ Implemented tests for Veteran Player Import
  - ✓ Implemented tests for Rookie Projection creation
  - ✓ Implemented tests for Rookie Projection Templates
- ✓ Enhanced Batch Service with robust error handling
  - ✓ Added BatchService.process_batch method for batch operations
  - ✓ Implemented circuit breaker pattern to prevent cascading failures
  - ✓ Added error logging to ImportLog table for better diagnostics
  - ✓ Added batch processing tests for success and failure cases
- ✓ Improved Data Import Service robustness
  - ✓ Enhanced request backoff algorithm with jitter for rate limiting
  - ✓ Added proper error handling for network and service errors
  - ✓ Fixed external response handling tests
- ✓ Improved System Test organization
  - ✓ Split end-to-end tests into component tests for better debugging
  - ✓ Created test_veteran_player_projections.py and fixed fantasy point field issues
  - ✓ Created test runner script (run_tests.sh) for focused component testing
  - ✓ Documented test issues and standardization plans
  - ✓ Fixed method naming confusion in TeamStatService
- ✓ Standardized on rush_attempts field name
  - ✓ Updated database models to use rush_attempts consistently
  - ✓ Removed carries field from TeamStat model
  - ✓ Updated from_dict method to handle rush_attempts instead of carries
  - ✓ Fixed car_pct to rush_att_pct in Projection model
  - ✓ Fixed TeamStatService to use rush_attempts consistently
- ⟳ Still in progress: System test component fixes
  - ✓ Fixed team-level adjustment implementation
    - ✓ Fixed apply_team_adjustments in TeamStatService
    - ✓ Fixed test_team_adjustments.py to store original values before applying changes
    - ✓ Fixed proper application of scoring_rate adjustments
    - ✓ Fixed proper application of player_share adjustments
  - ⟳ Fixing RookieProjectionService
  - ✓ Resolved fantasy point field inconsistencies across all tests
  - ⟳ Fixing scenario adjustment issues
- ⟳ Need to complete Service Interactions tests
  - ✓ Team-level adjustment integration tests
  - ✓ Player share adjustments tests
  - ⟳ Complete projection pipeline integration tests
- ⟳ Need to complete System tests
  - ⟳ Import/Export Processes
  - ⟳ End-to-End Flows
  - ⟳ Performance Testing

## Breaking Down the Large Test

Rather than trying to fix the complete_season_pipeline test directly, we've broken it down into smaller, focused component tests:

1. ✓ Veteran player projection tests
2. ⟳ Rookie projection tests
3. ✓ Team adjustment tests
4. ⟳ Scenario tests
5. ✓ Override tests

This divide-and-conquer approach makes it easier to identify and fix specific issues. Once all components are working correctly, we can focus on integrating them in the complete pipeline test.

## Key Standardization Efforts

### 1. Fantasy Point Fields Standardization (COMPLETED)
- Standardized on only using the half_ppr field, as it's the only field that exists in the Projection model
- Updated all tests to use half_ppr consistently
- Removed references to standard and ppr fields in test files

### 2. Rush Attempts Standardization (COMPLETED)
- Standardized on using rush_attempts consistently throughout the codebase
- Removed carries field from TeamStat model
- Updated TeamStatService to use rush_attempts everywhere
- Fixed Projection model to use rush_att_pct instead of car_pct
- Updated all tests to use rush_attempts consistently

## Current Issues Being Addressed

1. ✓ TeamStatService.apply_team_adjustments() not applying adjustments correctly
   - Fixed pass volume adjustments issue
   - Fixed scoring rate adjustments to be applied independently of volume adjustments
   - Fixed player share adjustments implementation
   - Fixed test suite to verify adjustments are correctly applied

2. ⟳ RookieProjectionService not properly creating/saving projections
   - Need to fix creation and persistence of rookie projections
   - Need to fix rookie projection template application

3. ⟳ ScenarioService issues with projection adjustments
   - Projection adjustments not being correctly applied through scenarios
   - Need to fix scenario application logic

## Next Steps

1. ⟳ Fix RookieProjectionService
   - Fix rookie projection creation and persistence
   - Complete rookie projection tests

2. ⟳ Resolve scenario adjustment issues
   - Fix ScenarioService to correctly apply adjustments
   - Verify adjustments are properly reflected in projections

3. ⟳ Reintegrate component tests
   - After fixing individual components, reintegrate into end-to-end test
   - Verify complete season pipeline works correctly

4. ⟳ Complete remaining system tests
   - Implement/fix import/export process tests
   - Complete draft day tool tests
   - Add performance testing

## Running Tests

Use the provided bash script to run specific test categories:

```bash
./tests/system/run_tests.sh veteran   # Run just veteran projection tests
./tests/system/run_tests.sh rookie    # Run just rookie projection tests
./tests/system/run_tests.sh components # Run all component tests
./tests/system/run_tests.sh pipeline  # Run the complete pipeline test
```

## Test Data Management
- Create comprehensive test fixtures
- Use realistic sample datasets
- Maintain separation between test and production data

## Continuous Integration
- Run unit tests on every PR
- Run integration tests nightly
- Run system tests before releases
- Track and report coverage trends

## Test Tooling
- pytest for test execution
- pytest-asyncio for async testing
- pytest-cov for coverage reporting
- Mock for unit test isolation

## Test Fixture Strategy
- Create base fixtures for database and test data
- Use factory patterns for generating test entities
- Implement scoped fixtures to optimize performance
- Use parametrized tests for comprehensive test coverage

## API Integration Testing Approach
Our approach to API testing is to use integration tests that test the full application stack:

1. We use the pytest fixture system to create a test version of the full application
2. A test client fixture connects to the test application
3. Database fixtures create test data
4. Tests verify full API flows rather than isolated routes
5. We focus on data integrity and response validation

This approach provides better test coverage for real-world usage patterns and is more maintainable than isolated unit tests for each API route.