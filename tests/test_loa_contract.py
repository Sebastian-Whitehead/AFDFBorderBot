from datetime import date

from database.loa_functions import LOAManager as L

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


async def test_l2_create_and_get(local_db):
    _, d = ids(1)
    assert await L.create_or_update_loa(d, "zz_test_user", "2030-01-31", "trip") == (False, "submitted")
    r = await L.get_active_loa_by_discord_id(d)
    assert KEYS <= set(r)
    assert r["discord_id"] == d and isinstance(r["discord_id"], str)
    assert r["status"] == "active"
    assert r["reason"] == "trip"
    assert await L.parse_end_date(str(r["end_date"])) == date(2030, 1, 31)


async def test_l3_update(local_db):
    _, d = ids(1)
    await L.create_or_update_loa(d, "zz_test_user", "2030-01-31", "trip")
    assert await L.create_or_update_loa(d, "zz_test_user", "2030-02-15", "longer") == (True, "updated")
    r = await L.get_active_loa_by_discord_id(d)
    assert await L.parse_end_date(str(r["end_date"])) == date(2030, 2, 15)
    assert r["reason"] == "longer"
    assert [x for x in await L.get_all_active_loas() if x["discord_id"] == d].__len__() == 1


async def test_l4_update_keeps_reason(local_db):
    _, d = ids(1)
    await L.create_or_update_loa(d, "zz_test_user", "2030-01-31", "trip")
    await L.create_or_update_loa(d, "zz_test_user", "2030-02-15", None)
    assert (await L.get_active_loa_by_discord_id(d))["reason"] == "trip"


async def test_l5_ordering_newest_first(local_db):
    _, d1 = ids(1)
    _, d2 = ids(2)
    await L.create_or_update_loa(d1, "zz_test_one", "2030-01-31", "a")
    await L.create_or_update_loa(d2, "zz_test_two", "2030-01-31", "b")
    mine = [x["discord_id"] for x in await L.get_all_active_loas() if x["discord_id"] in (d1, d2)]
    assert mine == [d2, d1]


async def test_l6_cancel(local_db):
    _, d = ids(1)
    await L.create_or_update_loa(d, "zz_test_user", "2030-01-31", "trip")
    assert await L.cancel_loa(d) is True
    assert await L.cancel_loa(d) is False
    assert await L.get_active_loa_by_discord_id(d) is None


async def test_l7_cleanup_expired(local_db):
    _, d = ids(1)
    await L.create_or_update_loa(d, "zz_test_user", "2000-01-01", None)
    await L.cleanup_expired_loas()
    assert await L.get_active_loa_by_discord_id(d) is None
