# Next Steps for Fantasy Football Projections App

## Data Import and Verification
- [x] Add data verification checks to upload_season.py
- [x] Implement validation for game counts and season totals
- [x] Add handling for missing required stats
- [x] Improve error reporting during data imports
- [x] Add unit tests for data validation service

## Projection Engine Enhancements
- [x] Finalize rookie projection methodology
- [x] Add support for team-level statistical adjustments
- [x] Implement projection variance/confidence intervals
- [x] Support historical comparisons with past seasons

## API Improvements
- [x] Add batch operations for projections
- [x] Implement caching for frequently accessed data
- [x] Optimize query performance for player listings
- [x] Add endpoints for exporting projection data

## Frontend Development
- [x] Create comprehensive navigation structure
- [x] Build dashboard view for overall projection analysis
- [x] Implement side-by-side player comparison view
- [x] Add visualization components for showing projection ranges

## Testing and Quality Assurance
- [x] Add unit tests for data validation
- [x] Expand unit test coverage for projection algorithms
- [x] Add integration tests for the complete projection pipeline
- [x] Implement end-to-end tests for critical user flows
- [x] Add comprehensive tests for the override service
- [x] Add integration tests for override-projection interaction
- [x] Implement NFL data import testing framework
- [x] Refactor tests to use new NFLDataImportService API
- [x] Add comprehensive mocking for external data sources
- [x] Improve async test patterns with proper AsyncMock usage
- [x] Add detailed debugging output to stabilize tests
- [x] Complete API route tests with schema validation fixes
  - [x] Fixed router prefixes in overrides.py and scenarios.py
  - [x] Fixed schema consistency across API endpoints
- [x] Update API route tests to use correct router prefixes
  - [x] Fixed integration tests in test_api_routes.py
  - [x] Fixed system tests in test_end_to_end_flows.py
- [ ] Set up automated test runs in CI/CD pipeline

## Documentation
- [x] Complete API documentation
- [x] Add developer setup guide
- [x] Document projection model and algorithms
- [x] Create user guide for scenario creation

## Phase 2 

- [x] Combined Player Details CSV Upload 
  - [x] Add enhanced player details
  - [x] Update existing Player model with additional fields
  - [x] Create new import service and API endpoint
  
- [x] Starter/Backup and Status Tags
  - [ ] Implement UI components for managing tags
  - [x] Add API endpoints for status and depth chart management
  - [x] Support batch updates for multiple players
  
- [x] Rookie Projections Based on Draft Position
  - [x] Create RookieProjectionTemplate table
  - [x] Enhance RookieProjectionService to use draft position templates
  - [x] Add API endpoint for draft-based rookie projections
  
- [x] Simple Draft Day Tool
  - [x] Add draft status fields to Player model
  - [x] Create frontend component for draft day operations
  - [x] Implement API endpoints for the draft tool
  - [x] Add batch operations for rookie updates
  - [x] Support automatic projection creation after draft

## Phase 3 

### NFL Data Integration Testing
- [x] Test integration with NFL data sources (nfl-data-py and NFL API)
- [x] Test NFLDataImportService with mocked adapters
- [x] Test WebDataAdapter for handling HTML, JSON, and CSV responses
- [x] Test rate limiting and circuit breaker pattern implementation
- [x] Create comprehensive mock data for testing without external dependencies

### Position-Specific Import Accuracy
- [x] Test QB stats import accuracy (passing metrics, fantasy points)
- [x] Test RB stats import accuracy (rushing, receiving, fantasy points)
- [x] Test WR/TE stats import accuracy (receiving metrics, fantasy points)
- [x] Test fantasy point calculation for half-PPR scoring

### Import-to-Projection Pipeline
- [x] Test the complete flow from NFL data import to projections
- [x] Test weekly stats aggregation to season totals
- [x] Test generation of future season projections
- [x] Test application of position-specific adjustments
- [x] Test application of team-level adjustments

### Core Service Testing
- [x] Test ProjectionService adjustment factors and projection creation
- [x] Test OverrideService manual overrides and dependent stat recalculation
- [x] Test TeamStatService team-level adjustments
- [x] Test ScenarioService scenario creation and application
- [x] Test RookieProjectionService template application

### Data Validation and Error Handling
- [x] Test data validation during import process
- [x] Test data consistency checks with validation service
- [x] Test handling of various response formats
- [x] Test error handling for network issues and malformed data
- [x] Test automatic correction of inconsistent data


## Phase 4: Enhanced Player Data Management 

### Database Seeding and Player Import Improvements
- [x] Create seed_database.py script to populate the database from active_players.csv
- [x] Enhance convert_rookies.py to handle additional player attributes
  - [x] Support for height, weight, and date of birth
  - [x] Add player physical measurements processing
  - [x] Support multiple input formats (CSV and Excel)
- [x] Add unit tests for the new seeding functionality

### Support for Enhanced Player Attributes
- [x] Update Player model and services to use the extended player data
- [x] Create API endpoints for accessing enhanced player attributes
- [x] Improve rookie import to properly handle player measurements
- [x] Add depth chart data integration with player details

### Player Import Format Flexibility
- [x] Refactor rookie import to accept both CSV and Excel formats
- [x] Implement common processing path after loading either format
- [x] Add validation for the enhanced player attributes
- [x] Create comprehensive test coverage for the player import functionality

## Phase 5: NFL Data Integration

### NFL Data Import System
- [x] Implement adapters for multiple NFL data sources
  - [x] Create NFLDataPyAdapter for nfl-data-py package integration
  - [x] Create NFLApiAdapter for direct NFL API access
  - [x] Create WebDataAdapter for testing and fallback options
- [x] Build a robust NFLDataImportService
  - [x] Support player data import from NFL sources
  - [x] Support weekly stats import and aggregation
  - [x] Support team stats import and processing
  - [x] Implement validation and data consistency checks
- [x] Create comprehensive test suite for NFL data integration

### Testing Infrastructure
- [x] Refactor tests to work with new NFL data import system
  - [x] Update unit tests for data transformations and validations
  - [x] Update integration tests for NFL data pipeline
  - [x] Update system tests for end-to-end flows
- [x] Implement mock framework for NFL data sources
  - [x] Support HTML, JSON, and CSV response mocking
  - [x] Create realistic test data fixtures
  - [x] Support rate limiting and error simulation
- [x] Create test utilities for common testing patterns
  - [x] Create AsyncMock utilities for testing async code
  - [x] Implement database fixtures for testing
  - [x] Support test isolation and cleanup

## Phase 6: Complete Testing and Validation

### Fix Remaining Tests
- [x] Fix test_complete_season_pipeline.py to fully integrate with NFLDataImportService
  - [x] Fixed NoneType errors in team_stat_service.py
  - [x] Added proper targets/pass_attempts ratio handling
- [x] Fix API test failures after router prefix changes
  - [x] Updated test URLs to match the new router prefixes
  - [x] Fixed all test_end_to_end_flows.py HTTP client tests to pass
- [x] Fix database model field inconsistencies in test fixtures
  - [x] Standardized all fixtures to use rush_attempts instead of carries
  - [x] Fixed test fixtures in all integration and system tests
- [ ] Implement/fix export process tests
- [ ] Complete draft day tool tests
- [ ] Add performance testing for large datasets

### Code Quality Improvements
- [ ] Update deprecated code patterns:
  - [ ] Replace FastAPI on_event with lifespan event handlers
  - [ ] Update Query parameters to use pattern instead of regex
  - [ ] Fix SQLAlchemy legacy warnings (Query.get method)

### Data Validation
- [ ] Add comprehensive validation for NFL data imports
- [ ] Implement consistency checks between stats and projections
- [ ] Create robust error handling for all data sources

## Future Phase: Production Deployment
*Note: These items are deprioritized until we have a complete model and all tests passing*

### Containerization
- [ ] Create Docker configuration for the backend
- [ ] Configure Docker Compose for local development
- [ ] Set up multi-stage build process for frontend

### Database Migration
- [ ] Create Alembic migration scripts
- [ ] Set up automated database migration process
- [ ] Implement backup and restore procedures

### Monitoring and Logging
- [ ] Set up structured logging
- [ ] Implement health check endpoints
- [ ] Configure monitoring dashboards
- [ ] Add performance tracking metrics

### Deprioritized CI/CD Pipeline Tasks
*Note: These items are deprioritized until we have a complete model and all tests passing*

- [ ] Set up automated testing workflow
- [ ] Implement build and deployment pipeline
- [ ] Configure environment-specific configurations
- [ ] Add automated documentation generation

## Updates for NFL Data Integration and Testing

### Recent Completions
- [x] Fixed router prefixes in API routes:
  - [x] Added prefix to overrides.py: `/overrides` 
  - [x] Added prefix to scenarios.py: `/scenarios`
- [x] Updated system tests:
  - [x] Enhanced test_complete_season_pipeline.py to verify NFL data import
  - [x] Fixed test_import_projection_flow.py with proper completion
- [x] Completed API route tests with schema validation fixes

### Remaining Testing Tasks
- [x] Fix test_complete_season_pipeline.py for the full pipeline test
  - [x] Fixed NoneType errors in team_stat_service.py
  - [x] Fixed targets/pass_attempts ratio issue
- [x] Fix API route tests to use correct router prefixes
  - [x] Fixed integration tests in test_api_routes.py (all 11 tests pass)
  - [x] Fixed all HTTP client tests in test_end_to_end_flows.py (5/5 tests pass)
  - [x] Fixed complete system test workflow with scenario-related tests
- [x] Fix test database configuration for system tests
  - [x] Fixed database-related issues in test_end_to_end_flows.py with comprehensive solution
  - [x] Implemented properly separated test database sessions with file-based SQLite
  - [x] Added consistent approach to fixture isolation with proper cleanup
  - [x] Enhanced test resilience with API fallback mechanisms
- [x] Fix database model field inconsistencies in test fixtures
  - [x] Updated "carries" to "rush_attempts" in all Projection model instances
  - [x] Updated all TeamStat fixtures to properly standardize on rush_attempts 
  - [x] Fixed all test fixtures to use rush_attempts consistently
- [ ] Update deprecated code patterns in tests:
  - [ ] Replace `regex` with `pattern` in FastAPI Query parameters
  - [ ] Replace `on_event` with lifespan event handlers
  - [ ] Replace SQLAlchemy's Query.get() with Session.get()
- [ ] Fix database isolation issues between tests:
  - [ ] Create more focused test fixtures
  - [ ] Implement proper transaction rollback
  - [ ] Add strict cleanup procedures for test data
- [ ] Add performance testing for large datasets

### Deprioritized Tasks (Until Core Tests Pass)
- [ ] Set up automated test runs in CI/CD pipeline
- [ ] Implement Docker containerization