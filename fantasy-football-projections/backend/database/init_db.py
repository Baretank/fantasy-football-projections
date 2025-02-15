import sys
from pathlib import Path

# Add the project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)

from backend.database.database import engine, Base
from backend.database.models import Player, BaseStat, Projection

def init_db():
    # Create data directory if it doesn't exist
    data_dir = Path(project_root) / "data"
    data_dir.mkdir(exist_ok=True)
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    
    print("Database initialized successfully.")

if __name__ == "__main__":
    init_db()