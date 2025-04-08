# Fantasy Football Projections Scripts

This directory contains utility scripts for data import, validation, and maintenance of the Fantasy Football Projections system.

## Data Import Scripts

### import_nfl_data.py
Imports all player statistics from official NFL data sources using the NFL API and nfl_data_py package.

```bash
# Import complete data for 2023 season
python backend/scripts/import_nfl_data.py --seasons 2023 --type full

# Import only player data for multiple seasons
python backend/scripts/import_nfl_data.py --seasons 2021 2022 2023 --type players

# Import weekly stats for a specific season
python backend/scripts/import_nfl_data.py --seasons 2023 --type weekly

# Import team stats for multiple seasons
python backend/scripts/import_nfl_data.py --seasons 2021 2022 2023 --type team

# Calculate season totals from weekly data
python backend/scripts/import_nfl_data.py --seasons 2023 --type totals

# Validate imported data
python backend/scripts/import_nfl_data.py --seasons 2023 --type validate
```

### import_by_position.py
Imports NFL player statistics position-by-position to optimize memory usage and performance.

```bash
# Import team data only
python backend/scripts/import_by_position.py --season 2023 --position team

# Import QB data
python backend/scripts/import_by_position.py --season 2023 --position QB

# Import RB data
python backend/scripts/import_by_position.py --season 2023 --position RB

# Import WR data
python backend/scripts/import_by_position.py --season 2023 --position WR

# Import TE data
python backend/scripts/import_by_position.py --season 2023 --position TE

# Import all positions sequentially
python backend/scripts/import_by_position.py --season 2023 --position all
```

### check_import.py
Verifies database contents after import operations for validation and monitoring.

```bash
# Basic check
python backend/scripts/check_import.py

# Check with position filter
python backend/scripts/check_import.py --position QB --season 2023

# Check specific player
python backend/scripts/check_import.py --player "Patrick Mahomes"

# Show import logs
python backend/scripts/check_import.py --logs
```

### setup_nfl_data.py
Verifies and installs the required dependencies for the NFL data import system.

```bash
# Check and install required packages
python backend/scripts/setup_nfl_data.py
```

### convert_rookies.py
Converts rookie player data from CSV format to the internal database format.

```bash
# Import rookie data from default CSV file
python backend/scripts/convert_rookies.py

# Import from a specific file with verification
python backend/scripts/convert_rookies.py --file "data/Rookie '25 Projections.csv" --verify
```

### initialize_rookie_templates.py
Creates rookie projection templates based on draft position and historical performance.

```bash
# Initialize templates for all positions
python backend/scripts/initialize_rookie_templates.py

# Initialize templates for a specific position
python backend/scripts/initialize_rookie_templates.py --position WR
```

## Usage Notes

- Data import scripts include comprehensive error handling and validation
- NFL data imports use exponential backoff and caching to respect API rate limits
- All scripts support the `--dry-run` flag to preview operations without modifying the database
- Verification mode validates statistical totals against game-by-game data
- Import operations are logged to both the console and the `import_logs` table in the database

## Current Progress

The following features have been implemented:
- ✅ NFL data import from official NFL API and nfl_data_py
- ✅ Weekly and season-level data processing
- ✅ Team-level statistics import
- ✅ Rookie data import and conversion
- ✅ Draft position-based rookie projection templates
- ✅ Data verification and validation
- ✅ Comprehensive error handling and reporting

## Current Status

The scripts have been updated to implement a comprehensive NFL data integration system:

- **Data Source Integration**:
  - ✅ Complete integration with nfl-data-py package
  - ✅ Integration with NFL API for additional data
  - ✅ Adapter-based architecture for multiple data sources
  - ✅ Comprehensive test coverage for data imports

- **Import Process Improvements**:
  - ✅ Rate limiting and backoff strategies
  - ✅ Robust error handling and retry mechanisms
  - ✅ Support for background processing of long-running imports
  - ✅ Position-by-position imports for resource optimization
  - ✅ Memory-efficient processing with batch commits
  - ✅ Detailed metrics tracking and logging
  - ✅ Centralized log file management in backend/logs

- **Data Transformation**:
  - ✅ Advanced data transformation and mapping
  - ✅ Fantasy point calculation
  - ✅ Derived statistics calculation
  - ✅ Data validation and consistency checks
  - ✅ Baseline scenario generation for projections

## Future Enhancements

Planned script improvements:
- [ ] Automated weekly in-season player statistic updates
- [ ] Injury status tracking and updates
- [ ] Strength of schedule data import
- [ ] Weather data integration for game forecasting
- [ ] Advanced batch processing for efficiency
- [ ] More detailed player performance metrics
- [ ] Advanced statistical analysis tools