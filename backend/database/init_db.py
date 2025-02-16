import sys
from pathlib import Path
import json

# Add the project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)

from backend.database.database import engine, Base
from backend.database.models import Player, BaseStat, Projection, TeamStat

def init_db():
    """Initialize database and required data files."""
    # Create data directory if it doesn't exist
    data_dir = Path(project_root) / "data"
    data_dir.mkdir(exist_ok=True)
    
    # Ensure rookies.json exists with proper structure
    rookie_file = data_dir / "rookies.json"
    if not rookie_file.exists():
        default_rookies = {
            "version": "1.0",
            "last_updated": "",
            "rookies": []
        }
        with open(rookie_file, 'w') as f:
            json.dump(default_rookies, f, indent=2)
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    
    print("Database initialized successfully.")
    print(f"Data directory: {data_dir}")
    print(f"Rookie data file: {rookie_file}")

if __name__ == "__main__":
    init_db()