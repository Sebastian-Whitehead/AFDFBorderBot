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


async def test_create_session_row(shared_db):
    from database.user_functions import create_session
    new_id = await create_session("zz_test_session", description="d", external_event_id="zz-ev-1")
    assert new_id is not None
    db = await get_shared_db_manager()
    rows = await db.execute_raw_query("SELECT * FROM military.sessions WHERE id = :i", {"i": new_id})
    assert rows[0]["session_name"] == "zz_test_session" and rows[0]["external_event_id"] == "zz-ev-1"
    assert rows[0]["timeline"] == "A"
    assert (await create_session("zz_test_null"))is not None
    from database.user_functions import end_latest_session
    import datetime
    early = datetime.datetime(2000, 1, 1, tzinfo=datetime.timezone.utc)
    await db.execute_raw_query("UPDATE military.sessions SET end_at = now() WHERE end_at IS NULL AND session_name NOT LIKE 'zz_test_%'")
    await create_session("zz_test_late", start_at=datetime.datetime(2999, 1, 1, tzinfo=datetime.timezone.utc))
    assert (await end_latest_session())[0] == "before_start"
    assert (await end_latest_session(datetime.datetime(2999, 1, 2, tzinfo=datetime.timezone.utc)))[0] == "ended"
    status, row = await end_latest_session()  # next latest open one is zz_test_null (start now)
    assert status == "ended" and row["session_name"] == "zz_test_null"
    await end_latest_session()
    await end_latest_session()
    assert (await end_latest_session())[0] == "none_open"
    await db.execute_raw_query("DELETE FROM military.sessions WHERE session_name LIKE 'zz_test_%'")


async def test_attendance_roundtrip(shared_db):
    from database.attendance_functions import find_unaccounted, submit_attendance, get_open_session
    from database.user_functions import create_session, create_service_record, ensure_player_identity
    s1, d1 = ids(30)
    s2, d2 = ids(31)
    for s, d in ((s1, d1), (s2, d2)):
        assert await create_user(f"zz_test_att{d[-2:]}", s, d, rank="EN0")
    db = await get_shared_db_manager()
    await db.execute_raw_query("UPDATE military.sessions SET end_at = now() WHERE end_at IS NULL")
    sid = await create_session("zz_test_att")
    assert (await get_open_session())["id"] == sid
    missing = await find_unaccounted([d1])
    assert d2 in missing and d1 not in missing
    res = await submit_attendance(sid, [{"discord_id": d1, "status": "on_leave", "notes": "LOA"},
                                        {"discord_id": d2, "status": "absent"}, {"discord_id": "900000000000999999", "status": "present"}], "1")
    assert res == {"saved": [d1, d2], "skipped": ["900000000000999999"]}
    # resubmit overwrites instead of failing on the unique constraint
    assert (await submit_attendance(sid, [{"discord_id": d1, "status": "present"}], "1"))["saved"] == [d1]
    rows = await db.execute_raw_query("SELECT attendance_status::text AS st FROM military.attendance WHERE session_id = :s ORDER BY id", {"s": sid})
    assert [r["st"] for r in rows] == ["present", "absent"]
    await db.execute_raw_query("DELETE FROM military.attendance WHERE session_id = :s", {"s": sid})
    await db.execute_raw_query("DELETE FROM military.sessions WHERE session_name LIKE 'zz_test_%'")


async def test_list_sessions_paging(shared_db):
    import datetime
    from database.attendance_functions import list_sessions
    from database.user_functions import create_session
    db = await get_shared_db_manager()
    await db.execute_raw_query("DELETE FROM military.sessions WHERE timeline = 'zz_test_tl'")
    for n in range(12):
        await create_session(f"zz_test_s{n}", timeline="zz_test_tl",
                             start_at=datetime.datetime(2999, 1, 1 + n, tzinfo=datetime.timezone.utc))
    rows, total = await list_sessions("ZZ_TEST_TL", 1)  # case-insensitive
    assert total == 12 and len(rows) == 10 and rows[0]["session_name"] == "zz_test_s11"  # newest first
    rows, _ = await list_sessions("zz_test_tl", 2)
    assert [r["session_name"] for r in rows] == ["zz_test_s1", "zz_test_s0"]
    assert (await list_sessions("zz_test_tl", 3))[0] == []
    await db.execute_raw_query("DELETE FROM military.sessions WHERE timeline = 'zz_test_tl'")


async def test_load_session_attendance(shared_db):
    from database.attendance_functions import load_session_attendance, submit_attendance
    from database.user_functions import create_session
    s, d = ids(32)
    assert await create_user("zz_test_ls", s, d, rank="EN0")
    sid = await create_session("zz_test_ls")
    await submit_attendance(sid, [{"discord_id": d, "status": "excused", "notes": "n"}], "1")
    sess, rows = await load_session_attendance(sid)
    assert sess["session_name"] == "zz_test_ls" and rows == [{"discord_id": d, "status": "excused", "notes": "n"}]
    assert await load_session_attendance(999999999) == (None, [])
    db = await get_shared_db_manager()
    await db.execute_raw_query("DELETE FROM military.attendance WHERE session_id = :s", {"s": sid})
    await db.execute_raw_query("DELETE FROM military.sessions WHERE id = :s", {"s": sid})


async def test_update_session(shared_db):
    import datetime
    from database.attendance_functions import update_session
    from database.user_functions import create_session
    db = await get_shared_db_manager()
    t = datetime.datetime(2999, 1, 1, tzinfo=datetime.timezone.utc)
    sid = await create_session("zz_test_upd", start_at=t)
    assert (await update_session(sid))[0] == "no_changes"
    assert (await update_session(999999999, operation="x"))[0] == "not_found"
    assert (await update_session(sid, end_at=t - datetime.timedelta(days=1)))[0] == "bad_dates"
    status, row = await update_session(sid, session_name="zz_test_upd2", timeline="B", end_at=t + datetime.timedelta(hours=2))
    assert status == "updated" and row["session_name"] == "zz_test_upd2"
    got = (await db.execute_raw_query("SELECT * FROM military.sessions WHERE id = :i", {"i": sid}))[0]
    assert got["timeline"] == "B" and got["end_at"] == t + datetime.timedelta(hours=2) and got["updated_at"] > got["created_at"]
    assert (await update_session(sid, start_at=t + datetime.timedelta(days=1)))[0] == "bad_dates"  # start after existing end
    await db.execute_raw_query("DELETE FROM military.sessions WHERE id = :i", {"i": sid})
