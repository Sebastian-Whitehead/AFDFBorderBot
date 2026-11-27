from datetime import date, datetime, timedelta

import pytest

from database.db_manager import get_shared_db_manager
from database.loa_functions import LOAManager as L
from database.user_functions import create_user
from tests.helpers import ids

pytestmark = pytest.mark.asyncio

_SR = ("SELECT sr.id, p.discord_id FROM military.leave_requests lr "
       "JOIN military.service_records sr ON sr.id = lr.service_record_id "
       "JOIN public.identities_player p ON p.id = sr.player_identity_id WHERE p.discord_id = :d")


async def test_l8_service_record_link(shared_db):
    s, d = ids(30)
    db = await get_shared_db_manager()
    assert await L.create_or_update_loa(d, "u", "2030-01-31", "x") == (False, "failed")
    assert await db.execute_raw_query(_SR, {"d": int(d)}) == []
    assert await create_user("zz_test_l", s, d)
    assert await L.create_or_update_loa(d, "u", "2030-01-31", "x") == (False, "submitted")
    rows = await db.execute_raw_query(_SR, {"d": int(d)})
    assert len(rows) == 1


async def test_l9_dd_mm_yyyy_format(shared_db):
    s, d = ids(31)
    assert await create_user("zz_test_l", s, d)
    await L.create_or_update_loa(d, "u", "31/01/2030")
    assert (await L.get_active_loa_by_discord_id(d))["end_date"] == "2030-01-31"


async def test_l10_loa_list_compat(shared_db):
    for n in (32, 33):
        s, d = ids(n)
        assert await create_user("zz_test_l", s, d)
        await L.create_or_update_loa(d, "u", "2030-01-31", "r")
    mine = [x for x in await L.get_all_active_loas() if x["discord_id"] in (ids(32)[1], ids(33)[1])]
    assert len(mine) == 2
    for loa_data in mine:  # same calls as afdfbot/commands/LOA.py /loa_list
        end_date = await L.parse_end_date(loa_data["end_date"])
        assert isinstance(end_date, date) and end_date >= datetime.now().date()
        str(loa_data["start_date"])


async def test_l11_cleanup_expired(shared_db):
    db = await get_shared_db_manager()
    past, future = ids(34)[1], ids(35)[1]
    for n in (34, 35):
        s, d = ids(n)
        assert await create_user("zz_test_l", s, d)
        await L.create_or_update_loa(d, "u", "2030-01-31")
    y = date.today() - timedelta(days=1)
    # backdate directly: end_date >= start_date CHECK forbids a past end via the manager
    await db.execute_raw_query(
        "UPDATE military.leave_requests SET start_date = :s, end_date = :e WHERE service_record_id IN ("
        "SELECT sr.id FROM military.service_records sr JOIN public.identities_player p "
        "ON p.id = sr.player_identity_id WHERE p.discord_id = :d)",
        {"s": y - timedelta(days=5), "e": y, "d": int(past)})
    await L.cleanup_expired_loas()
    assert await L.get_active_loa_by_discord_id(past) is None
    assert await L.get_active_loa_by_discord_id(future) is not None


async def test_loa_start_and_end_dates(shared_db):
    s, d = ids(31)
    assert await create_user("zz_test_l2", s, d)
    assert await L.create_or_update_loa(d, "u", "2030-01-05", None, start_date="2030-01-02") == (False, "submitted")
    r = await L.get_active_loa_by_discord_id(d)
    assert str(r["start_date"]) == "2030-01-02" and r["end_date"] == "2030-01-05"
    # single-day LOA: start == end
    assert await L.create_or_update_loa(d, "u", "2030-03-01", None, start_date="2030-03-01") == (True, "updated")
    r = await L.get_active_loa_by_discord_id(d)
    assert str(r["start_date"]) == "2030-03-01" and r["end_date"] == "2030-03-01"
    # end before start is refused
    assert await L.create_or_update_loa(d, "u", "2030-02-01", None, start_date="2030-03-01") == (False, "failed")
    # update without a start keeps it valid when the end moves earlier than the old start
    assert await L.create_or_update_loa(d, "u", "2030-02-20") == (True, "updated")
    r = await L.get_active_loa_by_discord_id(d)
    assert str(r["start_date"]) == "2030-02-20" and r["end_date"] == "2030-02-20"
