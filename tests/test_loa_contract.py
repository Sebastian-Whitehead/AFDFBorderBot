from datetime import date

from database.loa_functions import LOAManager as L
from database.user_functions import create_user

try:
    from tests.helpers import ids
except ImportError:
    from tests.conftest import ids

KEYS = {"id", "discord_id", "username", "start_date", "end_date", "reason",
        "status", "submitted_at", "last_modified"}


async def test_l1_parse_end_date():
    assert await L.parse_end_date("2030-01-31") == date(2030, 1, 31)
    assert await L.parse_end_date("01/31/2030") == date(2030, 1, 31)
    assert await L.parse_end_date("31-01-2030") is None
    assert await L.parse_end_date("garbage") is None


async def test_l2_create_and_get(shared_db):
    s, d = ids(1)
    await create_user('zz_test_user', s, d)
    assert await L.create_or_update_loa(d, "zz_test_user", "2030-01-31", "trip") == (False, "submitted")
    r = await L.get_active_loa_by_discord_id(d)
    assert KEYS <= set(r)
    assert r["discord_id"] == d and isinstance(r["discord_id"], str)
    assert r["status"] == "active"
    assert r["reason"] == "trip"
    assert await L.parse_end_date(str(r["end_date"])) == date(2030, 1, 31)


async def test_l3_update(shared_db):
    s, d = ids(1)
    await create_user('zz_test_user', s, d)
    await L.create_or_update_loa(d, "zz_test_user", "2030-01-31", "trip")
    assert await L.create_or_update_loa(d, "zz_test_user", "2030-02-15", "longer") == (True, "updated")
    r = await L.get_active_loa_by_discord_id(d)
    assert await L.parse_end_date(str(r["end_date"])) == date(2030, 2, 15)
    assert r["reason"] == "longer"
    assert [x for x in await L.get_all_active_loas() if x["discord_id"] == d].__len__() == 1


async def test_l4_update_keeps_reason(shared_db):
    s, d = ids(1)
    await create_user('zz_test_user', s, d)
    await L.create_or_update_loa(d, "zz_test_user", "2030-01-31", "trip")
    await L.create_or_update_loa(d, "zz_test_user", "2030-02-15", None)
    assert (await L.get_active_loa_by_discord_id(d))["reason"] == "trip"


async def test_l5_ordering_newest_first(shared_db):
    s1, d1 = ids(1)
    s2, d2 = ids(2)
    await create_user('zz_test_one', s1, d1)
    await create_user('zz_test_two', s2, d2)
    await L.create_or_update_loa(d1, "zz_test_one", "2030-01-31", "a")
    await L.create_or_update_loa(d2, "zz_test_two", "2030-01-31", "b")
    mine = [x["discord_id"] for x in await L.get_all_active_loas() if x["discord_id"] in (d1, d2)]
    assert mine == [d2, d1]


async def test_l6_cancel(shared_db):
    s, d = ids(1)
    await create_user('zz_test_user', s, d)
    await L.create_or_update_loa(d, "zz_test_user", "2030-01-31", "trip")
    assert await L.cancel_loa(d) is True
    assert await L.cancel_loa(d) is False
    assert await L.get_active_loa_by_discord_id(d) is None


async def test_l7_cleanup_expired(shared_db):
    s, d = ids(1)
    await create_user('zz_test_user', s, d)
    assert await L.create_or_update_loa(d, "zz_test_user", "2000-01-01", None) == (False, "submitted")
    await L.cleanup_expired_loas()
    assert await L.get_active_loa_by_discord_id(d) is None
