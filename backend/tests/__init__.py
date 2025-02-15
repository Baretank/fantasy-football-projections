from pathlib import Path
import sys

# Add the project root to Python path for imports in tests
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)