#!/usr/bin/env python
import sys
from pathlib import Path

# Add the project root directory to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.database.database import SessionLocal
from backend.database.models import Player
from backend.api.schemas import PlayerResponse
from pydantic import ConfigDict
import json

def debug_rookies_api():
    """Debug script to test the conversion from ORM objects to Pydantic models"""
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
            
            # Test manual conversion to dict
            try:
                player_dict = {
                    "player_id": sample.player_id,
                    "name": sample.name,
                    "team": sample.team,
                    "position": sample.position,
                    "status": sample.status,
                    "created_at": sample.created_at,
                    "updated_at": sample.updated_at,
                    "date_of_birth": sample.date_of_birth,
                    "height": sample.height,
                    "weight": sample.weight,
                    "depth_chart_position": sample.depth_chart_position,
                    "draft_position": sample.draft_position,
                    "draft_team": sample.draft_team,
                    "draft_round": sample.draft_round,
                    "draft_pick": sample.draft_pick,
                }
                print(f"\nManual dict conversion successful")
                
                try:
                    # Test JSON serialization
                    json_str = json.dumps(player_dict, default=str)
                    print(f"JSON serialization successful")
                    
                    # Test PlayerResponse model
                    response_model = PlayerResponse(**player_dict)
                    print(f"Pydantic conversion successful: {response_model.model_dump()}")
                except Exception as e:
                    print(f"Pydantic conversion error: {str(e)}")
            except Exception as e:
                print(f"Dict conversion error: {str(e)}")
            
    finally:
        db.close()

if __name__ == "__main__":
    debug_rookies_api()