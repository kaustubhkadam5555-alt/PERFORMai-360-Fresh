import sys
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Ensure backend directory is in sys.path so 'app' is resolvable from anywhere
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app  # noqa: E402


@pytest_asyncio.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
