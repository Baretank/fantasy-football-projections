# Fantasy Football Projections Scripts

This directory contains utility scripts for data import, validation, and maintenance of the Fantasy Football Projections system.

## Data Import Scripts

### import_nfl_data.py
Imports player statistics from official NFL data sources using the NFL API and nfl_data_py package.

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
  - ✅ Detailed metrics tracking and logging

- **Data Transformation**:
  - ✅ Advanced data transformation and mapping
  - ✅ Fantasy point calculation
  - ✅ Derived statistics calculation
  - ✅ Data validation and consistency checks

## Future Enhancements

Planned script improvements:
- [ ] Automated weekly in-season player statistic updates
- [ ] Injury status tracking and updates
- [ ] Strength of schedule data import
- [ ] Weather data integration for game forecasting
- [ ] Advanced batch processing for efficiency
- [ ] More detailed player performance metrics
- [ ] Advanced statistical analysis tools