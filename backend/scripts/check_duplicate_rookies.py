#!/usr/bin/env python
import sys
from pathlib import Path

# Add the project root directory to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.database.database import SessionLocal
from backend.database.models import Player


def check_duplicate_rookies():
    """Check for duplicate rookie names in the database"""
    db = SessionLocal()
    try:
        # Query all rookies
        rookies = db.query(Player).filter(Player.status == "Rookie").all()
        print(f"Found {len(rookies)} total rookies in the database")

        # Check for duplicates
        names = [r.name for r in rookies]
        duplicates = [name for name in set(names) if names.count(name) > 1]

        if duplicates:
            print(f"\nFound {len(duplicates)} duplicated rookie names:")
            for name in duplicates:
                dupes = (
                    db.query(Player).filter(Player.name == name, Player.status == "Rookie").all()
                )
                print(f"\nName: {name}")
                for d in dupes:
                    print(
                        f"  - ID: {d.player_id}, Position: {d.position}, Team: {d.team}, Created: {d.created_at}"
                    )

            # Ask if we should remove duplicates
            print("\nWould you like to remove one of the duplicate players? (y/n)")
            answer = input("> ")

            if answer.lower() == "y":
                for name in duplicates:
                    dupes = (
                        db.query(Player)
                        .filter(Player.name == name, Player.status == "Rookie")
                        .all()
                    )
                    print(f"\nDuplicates for {name}:")
                    for i, d in enumerate(dupes):
                        print(
                            f"{i+1}. ID: {d.player_id}, Position: {d.position}, Team: {d.team}, Created: {d.created_at}"
                        )

                    print(f"Enter number to remove (1-{len(dupes)}) or 0 to skip:")
                    try:
                        choice = int(input("> "))
                        if 1 <= choice <= len(dupes):
                            player_to_remove = dupes[choice - 1]
                            print(
                                f"Removing {player_to_remove.name} with ID {player_to_remove.player_id}"
                            )
                            db.delete(player_to_remove)
                            db.commit()
                            print("Removed successfully!")
                        else:
                            print("Skipping...")
                    except ValueError:
                        print("Invalid choice, skipping...")
        else:
            print("No duplicate rookie names found.")

    finally:
        db.close()


if __name__ == "__main__":
    check_duplicate_rookies()
