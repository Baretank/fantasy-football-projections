# Fantasy Football Projections System Structure

## Directory Structure

```
fantasy-football-projections/
├── README.md
├── CLAUDE.md                # Guide for agentic coding assistants
├── .gitignore
├── package.json
├── tsconfig.json
│
├── backend/
│   ├── __init__.py
│   ├── main.py              # FastAPI entry point
│   ├── environment.yml      # Conda environment config
│   ├── newfeatures.md       # Feature additions document
│   ├── nextsteps.md         # Development roadmap
│   ├── database/
│   │   ├── __init__.py
│   │   ├── init_db.py       # Database initialization
│   │   ├── models.py        # SQLAlchemy models
│   │   └── database.py      # Database connection
│   ├── api/
│   │   ├── __init__.py
│   │   ├── schemas.py       # Pydantic schemas
│   │   ├── docs/
│   │   │   └── README.md    # API Documentation
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── players.py   # Player endpoints
│   │       ├── projections.py # Projection endpoints
│   │       ├── overrides.py # Manual override endpoints
│   │       ├── scenarios.py # Scenario management endpoints
│   │       └── batch.py     # Batch operations endpoints
│   ├── scripts/
│   │   ├── README.md
│   │   ├── upload_season.py # Import seasonal data
│   │   ├── convert_rookies.py # Import rookie data
│   │   └── initialize_rookie_templates.py # Create rookie projection templates
│   ├── services/
│   │   ├── __init__.py
│   │   ├── projection_service.py     # Projection calculations
│   │   ├── nfl_data_import_service.py # NFL data import handling
│   │   ├── data_service.py           # Data retrieval
│   │   ├── data_validation.py        # Data validation
│   │   ├── team_stat_service.py      # Team statistics
│   │   ├── override_service.py       # Manual overrides
│   │   ├── scenario_service.py       # Scenario management
│   │   ├── cache_service.py          # Caching service
│   │   ├── batch_service.py          # Batch operations
│   │   ├── query_service.py          # Optimized database queries
│   │   ├── player_import_service.py  # Player import functionality
│   │   ├── rookie_import_service.py  # Rookie import functionality
│   │   ├── rookie_projection_service.py # Rookie projections
│   │   ├── projection_variance_service.py # Projection uncertainty
│   │   └── adapters/                  # Data source adapters
│   │       ├── nfl_data_py_adapter.py # Adapter for nfl_data_py library
│   │       └── nfl_api_adapter.py     # Adapter for NFL API
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py            # Test fixtures
│       ├── unit/                  # Unit tests
│       │   ├── __init__.py
│       │   ├── test_projection_service.py
│       │   ├── test_data_service.py
│       │   ├── test_team_stat_service.py
│       │   ├── test_data_validation.py
│       │   ├── test_nfl_data_import_service.py
│       │   ├── test_data_import_transformations.py
│       │   ├── test_external_response_handling.py
│       │   ├── test_override_service.py
│       │   ├── test_position_import_accuracy.py
│       │   ├── test_rate_limiting.py
│       │   ├── test_scenario_service.py
│       │   └── test_batch_import_functionality.py
│       ├── integration/           # Integration tests
│       │   ├── __init__.py
│       │   ├── test_projection_pipeline.py
│       │   └── test_nfl_data_integration.py
│       └── system/                # System tests
│           ├── __init__.py
│           ├── test_end_to_end_flows.py
│           ├── test_import_projection_flow.py
│           └── test_season_upload.py
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── playerselect.tsx       # Player selection
│   │   │   ├── counter.ts
│   │   │   ├── dashboard.tsx          # Dashboard component
│   │   │   ├── projectionadjuster.tsx # Adjusting projections
│   │   │   ├── statsdisplay.tsx       # Displaying stats
│   │   │   ├── ui/                    # UI components
│   │   │   │   ├── button.tsx
│   │   │   │   ├── card.tsx
│   │   │   │   ├── dialog.tsx
│   │   │   │   ├── input.tsx
│   │   │   │   ├── label.tsx
│   │   │   │   ├── separator.tsx
│   │   │   │   ├── slider.tsx
│   │   │   │   ├── table.tsx
│   │   │   │   ├── tabs.tsx
│   │   │   │   └── badge.tsx
│   │   │   ├── layout/               # Layout components
│   │   │   │   └── AppLayout.tsx
│   │   │   ├── navigation/           # Navigation components
│   │   │   │   └── MainNav.tsx
│   │   │   └── visualization/        # Visualization components
│   │   │       └── ProjectionRangeChart.tsx
│   │   ├── pages/                    # Page components
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── ComparePage.tsx
│   │   │   └── NotFoundPage.tsx  
│   │   ├── services/
│   │   │   └── api.ts                # API client
│   │   ├── types/
│   │   │   └── index.ts              # TypeScript types
│   │   ├── utils/
│   │   │   └── calculatioms.ts       # Utility functions
│   │   ├── lib/
│   │   │   └── utils.ts              # Helper functions
│   │   ├── routes.tsx                # Application routes
│   │   ├── ProjectionApp.tsx         # Main app component
│   │   ├── main.tsx                  # Entry point
│   │   └── style.css                 # Global styles
│   ├── public/
│   │   └── vite.svg
│   ├── index.html
│   ├── tsconfig.node.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── package.json
│
├── docs/
│   ├── Structure.md          # This document
│   ├── Model.md              # Projection model docs
│   ├── nfl_data_integration.md # NFL data integration technical details
│   ├── nfl_data_import.md     # NFL data import user guide
│   ├── api_docs.md           # Comprehensive API documentation
│   ├── developer_setup.md    # Developer environment setup guide
│   └── user_guide.md         # User manual for the application
│
└── data/
    ├── rookies.json          # Rookie player data
    └── NFL 2025 Projections.xlsx  # Excel projection model
```

## Core Components

### Database Models (`/backend/database/models.py`)

- **Player**: Player information and metadata
- **BaseStat**: Historical and baseline statistics
- **GameStats**: Game-by-game player statistics
- **TeamStat**: Team-level offensive statistics and metrics
- **Projection**: Individual player projections with statistical modeling
- **ProjectionVariance**: Statistical variance and confidence intervals
- **Scenario**: Projection scenarios for what-if analysis
- **StatOverride**: Manual overrides to projection values
- **RookieProjectionTemplate**: Templates for rookie projections based on draft position

### Services (`/backend/services/`)

- **DataService**: Player and statistical data retrieval
- **NFLDataImportService**: NFL data import from multiple sources with adapters
- **DataValidationService**: Data validation and verification
- **ProjectionService**: Core projection calculations
- **TeamStatService**: Team-level statistics management
- **RookieProjectionService**: Specialized rookie projections
- **ProjectionVarianceService**: Uncertainty and confidence intervals
- **OverrideService**: Manual overrides handling
- **ScenarioService**: Scenario creation and comparison
- **BatchService**: Batch operations for multiple entities
- **CacheService**: Caching for performance optimization
- **QueryService**: Optimized database queries
- **PlayerImportService**: Import functionality for existing players
- **RookieImportService**: Import functionality specific to rookies

### API Endpoints (`/backend/api/routes/`)

- **players.py**: Player information endpoints
- **projections.py**: Projection creation and retrieval
- **overrides.py**: Manual override management
- **scenarios.py**: Scenario planning and comparison
- **batch.py**: Batch operations and data export

### Scripts (`/backend/scripts/`)

- **upload_season.py**: Import historical player statistics from external sources
- **convert_rookies.py**: Process rookie data from CSV files
- **initialize_rookie_templates.py**: Create templates for rookie projections

### Frontend Pages and Views (`/frontend/src/pages/`)

- **DashboardPage.tsx**: Main dashboard with analytics overview
- **ComparePage.tsx**: Side-by-side player comparison tool
- **NotFoundPage.tsx**: 404 error handling

### Frontend Components (`/frontend/src/components/`)

- **layout/AppLayout.tsx**: Main application layout with navigation
- **navigation/MainNav.tsx**: Primary navigation component
- **playerselect.tsx**: Player selection component
- **projectionadjuster.tsx**: Adjusting projection values
- **statsdisplay.tsx**: Statistical data visualization
- **dashboard.tsx**: Dashboard component with analytics
- **visualization/ProjectionRangeChart.tsx**: Confidence interval charts

## Key Features

### Enhanced Statistical Model

- Advanced metrics including net yards, efficiency rates, etc.
- Position-specific modeling (QB, RB, WR, TE)
- Team context integration
- Statistical variance and confidence intervals

### Manual Override System

- Override tracking for individual statistics
- Automatic recalculation of dependent stats
- Batch override capabilities
- Contextual adjustments (injuries, coaching changes, etc.)

### Scenario Planning

- Alternative projection scenarios
- Scenario comparison functionality
- Baseline scenario establishment
- Scenario cloning

### Data Consistency Mechanisms

- Fill player generation for complete team projections
- Team-level validation
- Mathematical consistency checks

### Rookie Projection System

- Draft position-based projection templates
- Three-tiered projection approach (low, medium, high outcomes)
- College production integration
- Historical comparison modeling

### Import and Validation

- NFL data integration with official APIs
- Data validation and verification
- Exponential backoff for external APIs
- Batch processing with configurable settings

### Performance Optimization

- Response caching
- Optimized database queries
- Batch operations for multiple entities
- Efficient data transformation

## Implementation Status

### Completed Features
- ✅ Core projection engine
- ✅ Manual override system
- ✅ Scenario planning
- ✅ Team statistics management
- ✅ Rookie projection system
- ✅ Projection variance and confidence intervals
- ✅ Rate-limited data import
- ✅ Comprehensive test suite

### In Progress
- 🔄 Enhanced UI components for status and depth chart management
- 🔄 Authentication and authorization
- 🔄 Automated CI/CD pipeline

### Future Enhancements
- ⏳ Machine learning integration
- ⏳ Strength of schedule adjustments
- ⏳ Game script dependency modeling
- ⏳ Injury impact modeling
- ⏳ Additional scoring format support
- ⏳ Time-series based uncertainty analysis