# Import all positions for 2024
python backend/scripts/upload_season.py --season 2024

# Import only QBs for 2024
python backend/scripts/upload_season.py --season 2024 --position QB

# Import WRs with data verification
python backend/scripts/upload_season.py --season 2024 --position WR --verify