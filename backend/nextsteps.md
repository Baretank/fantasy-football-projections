# Next Steps for Fantasy Football Projections App

## April 2025 Status Update
- 409/410 tests passing
- Export functionality: 4/4 tests passing
- One failing test: test_season_upload.py::TestDataImport::test_full_import_pipeline

## Completed Items

### Core Functionality (Completed ✓)
- ✓ Data import and verification implementation
- ✓ Projection engine with rookie projection and team adjustments
- ✓ API improvements with batch operations and export endpoints
- ✓ NFL data integration with adapters for multiple data sources

### Testing Improvements (Completed ✓)
- ✓ Export functionality tests (4/4 tests passing)
- ✓ Unit tests for all core services 
- ✓ Integration tests for NFL data import system (9/9 tests passing)
- ✓ System tests for end-to-end flows (5/5 tests passing)
- ✓ Field standardization across codebase (rush_attempts vs carries)

## Pending Tasks

### Bug Fixes
- [ ] Fix failing test in test_season_upload.py (missing 'services' fixture)

### Draft Day Tools
- [ ] Implement API endpoints for draft day operations
- [ ] Connect to test framework in test_draft_day_tools.py

### Performance Testing
- [ ] Implement performance testing endpoints
- [ ] Connect to test framework in test_performance.py

### Code Quality Improvements
- [ ] Update deprecated FastAPI patterns:
  - [ ] Replace on_event with lifespan event handlers (in main.py)
  - [ ] Update Query parameters to use pattern instead of regex (in multiple routes)
- [ ] Fix SQLAlchemy legacy warnings:
  - [ ] Replace Query.get() with Session.get() in projection_service.py
- [ ] Address Pydantic deprecation warnings:
  - [ ] Replace class-based config with ConfigDict
  - [ ] Use json_schema_extra instead of extra keyword arguments on Field

### Future Phase: Production Deployment
- [ ] Create Docker configuration for the backend
- [ ] Configure Docker Compose for local development
- [ ] Set up multi-stage build process for frontend
- [ ] Create database migration scripts
- [ ] Set up monitoring and logging
- [ ] Implement CI/CD pipeline

## Current Priority
1. Fix failing test in test_season_upload.py
2. Implement draft day tool API endpoints
3. Implement performance testing endpoints
4. Address technical debt and deprecation warnings (starting with most critical warnings)