#!/usr/bin/env python
import sys
from pathlib import Path

# Add the project root directory to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.database.database import SessionLocal
from backend.database.models import Player
import json


def debug_rookies():
    """Debug script to verify rookies in the database and inspect the Player model"""
    db = SessionLocal()
    try:
        # Check if there are rookies in the database
        rookies = db.query(Player).filter(Player.status == "Rookie").all()
        print(f"Found {len(rookies)} rookies in the database")

        if rookies:
            print("\nSample rookie data:")
            sample = rookies[0]
            print(f"- ID: {sample.player_id}")
            print(f"- Name: {sample.name}")
            print(f"- Position: {sample.position}")
            print(f"- Team: {sample.team}")
            print(f"- Status: {sample.status}")

            # List all attributes of the Player model
            print("\nPlayer model attributes:")
            for attr in dir(sample):
                if not attr.startswith("_") and attr not in ("metadata", "registry"):
                    value = getattr(sample, attr)
                    if not callable(value):
                        print(f"- {attr}: {value}")

            # Try to JSON serialize a player
            print("\nTesting JSON serialization:")
            try:
                # Directly convert to dict
                player_dict = {
                    "player_id": sample.player_id,
                    "name": sample.name,
                    "team": sample.team,
                    "position": sample.position,
                    "status": sample.status,
                }
                print(f"Dict conversion successful: {json.dumps(player_dict)[:100]}...")
            except Exception as e:
                print(f"Dict conversion error: {e}")

        # Check raw SQL query
        print("\nPerforming raw SQL query:")
        from sqlalchemy import text

        result = db.execute(
            text("SELECT * FROM players WHERE status = 'Rookie' LIMIT 1")
        ).fetchone()
        if result:
            print(f"SQL query successful")
            # Access the result as a tuple
            print(f"First rookie from SQL: {result[2]}")  # Assuming name is column 2
        else:
            print("SQL query returned no results")

    finally:
        db.close()


if __name__ == "__main__":
    debug_rookies()
