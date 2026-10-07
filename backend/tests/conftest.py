import sys
from pathlib import Path

# Add project root to python path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest_asyncio
from app.repositories.database import engine

@pytest_asyncio.fixture(autouse=True)
async def cleanup_db_connections():
    yield
    await engine.dispose()

