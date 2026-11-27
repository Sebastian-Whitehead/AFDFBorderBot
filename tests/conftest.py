import os
import socket
from urllib.parse import urlparse
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
# Local `afdfbot/` and `database/` packages must win over any pip package.
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env.test")

from tests.helpers import cleanup, cleanup_shared  # noqa: E402
from tests.helpers import ids as _ids  # noqa: E402


@pytest_asyncio.fixture(autouse=True)
async def _close_db():
    yield
    # Engines are bound to the test's event loop; drop them so the next test rebuilds.
    from database.db_manager import close_database
    await close_database()
    # close_database() closes both the local and the shared manager.


def require_reachable(url: str) -> None:
    """Skip fast instead of hanging when the shadow DB container is not running."""
    u = urlparse(url)
    try:
        socket.create_connection((u.hostname, u.port or 5432), timeout=1).close()
    except OSError:
        pytest.skip("shadow DB not running (bash migration/build_shadow.sh)")


@pytest_asyncio.fixture
async def shared_db(monkeypatch):
    url = os.getenv("TEST_SHARED_DATABASE_URL")
    if not url:
        pytest.skip("TEST_SHARED_DATABASE_URL not set")
    require_reachable(url)
    monkeypatch.setenv("SUPABASE_DATABASE_URL", url)
    from database.db_manager import close_database
    await close_database()  # never reuse a manager built for another URL
    await cleanup_shared()
    yield
    await cleanup_shared()


@pytest_asyncio.fixture
async def local_db(monkeypatch):
    url = os.getenv("TEST_LOCAL_DATABASE_URL")
    if not url:
        pytest.skip("TEST_LOCAL_DATABASE_URL not set")
    monkeypatch.setenv("DATABASE_URL", url)
    from database.db_manager import close_database
    await close_database()  # never reuse a manager built for another URL
    await cleanup()
    yield
    await cleanup()


@pytest.fixture
def ids():
    return _ids
