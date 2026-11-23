import os

import pytest

from database import db_manager
from database.db_manager import DatabaseManager, _to_asyncpg_url, close_database, get_db_manager, get_shared_db_manager

ASYNC = "postgresql+asyncpg://u:p@h:5432/d"


def test_c1_to_asyncpg_url():
    assert _to_asyncpg_url("postgres://u:p@h:5432/d") == ASYNC
    assert _to_asyncpg_url("postgresql://u:p@h:5432/d") == ASYNC
    assert _to_asyncpg_url(ASYNC) == ASYNC
    assert _to_asyncpg_url("postgresql://u:p@h:5432/d?ssl=require") == ASYNC + "?ssl=require"


async def test_c2_shared_url_unset(monkeypatch):
    monkeypatch.delenv("SUPABASE_DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="SUPABASE_DATABASE_URL"):
        await get_shared_db_manager()


async def test_c3_local_url_unchanged(local_db):
    raw = os.environ["DATABASE_URL"]
    # Pre-change behaviour: only postgres:// was rewritten.
    expected = raw.replace("postgres://", "postgresql+asyncpg://", 1) if raw.startswith("postgres://") else raw
    assert DatabaseManager().database_url == expected


async def test_c4_shared_health(shared_db):
    mgr = await get_shared_db_manager()
    rows = await mgr.execute_raw_query("SELECT to_regclass('military.leave_requests') AS t")
    assert rows[0]["t"] is not None


async def test_c5_two_managers_and_close(local_db, shared_db):
    local = await get_db_manager()
    shared = await get_shared_db_manager()
    assert local is not shared
    assert local.database_url != shared.database_url
    await close_database()
    assert db_manager._db_manager is None
    assert db_manager._shared_db_manager is None
