# NFL Data Import Guide

This document provides instructions for using the new NFL data import functionality, which replaces the previous Pro Football Reference (PFR) scraper with more reliable NFL data sources.

## Overview

The new NFL data import system uses two primary data sources:

1. **nfl-data-py Python Package** - Provides comprehensive NFL statistics with a simple, well-maintained API
2. **NFL API** - Official NFL data with detailed player and game information

These sources provide more reliable, comprehensive data and are less prone to rate limiting or availability issues than web scraping.

## Installation

To use the NFL data import functionality, you need to install the required dependencies:

```bash
# Within your conda environment
conda env update -f backend/environment.yml
```

This will install the `nfl-data-py` package and other dependencies required by the import system.

## Importing Data via API

The system provides several API endpoints for importing data:

### Full Season Import

```
POST /batch/import/nfl-data/{season}
```

This endpoint imports all data for a specific season, including players, weekly stats, team stats, and calculates season totals.

**Example Request:**
```http
POST /batch/import/nfl-data/2023
```

For longer imports, use the background task option by setting the query parameter `background=true`.

### Specific Data Imports

The system also provides endpoints for importing specific data types:

- **Player Import**: `POST /batch/import/nfl-data/players/{season}`
- **Weekly Stats**: `POST /batch/import/nfl-data/weekly/{season}`
- **Team Stats**: `POST /batch/import/nfl-data/team/{season}`
- **Season Totals Calculation**: `POST /batch/import/nfl-data/totals/{season}`
- **Data Validation**: `POST /batch/import/nfl-data/validate/{season}`

## Command Line Import

### Full Import (All Data at Once)

For bulk operations or initial data loading, use the main import script:

```bash
# Import full data for the 2023 season
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

### Position-by-Position Import (Recommended for Resource Management)

For better resource management, especially with large datasets, use the position-based import script:

```bash
# Import team data first
python backend/scripts/import_by_position.py --season 2024 --position team

# Import QB data
python backend/scripts/import_by_position.py --season 2024 --position QB

# Import RB data
python backend/scripts/import_by_position.py --season 2024 --position RB

# Import WR data
python backend/scripts/import_by_position.py --season 2024 --position WR

# Import TE data
python backend/scripts/import_by_position.py --season 2024 --position TE

# Alternative: Import all positions with one command (still done sequentially)
python backend/scripts/import_by_position.py --season 2024 --position all
```

The position-by-position approach offers several advantages:
- Lower memory usage since it processes one position at a time
- Better visibility into progress by position
- Ability to prioritize specific positions
- Easier recovery if an import fails (just restart that position)

## Data Processing Pipeline

The NFL data import process follows these steps:

1. **Player Import**: Import player information including name, team, position, height, weight, etc.
2. **Weekly Stats Import**: Import game-by-game statistics for all players
3. **Team Stats Import**: Import team-level offensive statistics
4. **Season Totals Calculation**: Calculate season totals from weekly game data
5. **Data Validation**: Validate data consistency and fix any issues

## Logging and Monitoring

The system logs all import operations to both the console and log files:

- **Console output**: Provides real-time feedback during import operations
- **Log files**: Detailed logs are saved to the `backend/logs` directory:
  - `nfl_data_import.log`: For the main import script
  - `position_import.log`: For position-based imports
- **Database logging**: Import operations are also logged to the `import_logs` table in the database

You can check database contents after import using the check_import.py tool:

```bash
# Basic check
python backend/scripts/check_import.py

# Filter by position
python backend/scripts/check_import.py --position QB --season 2024

# Check specific player
python backend/scripts/check_import.py --player "Patrick Mahomes"

# Show import logs
python backend/scripts/check_import.py --logs
```

## Troubleshooting

Common issues and solutions:

1. **Rate limiting**: If you encounter rate limiting from the NFL API, the system will automatically retry with backoff. For large imports, consider using the background task option.

2. **Data inconsistencies**: If you notice inconsistencies in the data, run the validation endpoint to identify and fix issues:
   ```
   POST /batch/import/nfl-data/validate/{season}
   ```

3. **Missing data**: If certain players or statistics are missing, you may need to import data for previous seasons to establish player history.

## Differences from PFR Scraper

The new NFL data import system differs from the previous PFR scraper in several ways:

1. **More comprehensive data**: Includes additional statistics not available in PFR
2. **More reliable**: Less prone to rate limiting or scraper failures
3. **Better performance**: Faster import times, especially for large datasets
4. **More granular control**: Import specific data types as needed
5. **Background processing**: Support for long-running imports in the background