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
│   ├── database/
│   │   ├── __init__.py
│   │   ├── init_db.py       # Database initialization
│   │   ├── models.py        # SQLAlchemy models
│   │   └── database.py      # Database connection
│   ├── api/
│   │   ├── __init__.py
│   │   ├── schemas.py       # Pydantic schemas
│   │   ├── docs/
│   │   │   └── README.md
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── players.py   # Player endpoints
│   │       ├── projections.py # Projection endpoints
│   │       ├── overrides.py # Manual override endpoints
│   │       └── scenarios.py # Scenario management endpoints
│   ├── scripts/
│   │   ├── README.md
│   │   ├── upload_season.py # Import seasonal data
│   │   └── convert_rookies.py # Import rookie data
│   ├── services/
│   │   ├── __init__.py
│   │   ├── projection_service.py  # Projection calculations
│   │   ├── data_import_service.py # Data import handling
│   │   ├── data_service.py        # Data retrieval
│   │   ├── team_stat_service.py   # Team statistics
│   │   ├── override_service.py    # Manual overrides
│   │   └── scenario_service.py    # Scenario management
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py            # Test fixtures
│       ├── unit/                  # Unit tests
│       │   ├── __init__.py
│       │   ├── test_projection_service.py
│       │   ├── test_data_service.py
│       │   ├── test_team_stat_service.py
│       │   └── test_data_import_service.py
│       ├── integration/           # Integration tests
│       │   ├── __init__.py
│       │   └── test_projection_pipeline.py
│       └── system/                # System tests
│           ├── __init__.py
│           └── test_season_upload.py
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── playerselect.tsx     # Player selection
│   │   │   ├── counter.ts
│   │   │   ├── projectionadjuster.tsx # Adjusting projections
│   │   │   └── statsdisplay.tsx     # Displaying stats
│   │   ├── services/
│   │   │   └── api.ts              # API client
│   │   ├── types/
│   │   │   └── index.ts            # TypeScript types
│   │   ├── utils/
│   │   │   └── calculatioms.ts     # Utility functions
│   │   ├── main.ts
│   │   └── style.css
│   ├── public/
│   │   └── vite.svg
│   ├── index.html
│   ├── tsconfig.node.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── package.json
│
├── docs/
│   ├── structure.md          # This document
│   ├── model.md              # Projection model docs
│   ├── Data Import Plan.md   # Data import details
│   └── PFR Docs.md           # Pro Football Reference details
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
- **Scenario**: Projection scenarios for what-if analysis
- **StatOverride**: Manual overrides to projection values

### Services (`/backend/services/`)

- **DataService**: Player and statistical data retrieval
- **DataImportService**: Data import from external sources
- **ProjectionService**: Core projection calculations
- **TeamStatsService**: Team-level statistics management
- **OverrideService**: Manual overrides handling
- **ScenarioService**: Scenario creation and comparison

### API Endpoints (`/backend/api/routes/`)

- **players.py**: Player information endpoints
- **projections.py**: Projection creation and retrieval
- **overrides.py**: Manual override management
- **scenarios.py**: Scenario planning and comparison

### Frontend Components (`/frontend/src/components/`)

- **playerselect.tsx**: Player selection component
- **projectionadjuster.tsx**: Adjusting projection values
- **statsdisplay.tsx**: Statistical data visualization

## Key Features

### Enhanced Statistical Model

- Advanced metrics including net yards, efficiency rates, etc.
- Position-specific modeling (QB, RB, WR, TE)
- Team context integration

### Manual Override System

- Override tracking for individual statistics
- Automatic recalculation of dependent stats
- Batch override capabilities

### Scenario Planning

- Alternative projection scenarios
- Scenario comparison functionality
- Baseline scenario establishment
- Scenario cloning

### Data Consistency Mechanisms

- Fill player generation for complete team projections
- Team-level validation
- Mathematical consistency checks