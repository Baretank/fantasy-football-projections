# Fantasy Football Projections v0.3.0 Implementation Plan

- See v0.2.0 snapshot [0.2.0 Snapshot](docs/versions/0.2.0/020_snapshot.md)

## 1. Database Redesign

### 1.1 Schema Redesign
- Create new table structure with season as a core organizing principle
- Implement proper relationships between players, teams, games, and seasons
- Add tables for aggregated season-level statistics
- Design enhanced projection and scenario tables

### 1.2 New Core Tables
- `Seasons`: Season metadata and configuration
- `TeamSeasons`: Team statistics aggregated at season level
- `PlayerSeasons`: Player statistics aggregated at season level
- `Games`: Game-level data with proper season relationship
- `GameStats`: Enhanced game statistics with optimized queries
- `Projections`: Revised projection model with accurate calculations
- `Scenarios`: Enhanced scenario management system

### 1.3 Statistical Model Improvements
- Implement proper team and player statistical relationships
- Add usage metrics (target share, rush share, etc.) to replace player status system
- Create "fill player" mechanism to maintain team statistical consistency
- Add proper indexing for performance optimization

## 2. Statistical Projection Engine

### 2.1 Core Projection Engine
- Redesign baseline projection calculation from historical data
- Implement proper usage share calculations (target share, pass attempt share, rush share)
- Create statistical regression algorithm for projection smoothing
- Ensure mathematical consistency between projections and team totals

### 2.2 Player Efficiency Metrics
- Calculate and store position-specific efficiency metrics
- Implement historical trend analysis for players
- Create comparison system between historical and projected efficiency
- Fix target share and usage calculations

### 2.3 Team Context Integration
- Ensure team-level constraints are properly applied to players
- Implement the "fill player" concept to maintain statistical consistency
- Add team offensive style metrics and adjustments
- Create validation system for team statistical totals

## 3. Data Import System

### 3.1 Data Source Integration
- Implement new season-based data import architecture
- Create position-by-position import system for resource optimization
- Add validation for imported data consistency
- Implement game and season-level data transformations

### 3.2 Historical Data Import
- Create import process for 2023 season data
- Implement import process for 2024 season data
- Add validation for historical data consistency
- Generate efficiency metrics from historical data

### 3.3 Projection Data Generation
- Create projection generation system from historical data
- Implement team-based statistical context for projections
- Add rookies and new players handling
- Create export functionality for current projections

## 4. API Enhancements

### 4.1 Core API Redesign
- Update API endpoints to support new database structure
- Implement season-based filtering across all endpoints
- Create efficient queries for aggregated season data
- Add consistent error handling for all new endpoints

### 4.2 New Endpoints
- `/seasons`: Endpoints for season management
- `/players/{player_id}/seasons/{season_id}`: Player season statistics
- `/teams/{team_id}/seasons/{season_id}`: Team season statistics
- `/projections/seasons/{season_id}`: Season-level projections

### 4.3 Enhanced Functionality
- Add bulk adjustment endpoints for efficient data updates
- Implement scenario comparison endpoints
- Create player comparison API
- Add export functionality for projections

## 5. Frontend Adaptations

### 5.1 Season Selection
- Add global season selector component
- Implement season context provider
- Update API client services to include season filtering
- Add season selection persistence (localStorage)

### 5.2 Dashboard Simplification
- Redesign dashboard to focus on player table display
- Add sortable columns for key statistics
- Implement position and team filtering
- Add basic search functionality

### 5.3 API Integration Updates
- Update all API service calls to work with new endpoints
- Add loading states for async operations
- Implement error handling for failed API calls
- Create data transformation utilities for frontend display

### 5.4 Component Updates
- Update projection adjuster to use new API endpoints
- Modify team adjuster for new team statistics model
- Update scenario manager to use enhanced scenario system
- Fix draft day tool to properly create 2025 projections

## 6. Scenarios System Completion

### 6.1 Core Scenarios Functionality
- Complete scenario creation and management backend
- Fix scenario cloning functionality
- Implement proper projection assignment to scenarios
- Add baseline scenario designation

### 6.2 Scenario Comparison
- Implement side-by-side scenario comparison
- Add statistical difference highlighting
- Create visualization for scenario comparison
- Implement batch copy operations between scenarios

### 6.3 Team-Level Scenario Adjustments
- Add team-level adjustment capability within scenarios
- Implement player usage distribution within team context
- Create validation for team-level statistical consistency
- Add batch update functionality for team adjustments

## 7. Testing Infrastructure

### 7.1 Backend Testing
- Create test fixtures for new database models
- Implement unit tests for core projection calculations
- Add integration tests for API endpoints
- Create validation tests for statistical consistency

### 7.2 Data Validation Tests
- Implement tests for data import accuracy
- Add validation for projection calculations
- Create consistency checks for team and player statistics
- Add efficiency metric calculation tests

### 7.3 Frontend Tests
- Update component tests for modified components
- Add tests for new season selection functionality
- Implement API service mocks for testing
- Create end-to-end tests for critical workflows

## 8. Documentation

### 8.1 Developer Documentation
- Document new database schema and relationships
- Create API endpoint documentation
- Add projection calculation methodology
- Document statistical models and algorithms

### 8.2 User Documentation
- Create user guide for new functionality
- Add tutorial for season selection
- Document scenarios usage and best practices
- Create examples for manual adjustments

# 9. Code Quality and Type Safety Enhancements

Based on the existing work outlined in PACKAGE_REFACTOR.md, the following improvements will be integrated throughout the v0.3.0 implementation:

## 9.1 Centralized Typing System

- Create `backend/services/typing.py` with comprehensive TypedDict definitions
- Implement safe utility functions for type operations:
  - `safe_float()`: Convert values to float with proper null/error handling
  - `safe_dict_get()`: Access dictionary values with default fallbacks
  - `safe_calculate()`: Perform calculations with built-in error prevention
- Add proper type annotations throughout all new and modified code
- Update interfaces to utilize proper Optional types for nullable fields

## 9.2 Data Safety Framework

- Implement TypedDataFrame wrapper for pandas operations:
  - Add safe accessor methods (get_float, get_int, get_str)
  - Implement series conversion utilities
  - Create defensive pandas operations
- Enhance all data import services with robust error handling
- Implement proper null safety with pd.isna() checks throughout
- Add input validation for all data processing functions
- Create comprehensive exception hierarchy for better error tracking

## 9.3 Error Handling Strategy

- Establish consistent error handling patterns across all modules
- Implement defensive programming for API responses
- Add proper null safety checks before property access
- Create robust error boundaries for frontend components
- Add safe fallbacks for all data rendering
- Implement comprehensive logging for error scenarios
- Add structured try/except blocks with specific exception types

## 9.4 Code Organization

- Standardize on absolute imports (`from backend.x import y`)
- Enhance all required `__init__.py` files for proper module resolution
- Fix module resolution issues for mypy type checking
- Remove unused imports (fix F401 violations)
- Fix whitespace and formatting issues
- Address bare except clauses with specific exception handling
- Implement proper function and class spacing

## 9.5 Code Quality Tooling

- Configure mypy for strict type checking
- Add linting configuration for consistent code style
- Implement pre-commit hooks for code quality checks
- Create CI checks for type safety and linting
- Add documentation generation from type annotations
- Establish guidelines for TypedDict usage
- Create code quality reporting system

## 9.6 Frontend Type Safety

- Implement proper TypeScript interfaces for all API responses
- Add defensive null checking in React components
- Create safe formatting utilities for numeric display
- Implement proper error handling for all API calls
- Add runtime type validation for critical data structures
- Use proper Optional types and null coalescing
- Add component prop validation throughout

## Implementation Approach

The type safety and code quality improvements will be integrated throughout the development process:

1. **Phase 1**: Establish centralized typing system and basic patterns
2. **Phase 2**: Integrate type safety into new database models and services
3. **Phase 3**: Implement frontend type safety for new and modified components
4. **Phase 4**: Add comprehensive testing for edge cases and error handling

## Implementation Timeline

### Phase 1: Foundation
- Database schema redesign
- Core database models implementation
- Initial data import system

### Phase 2: Core Functionality
- Projection engine implementation
- API endpoint updates
- Basic frontend adaptations

### Phase 3: Advanced Features
- Scenarios system completion
- Team-level adjustments
- Dashboard simplification

### Phase 4: Integration & Testing 
- Comprehensive testing
- Bug fixes and refinements
- Documentation
- Final validation and release

## Technical Considerations

### Performance Optimization
- Implement proper indexing for common queries
- Use batch operations for bulk updates
- Add caching for frequently accessed data
- Optimize statistical calculations

### Code Organization
- Maintain clear separation of concerns
- Use consistent naming conventions
- Implement proper error handling
- Add comprehensive logging

### Future Compatibility
- Design database schema to support future in-season updates
- Create flexible projection engine for future enhancements
- Implement extensible API design for additional features
- Plan for potential PostgreSQL migration