from pathlib import Path

import pytest

from database.db_manager import get_shared_db_manager
from database.user_functions import create_user, get_user_info, modify_user
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
    assert await modify_user(d, rank="OF1", reason="r") is True
    assert (await get_user_info(d))["rank"] == "OF1"
    db = await get_shared_db_manager()
    rows = await db.execute_raw_query(
        "SELECT r.current_rank, e.notes FROM military.service_records r "
        "JOIN public.identities_player p ON p.id = r.player_identity_id "
        "JOIN military.service_events e ON e.service_record_id = r.id AND e.event_type = 'rank_changed' "
        "WHERE p.steam_id = :s", {"s": int(s)})
    assert len(rows) == 1 and rows[0]["current_rank"] == "OF1" and rows[0]["notes"] == "r"


async def test_invalid_rank_codes(shared_db):
    s, d = ids(22)
    assert await create_user("zz_test_a", s, d, rank="UO") is None
    assert await create_user("zz_test_a", s, d)
    for bad in ("UO", "XX"):
        assert await modify_user(d, rank=bad) is False
    assert (await get_user_info(d))["rank"] == "EN0"


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
