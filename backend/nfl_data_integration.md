# NFL Data Integration Reference

## Data Sources Overview

### 1. nfl-data-py Python Package
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

### 2. NFL API Resources
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
- **Rate limiting**: Implement backoff strategies and response caching to respect API limits
- **Error handling**: Check for HTTP status codes and implement retry logic for failed requests

## Data Field Mappings

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

## Data Transformation Requirements

### 1. Height Conversion
Convert from "feet-inches" format to total inches:
```python
if height_str and '-' in height_str:
    feet, inches = height_str.split('-')
    height_inches = int(feet) * 12 + int(inches)
```

### 2. Derived Statistics Calculation
| Derived Stat         | Formula                        |
|----------------------|--------------------------------|
| Passing TD Rate      | `pass_td / pass_attempts`      |
| Completion Percentage| `completions / pass_attempts`  |
| Yards per Attempt    | `pass_yards / pass_attempts`   |
| Rush Yards per Attempt| `rush_yards / rush_attempts`  |
| Catch Rate           | `receptions / targets`         |
| Yards per Target     | `rec_yards / targets`          |
| Yards per Reception  | `rec_yards / receptions`       |

### 3. Season Totals Aggregation
- Aggregate weekly statistics into season totals
- Count distinct weeks to calculate games played

### 4. Fantasy Scoring Calculation
- **Half-PPR Scoring System** (Default):
  - 0.04 points per passing yard (1 point per 25 yards)
  - 4 points per passing touchdown
  - -1 point per interception
  - 0.1 points per rushing/receiving yard (1 point per 10 yards)
  - 6 points per rushing/receiving touchdown
  - 0.5 points per reception

### 5. Advanced Usage Metrics
- Target Share (percentage of team targets)
- Air Yards and Average Depth of Target (aDOT)
- Red Zone Usage
- Yards After Catch (YAC)
- Breakaway Run Rates

## Implementation Architecture

### New Service: NFLDataImportService
```python
class NFLDataImportService:
    """Service for importing NFL data from various sources."""
    
    def __init__(self, db: Session):
        self.db = db
        
    async def import_player_data(self, season: int) -> Dict[str, Any]:
        """Import player data for the specified season."""
        pass
        
    async def import_weekly_stats(self, season: int) -> Dict[str, Any]:
        """Import weekly statistics for the specified season."""
        pass
        
    async def import_team_stats(self, season: int) -> Dict[str, Any]:
        """Import team statistics for the specified season."""
        pass
        
    async def import_nfl_api_data(self, endpoint: str, season: int) -> Dict[str, Any]:
        """Import data from NFL API for the specified endpoint and season."""
        pass
        
    async def calculate_season_totals(self, season: int) -> Dict[str, Any]:
        """Calculate season totals from weekly data."""
        pass
```

### New API Routes
```python
@router.post("/import/nfl-data/{season}")
async def import_nfl_data(season: int, db: Session = Depends(get_db)):
    """Import NFL data for the specified season."""
    service = NFLDataImportService(db)
    results = await service.import_player_data(season)
    weekly_stats = await service.import_weekly_stats(season)
    team_stats = await service.import_team_stats(season)
    season_totals = await service.calculate_season_totals(season)
    
    return {
        "player_import": results,
        "weekly_stats": weekly_stats,
        "team_stats": team_stats,
        "season_totals": season_totals
    }

@router.post("/import/nfl-api/{endpoint}/{season}")
async def import_nfl_api_data(endpoint: str, season: int, db: Session = Depends(get_db)):
    """Import data from NFL API for the specified endpoint and season."""
    service = NFLDataImportService(db)
    results = await service.import_nfl_api_data(endpoint, season)
    return results
```

## Integration Guidelines

### 1. Dependencies to Add
```
pip install nfl-data-py requests pandas aiohttp
```

### 2. Files to Create or Modify
- New Files:
  - `/backend/services/nfl_data_import_service.py`
  - `/backend/tests/unit/test_nfl_data_import_service.py`
  
- Existing Files to Modify:
  - `/backend/api/routes/batch.py` - Add new import endpoints
  - `/backend/services/projection_service.py` - Update to use new data sources
  - `/backend/services/data_validation.py` - Add validation for new data

### 3. Data Validation and Error Handling
- Implement robust error handling for API calls
- Add data validation rules for imported data
- Create reconciliation process for handling conflicting data sources
- Verify that season totals match the sum of weekly stats
- Check that games played counts match actual appearances
- Log all import operations with success/error counts

### 4. Performance Considerations
- Use batch processing for large imports
- Implement caching for frequently accessed data
- Apply rate limiting for API calls
- Track progress for long-running imports

### 5. Special Edge Cases
- **Player Trades**: Track historical stats with previous teams and update current team references
- **Injuries**: Track player status changes and validate against actual game appearances
- **Rookie Projections**: Handle rookies who lack historical NFL data using college stats and draft position
- **Mid-Season Role Changes**: Adjust for players whose usage patterns change during the season

## Example Implementations

### Importing Player Data
```python
import nfl_data_py as nfl
import pandas as pd
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional

async def import_players(season: int, db: Session) -> Dict[str, Any]:
    """Import player data for the specified season."""
    try:
        # Get player data from nfl-data-py
        player_data = nfl.import_players([season])
        
        # Process and transform data
        players_added = 0
        players_updated = 0
        
        for _, row in player_data.iterrows():
            # Skip rows with missing player_id
            if pd.isna(row.get('player_id')):
                continue
                
            # Check if player exists
            existing_player = db.query(Player).filter(
                Player.player_id == row['player_id']
            ).first()
            
            # Convert height
            height_inches = None
            if row.get('height') and '-' in row['height']:
                feet, inches = row['height'].split('-')
                height_inches = int(feet) * 12 + int(inches)
            
            player_data = {
                "player_id": row['player_id'],
                "name": row['display_name'],
                "position": row['position'],
                "team": row['team'],
                "status": row.get('status'),
                "height": height_inches,
                "weight": row.get('weight')
            }
            
            if existing_player:
                # Update existing player
                for key, value in player_data.items():
                    setattr(existing_player, key, value)
                players_updated += 1
            else:
                # Create new player
                new_player = Player(**player_data)
                db.add(new_player)
                players_added += 1
        
        db.commit()
        return {
            "players_added": players_added,
            "players_updated": players_updated,
            "total_processed": players_added + players_updated
        }
    except Exception as e:
        db.rollback()
        raise Exception(f"Error importing player data: {str(e)}")
```

### Importing Weekly Stats
```python
async def import_weekly_stats(season: int, db: Session) -> Dict[str, Any]:
    """Import weekly statistics for the specified season."""
    try:
        # Get weekly stats data from nfl-data-py
        weekly_data = nfl.import_weekly_data([season])
        
        # Process and transform data
        stats_added = 0
        
        for _, row in weekly_data.iterrows():
            # Skip rows with missing player_id
            if pd.isna(row.get('player_id')):
                continue
                
            # Check if player exists
            player = db.query(Player).filter(
                Player.player_id == row['player_id']
            ).first()
            
            if not player:
                continue  # Skip if player not in database
                
            # Check if weekly stat already exists
            existing_stat = db.query(WeeklyStat).filter(
                WeeklyStat.player_id == row['player_id'],
                WeeklyStat.season == season,
                WeeklyStat.week == row['week']
            ).first()
            
            if existing_stat:
                continue  # Skip if already imported
                
            # Create new weekly stat record
            stat_data = {
                "player_id": row['player_id'],
                "season": season,
                "week": row['week'],
                "pass_attempts": row.get('pass_attempts'),
                "completions": row.get('completions'),
                "pass_yards": row.get('passing_yards'),
                "pass_td": row.get('passing_tds'),
                "interceptions": row.get('interceptions'),
                "rush_attempts": row.get('rushing_attempts'),
                "rush_yards": row.get('rushing_yards'),
                "rush_td": row.get('rushing_tds'),
                "targets": row.get('targets'),
                "receptions": row.get('receptions'),
                "rec_yards": row.get('receiving_yards'),
                "rec_td": row.get('receiving_tds')
            }
            
            new_stat = WeeklyStat(**stat_data)
            db.add(new_stat)
            stats_added += 1
        
        db.commit()
        return {
            "weekly_stats_added": stats_added
        }
    except Exception as e:
        db.rollback()
        raise Exception(f"Error importing weekly stats: {str(e)}")
```

### API Error Handling Implementation
```python
async def make_api_request(endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Make a request to the NFL API with proper error handling."""
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json'
    }
    
    url = f"https://api.nfl.com/v3/{endpoint}"
    
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:  # Rate limit exceeded
                        retry_count += 1
                        wait_time = min(2 ** retry_count, 60)  # Exponential backoff
                        await asyncio.sleep(wait_time)
                    else:
                        raise Exception(f"API request failed with status {response.status}: {await response.text()}")
        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                raise Exception(f"Failed to make API request after {max_retries} attempts: {str(e)}")
            await asyncio.sleep(1)
    
    raise Exception("Maximum retries exceeded")
```

## Best Practices for Implementation

1. **Data Requirements for Projections**:
   - Maintain at least 2-3 seasons of historical data
   - Use weekly stats for more granular analysis, not just season totals
   - Include snap counts and usage metrics when available
   - Incorporate contextual data (coaching changes, offensive scheme, offensive line rankings)

2. **Data Consistency Considerations**:
   - Ensure consistent team abbreviations across data sources
   - Map position codes consistently
   - Handle missing or null values systematically
   - Implement thorough data validation

3. **Data Cleansing and Sanitization**:
   - Convert string values to appropriate numeric types
   - Implement proper detection and handling of missing values
   - Check for and handle duplicate player records
   - Validate numerical statistics (check for negative values or outliers)

4. **Monitoring and Data Quality**:
   - Implement validation checks to verify data consistency
   - Log all import operations with detailed success/error counts
   - Track batch processing progress for long-running operations
   - Generate validation reports including issues found and fixes applied

5. **Incremental Data Loading**: Load data incrementally to avoid overwhelming the system.

6. **Data Reconciliation**: Create clear rules for resolving conflicts when multiple sources provide different values.

7. **Error Recovery**: Implement recovery mechanisms for failed imports.

8. **Testing Strategy**: Create tests with mock data for each import function.

9. **Logging and Monitoring**: Log all data imports and track performance metrics.

---

## Resources and References

1. [nfl-data-py package documentation](https://pypi.org/project/nfl-data-py/)
2. [NFL API Resources Gist](https://gist.github.com/nntrn/ee26cb2a0716de0947a0a4e9a157bc1c)
3. [NFL Fantasy Data Fields Reference](https://api.fantasy.nfl.com/v2/docs)