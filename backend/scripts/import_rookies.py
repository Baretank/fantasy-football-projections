#!/usr/bin/env python
import asyncio
import sys
from pathlib import Path

# Add the project root directory to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.database.database import SessionLocal
from backend.services.rookie_import_service import RookieImportService

async def import_rookies():
    db = SessionLocal()
    try:
        service = RookieImportService(db)
        # Use absolute path to rookies.json
        rookies_path = project_root / "data" / "rookies.json"
        success_count, errors = await service.import_rookies(str(rookies_path))
        print(f'Imported {success_count} rookies. Errors: {len(errors)}')
        if errors:
            print("First few errors:")
            for error in errors[:3]:
                print(f" - {error}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(import_rookies())