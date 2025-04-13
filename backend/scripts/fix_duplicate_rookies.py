#!/usr/bin/env python
import sys
from pathlib import Path

# Add the project root directory to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.database.database import SessionLocal
from backend.database.models import Player
from datetime import datetime

def fix_duplicate_rookies():
    """Fix duplicate rookie names in the database by keeping the most recently updated one"""
    db = SessionLocal()
    try:
        # Query all rookies
        rookies = db.query(Player).filter(Player.status == "Rookie").all()
        print(f"Found {len(rookies)} total rookies in the database")
        
        # Check for duplicates
        names = [r.name for r in rookies]
        duplicate_names = set([name for name in names if names.count(name) > 1])
        
        if duplicate_names:
            print(f"\nFound {len(duplicate_names)} duplicated rookie names:")
            total_removed = 0
            
            for name in duplicate_names:
                dupes = db.query(Player).filter(Player.name == name, Player.status == "Rookie").all()
                print(f"\nName: {name}")
                for d in dupes:
                    print(f"  - ID: {d.player_id}, Position: {d.position}, Team: {d.team}, Created: {d.created_at}")
                
                # Sort by created_at or updated_at to keep the newest one
                dupes.sort(key=lambda x: x.updated_at, reverse=True)
                
                # Keep the first one (most recently updated) and delete others
                keep = dupes[0]
                delete = dupes[1:]
                
                print(f"Keeping {keep.name} (ID: {keep.player_id}, Created: {keep.created_at}, Updated: {keep.updated_at})")
                
                for player in delete:
                    print(f"Removing {player.name} (ID: {player.player_id}, Created: {player.created_at})")
                    db.delete(player)
                    total_removed += 1
                
            # Commit the changes
            db.commit()
            print(f"\nFixed {len(duplicate_names)} duplicate names by removing {total_removed} duplicate players.")
            
            # Verify the fix
            rookies_after = db.query(Player).filter(Player.status == "Rookie").all()
            names_after = [r.name for r in rookies_after]
            duplicates_after = [name for name in set(names_after) if names_after.count(name) > 1]
            
            if duplicates_after:
                print(f"WARNING: Still found {len(duplicates_after)} duplicate names after fixing!")
            else:
                print("Verification passed: No more duplicate rookie names found.")
                print(f"Total rookies in database: {len(rookies_after)}")
        else:
            print("No duplicate rookie names found.")
        
    finally:
        db.close()

if __name__ == "__main__":
    fix_duplicate_rookies()