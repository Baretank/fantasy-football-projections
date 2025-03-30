# Fantasy Football Projections Scripts

This directory contains utility scripts for data import, validation, and maintenance of the Fantasy Football Projections system.

## Data Import Scripts

### upload_season.py
Imports player statistics from Pro Football Reference for a specific season. Includes rate limiting to ensure responsible web scraping.

```bash
# Import all positions for 2024
python backend/scripts/upload_season.py --season 2024

# Import only QBs for 2024
python backend/scripts/upload_season.py --season 2024 --position QB

# Import WRs with data verification
python backend/scripts/upload_season.py --season 2024 --position WR --verify

# Conservative rate limiting for larger imports
python backend/scripts/upload_season.py --season 2024 --batch-size 3 --batch-delay 5.0 --min-delay 1.0 --max-delay 2.0 --max-concurrent 2
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
- Rate limiting is implemented to prevent server overload (see Rate Limiting documentation)
- All scripts support the `--dry-run` flag to preview operations without modifying the database
- Verification mode validates statistical totals against game-by-game data
- All scripts log operations to `logs/import_log.txt` for troubleshooting

## Current Progress

The following features have been implemented:
- ✅ Historical player data import from Pro Football Reference
- ✅ Rookie data import and conversion
- ✅ Draft position-based rookie projection templates
- ✅ Data verification and validation
- ✅ Responsible rate limiting for external data sources
- ✅ Comprehensive error handling and reporting

## Future Enhancements

Planned script improvements:
- [ ] Automated weekly in-season player statistic updates
- [ ] Injury status tracking and updates
- [ ] Strength of schedule data import
- [ ] Weather data integration for game forecasting
- [ ] Advanced batch processing for efficiency