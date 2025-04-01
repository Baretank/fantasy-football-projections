# NFL Data Integration

This document provides a comprehensive guide to the NFL data integration implementation, which replaces the previous Pro Football Reference (PFR) web scraper with more reliable and robust NFL data sources.

## 1. Data Sources Overview

### nfl-data-py Python Package
- **Primary import functions**:
  - `import_seasonal_data()` - Season-level player statistics
  - `import_weekly_data()` - Week-by-week player statistics
  - `import_team_desc()` - Team descriptions and metadata
  - `import_team_stats()` - Team-level statistics
  - `import_players()` - Player profiles and information
  - `import_rosters()` - Team roster information
  - `import_schedules()` - NFL game schedules
  - `import_pbp_data()` - Play-by-play detailed data
- **Authentication**: None required
- **Install**: `pip install nfl-data-py`
- **Repository**: [https://pypi.org/project/nfl-data-py/](https://pypi.org/project/nfl-data-py/)

### NFL API Resources
- **Base endpoints**:
  - `https://api.nfl.com/v3/players` - Player information
  - `https://api.nfl.com/v3/players/stats` - Player statistics
  - `https://api.nfl.com/v3/teams` - Team information
  - `https://api.nfl.com/v3/games` - Game information
- **Authentication**: Basic headers
  ```python
  headers = {
      'User-Agent': 'Mozilla/5.0',
      'Accept': 'application/json'
  }
  ```
- **Resource documentation**: [NFL API Resources Gist](https://gist.github.com/nntrn/ee26cb2a0716de0947a0a4e9a157bc1c)
- **Rate limiting**: Implements backoff strategies and response caching to respect API limits
- **Error handling**: Checks for HTTP status codes and implements retry logic for failed requests

## 2. Data Field Mappings

### Player Model
| Source Field   | Application Field | Notes                      |
|----------------|-------------------|----------------------------|
| `player_id`    | `player_id`       |                            |
| `display_name` | `name`            |                            |
| `position`     | `position`        |                            |
| `team`         | `team`            |                            |
| `status`       | `status`          | "ACT"/"INA" flags          |
| `height`       | `height`          | Convert from "feet-inches" |
| `weight`       | `weight`          |                            |

### BaseStat Model (Weekly/Season Stats)
| Source Field       | Application Field | Notes |
|-------------------|-------------------|-------|
| `pass_attempts`   | `pass_attempts`   |       |
| `completions`     | `completions`     |       |
| `passing_yards`   | `pass_yards`      |       |
| `passing_tds`     | `pass_td`         |       |
| `interceptions`   | `interceptions`   |       |
| `rushing_attempts`| `rush_attempts`   |       |
| `rushing_yards`   | `rush_yards`      |       |
| `rushing_tds`     | `rush_td`         |       |
| `targets`         | `targets`         |       |
| `receptions`      | `receptions`      |       |
| `receiving_yards` | `rec_yards`       |       |
| `receiving_tds`   | `rec_td`          |       |

### TeamStat Model
| Source Field        | Application Field | Notes |
|--------------------|-------------------|-------|
| `team_abbr`        | `team`            |       |
| `season`           | `season`          |       |
| `plays_offense`    | `plays`           |       |
| `attempts_offense` | `pass_attempts`   |       |
| `completions_offense` | `completions`  |       |
| `pass_yards_offense` | `pass_yards`    |       |
| `pass_tds_offense` | `pass_td`         |       |
| `rushes_offense`   | `rush_attempts`   |       |
| `rush_yards_offense` | `rush_yards`    |       |
| `rush_tds_offense` | `rush_td`         |       |

## 3. Implementation Details

### 3.1 Data Transformation Requirements

#### Height Conversion
Convert from "feet-inches" format to total inches:
```python
if height_str and '-' in height_str:
    feet, inches = height_str.split('-')
    height_inches = int(feet) * 12 + int(inches)
```

#### Derived Statistics Calculation
| Derived Stat         | Formula                        |
|----------------------|--------------------------------|
| Passing TD Rate      | `pass_td / pass_attempts`      |
| Completion Percentage| `completions / pass_attempts`  |
| Yards per Attempt    | `pass_yards / pass_attempts`   |
| Rush Yards per Attempt| `rush_yards / rush_attempts`  |
| Catch Rate           | `receptions / targets`         |
| Yards per Target     | `rec_yards / targets`          |
| Yards per Reception  | `rec_yards / receptions`       |

#### Season Totals Aggregation
- Aggregate weekly statistics into season totals
- Count distinct weeks to calculate games played

#### Fantasy Scoring Calculation
- **Half-PPR Scoring System** (Default):
  - 0.04 points per passing yard (1 point per 25 yards)
  - 4 points per passing touchdown
  - -1 point per interception
  - 0.1 points per rushing/receiving yard (1 point per 10 yards)
  - 6 points per rushing/receiving touchdown
  - 0.5 points per reception

### 3.2 Architecture

The implementation follows a modular, adapter-based architecture:

#### Core Components
1. **Data Source Adapters**:
   - `NFLDataPyAdapter`: Interface to the nfl-data-py Python package
   - `NFLApiAdapter`: Interface to the official NFL API with rate limiting and error handling

2. **Core Import Service**:
   - `NFLDataImportService`: Main service that coordinates data import and processing

3. **API Layer**:
   - Endpoints for importing full seasons or specific data types
   - Support for background processing of long-running imports

4. **Command Line Interface**:
   - Script for importing data from the command line
   - Support for batch importing multiple seasons

### 3.3 Implementation Flow

The complete data import process follows these steps:

1. **Player Import**: Import player information including name, team, position, height, weight, etc.
2. **Weekly Stats Import**: Import game-by-game statistics for all players
3. **Team Stats Import**: Import team-level offensive statistics
4. **Season Totals Calculation**: Calculate season totals from weekly game data
5. **Data Validation**: Validate data consistency and fix any issues

## 4. Usage Guide

### 4.1 Installation

To use the NFL data import functionality, install the required dependencies:

```bash
# Within your conda environment
conda env update -f backend/environment.yml
```

This will install the `nfl-data-py` package and other dependencies required by the import system.

### 4.2 API Usage

The system provides several API endpoints for importing data:

#### Full Season Import

```
POST /batch/import/nfl-data/{season}
```

This endpoint imports all data for a specific season, including players, weekly stats, team stats, and calculates season totals.

**Example Request:**
```http
POST /batch/import/nfl-data/2023
```

For longer imports, use the background task option by setting the query parameter `background=true`.

#### Specific Data Imports

The system also provides endpoints for importing specific data types:

- **Player Import**: `POST /batch/import/nfl-data/players/{season}`
- **Weekly Stats**: `POST /batch/import/nfl-data/weekly/{season}`
- **Team Stats**: `POST /batch/import/nfl-data/team/{season}`
- **Season Totals Calculation**: `POST /batch/import/nfl-data/totals/{season}`
- **Data Validation**: `POST /batch/import/nfl-data/validate/{season}`

### 4.3 Command Line Usage

For bulk operations or initial data loading, use the command-line import script:

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

## 5. Special Considerations and Edge Cases

### 5.1 Player ID Mapping

For consistent player identification across data sources, the system implements a player ID mapping mechanism:

- Maps external player IDs to internal system IDs
- Handles changes in player IDs between seasons or data sources
- Creates consistent tracking for players across the system

### 5.2 Traded Players

For players who change teams mid-season, the system provides special handling:

- Tracks historical stats with previous teams
- Updates current team references
- Preserves complete season statistics across teams

### 5.3 Rookie Handling

For rookies who lack historical NFL data:

- Imports draft position, college stats, and other rookie-specific data
- Integrates with the rookie projection templates system
- Handles rookies with limited or no NFL game history

## 6. Monitoring and Logging

The system includes comprehensive monitoring and logging:

- **Console output**: Provides real-time feedback during import operations
- **Log file**: More detailed logs are saved to `nfl_data_import.log`
- **Database logging**: Import operations are also logged to the `import_logs` table
- **Metrics tracking**: Tracks request counts, errors, and processing times

## 7. Files and Components

### 7.1 New Files

- `/backend/services/adapters/nfl_data_py_adapter.py`
- `/backend/services/adapters/nfl_api_adapter.py`
- `/backend/services/nfl_data_import_service.py`
- `/backend/scripts/import_nfl_data.py`
- `/backend/tests/unit/test_nfl_data_import_service.py`
- `/backend/tests/integration/test_nfl_data_integration.py`

### 7.2 Modified Files

- `/backend/api/routes/batch.py` - Added NFL data import endpoints
- `/backend/environment.yml` - Added nfl-data-py and aiohttp dependencies

## 8. Troubleshooting

Common issues and solutions:

1. **Rate limiting**: If you encounter rate limiting from the NFL API, the system will automatically retry with backoff. For large imports, consider using the background task option.

2. **Data inconsistencies**: If you notice inconsistencies in the data, run the validation endpoint to identify and fix issues:
   ```
   POST /batch/import/nfl-data/validate/{season}
   ```

3. **Missing data**: If certain players or statistics are missing, you may need to import data for previous seasons to establish player history.

## 9. Advantages Over Previous PFR Scraper

The new NFL data import system offers several advantages:

1. **More comprehensive data**: Includes additional statistics not available in PFR
2. **More reliable**: Less prone to rate limiting or scraper failures
3. **Better performance**: Faster import times, especially for large datasets
4. **More granular control**: Import specific data types as needed
5. **Background processing**: Support for long-running imports in the background

## 10. Resources and References

1. [nfl-data-py package documentation](https://pypi.org/project/nfl-data-py/)
2. [NFL API Resources Gist](https://gist.github.com/nntrn/ee26cb2a0716de0947a0a4e9a157bc1c)
3. [NFL Fantasy Data Fields Reference](https://api.fantasy.nfl.com/v2/docs)