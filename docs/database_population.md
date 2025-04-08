# Database Population Guidelines

This document provides guidance for populating the database with NFL player and team data.

## Data Sources

The system uses the following data sources:

1. **NFL Data Python API**: Used for basic player information, weekly statistics, schedules and team data
2. **Custom NFL API Adapter**: Used for supplementary player information 
3. **Manual rookie data**: Used for rookie projections

## Data Import Process

### 1. Import Team Data

Always import team data first to establish the foundation for player data:

```bash
python backend/scripts/import_by_position.py --season 2024 --position team
```

This creates team entries and baseline team stats that will be used for projections.

### 2. Import Players By Position

For efficient memory management, import players by position rather than all at once:

```bash
# Import one position at a time
python backend/scripts/import_by_position.py --season 2024 --position QB
python backend/scripts/import_by_position.py --season 2024 --position RB
python backend/scripts/import_by_position.py --season 2024 --position WR
python backend/scripts/import_by_position.py --season 2024 --position TE

# Or import all positions sequentially
python backend/scripts/import_by_position.py --season 2024 --position all
```

Importing by position ensures:
- Better memory management for large datasets
- More fine-grained control over which positions to update
- Simplified debugging when import errors occur

### 3. Create Baseline Scenarios

After importing players and stats, create baseline scenarios:

```bash
python backend/scripts/create_baseline_scenario.py --season 2024 --type all
```

This generates four baseline scenarios:
- Standard: Raw statistical projections
- Conservative: Lower-bound projections (~10% decrease)
- Optimistic: Upper-bound projections (~10% increase)
- Team-Based: Projections adjusted for team contexts

## Rookie Data Processing

### 1. Import Rookies

Import rookies from draft data:

```bash
python backend/scripts/convert_rookies.py --draft-year 2024
```

### 2. Initialize Rookie Templates

Set up templates for generating rookie projections:

```bash
python backend/scripts/initialize_rookie_templates.py
```

### 3. Create Rookie Projections

Generate projections for rookies based on templates:

```bash
# Via script
python backend/scripts/create_baseline_scenario.py --season 2024 --type rookie

# Or via API endpoint
curl -X POST "http://localhost:8000/api/projections/rookies/create?season=2024"
```

## Verification

After import, verify the data is correctly populated:

```bash
python backend/scripts/check_import.py
```

For specific checks:

```bash
# Check specific position
python backend/scripts/check_import.py --position QB --season 2024

# Check specific player
python backend/scripts/check_import.py --player "Patrick Mahomes"

# Show import logs
python backend/scripts/check_import.py --logs
```

## Standardization Guidelines

To maintain consistency across the codebase:

1. **Field Naming**:
   - Use `rush_attempts` instead of `carries` consistently
   - Use `half_ppr` for fantasy point calculations by default

2. **Player IDs**:
   - Maintain consistent player IDs across imports
   - Use the `gsis_id` from NFL data as the primary `player_id`

3. **Team Abbreviations**:
   - Use standardized team abbreviations (e.g., "KC", "SF", "LAR")
   - Always normalize team abbreviations during import

## Troubleshooting

Common issues during data import:

1. **Memory Issues**: 
   - Use position-by-position import
   - Enable batch commits through the `--batch-size` parameter

2. **Missing Player Data**:
   - Verify player exists in the NFL data source
   - Check for proper ID mapping between data sources

3. **Inconsistent Statistics**:
   - Verify weekly stats match the expected season totals
   - Use the validation tools to check for data anomalies