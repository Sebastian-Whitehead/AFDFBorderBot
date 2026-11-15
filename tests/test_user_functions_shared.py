from pathlib import Path

import pytest

from database.db_manager import get_shared_db_manager
from database.user_functions import create_user, get_user_info, modify_user
from database import get_user_count_by_rank
from tests.helpers import ids

pytestmark = pytest.mark.asyncio


async def test_u8_adopt_existing_game_player(shared_db):
    s, d = ids(20)
    db = await get_shared_db_manager()
    await db.execute_raw_query("SELECT public.fab_ensure_player_account('zz_test_game', :s, NULL)", {"s": int(s)})
    assert await create_user("zz_test_game", s, d) is not None
    assert await get_user_info(d) is not None
    rows = await db.execute_raw_query("SELECT count(*) AS n FROM public.identities_player WHERE steam_id = :s", {"s": int(s)})
    assert rows[0]["n"] == 1


async def test_u9_modify_rank_event(shared_db):
    s, d = ids(21)
    assert await create_user("zz_test_a", s, d)
    assert await modify_user(d, rank=9, reason="r") is True
    assert (await get_user_info(d))["rank"] == 9
    db = await get_shared_db_manager()
    rows = await db.execute_raw_query(
        "SELECT r.current_rank, e.notes FROM military.service_records r "
        "JOIN public.identities_player p ON p.id = r.player_identity_id "
        "JOIN military.service_events e ON e.service_record_id = r.id AND e.event_type = 'rank_changed' "
        "WHERE p.steam_id = :s", {"s": int(s)})
    assert len(rows) == 1 and rows[0]["current_rank"] == "UO" and rows[0]["notes"] == "r"


async def test_u10_count_by_rank(shared_db):
    before = await get_user_count_by_rank()
    assert await create_user("zz_test_a", *ids(22), rank=2)
    assert await create_user("zz_test_b", *ids(23), rank=5)
    after = await get_user_count_by_rank()
    assert after.get(2, 0) - before.get(2, 0) == 1
    assert after.get(5, 0) - before.get(5, 0) == 1


async def test_u11_invalid_steam_id(shared_db):
    db = await get_shared_db_manager()
    q = "SELECT count(*) AS n FROM public.identities_player WHERE alias = 'zz_test_bad'"
    before = (await db.execute_raw_query(q))[0]["n"]
    assert await create_user("zz_test_bad", "abc", ids(24)[1]) is None
    assert (await db.execute_raw_query(q))[0]["n"] == before


async def test_u12_no_money_access(shared_db):
    src = (Path(__file__).resolve().parent.parent / "database" / "user_functions.py").read_text(encoding="utf-8").lower()
    for word in ("economy.", "money", "post_economy", "fab_transfer"):
        assert word not in src
    s, d = ids(25)
    u = await create_user("zz_test_a", s, d)
    assert "money" not in u and "money" not in await get_user_info(d)
