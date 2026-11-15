import pytest

from database import ensure_player_identity, enlist_member
from database.db_manager import get_shared_db_manager
from database.user_functions import get_user_info
from tests.helpers import ids

pytestmark = pytest.mark.asyncio


async def _count(sql, **p):
    db = await get_shared_db_manager()
    return (await db.execute_raw_query(sql, p))[0]["n"]


async def _identities(s):
    return await _count("SELECT count(*) AS n FROM public.identities_player WHERE steam_id = :s", s=int(s))


async def _records(s):
    return await _count(
        "SELECT count(*) AS n FROM military.service_records r JOIN public.identities_player p "
        "ON p.id = r.player_identity_id WHERE p.steam_id = :s", s=int(s))


async def _events(s):
    return await _count(
        "SELECT count(*) AS n FROM military.service_events e JOIN military.service_records r "
        "ON r.id = e.service_record_id JOIN public.identities_player p ON p.id = r.player_identity_id "
        "WHERE p.steam_id = :s AND e.event_type = 'enlisted'", s=int(s))


async def test_i1_identity_only(shared_db):
    s, d = ids(60)
    assert await ensure_player_identity("zz_test_a", s, d) is True
    assert await _identities(s) == 1
    assert await _records(s) == 0


async def test_i2_idempotent(shared_db):
    s, d = ids(61)
    assert await ensure_player_identity("zz_test_a", s, d) is True
    assert await ensure_player_identity("zz_test_a", s, d) is True
    assert await _identities(s) == 1 and await _records(s) == 0


async def test_i3_discord_conflict(shared_db):
    s1, d1 = ids(62)
    s2, d2 = ids(63)
    assert await ensure_player_identity("zz_test_a", s1, d1) is True
    assert await ensure_player_identity("zz_test_b", s1, d2) is False  # identity has another discord_id
    assert await ensure_player_identity("zz_test_b", s2, d1) is False  # discord_id held by another identity
    assert await _identities(s2) == 0


async def test_i4_enlist_no_identity(shared_db):
    assert await enlist_member(ids(64)[1]) == "no_identity"


async def test_i5_enlist_after_identity(shared_db):
    s, d = ids(65)
    assert await ensure_player_identity("zz_test_a", s, d) is True
    assert await enlist_member(d) == "enlisted"
    assert await _records(s) == 1 and await _events(s) == 1
    assert (await get_user_info(d))["enlisted"] is True


async def test_i6_enlist_twice(shared_db):
    s, d = ids(66)
    assert await ensure_player_identity("zz_test_a", s, d) is True
    assert await enlist_member(d) == "enlisted"
    assert await enlist_member(d) == "already_enlisted"
    assert await _records(s) == 1 and await _events(s) == 1


async def test_i7_adopt_game_identity(shared_db):
    s, d = ids(67)
    db = await get_shared_db_manager()
    await db.execute_raw_query("SELECT public.fab_ensure_player_account('zz_test_game', :s, NULL)", {"s": int(s)})
    assert await ensure_player_identity("zz_test_game", s, d) is True
    assert await _identities(s) == 1
    assert await enlist_member(d) == "enlisted"


async def test_identity_without_steam_then_steam_attached(shared_db):
    s, d = ids(70)
    assert await ensure_player_identity("zz_test_nosteam", None, d)
    assert await ensure_player_identity("zz_test_nosteam", None, d)  # idempotent
    assert await _count("SELECT count(*) AS n FROM public.identities_player WHERE discord_id = :d", d=int(d)) == 1
    assert await _count("SELECT count(*) AS n FROM public.identities_player WHERE discord_id = :d AND steam_id IS NULL", d=int(d)) == 1
    assert await enlist_member(d) == "enlisted"  # enlist works without a Steam ID
    assert await ensure_player_identity("zz_test_nosteam", s, d)  # later /approve with a Steam ID attaches it
    assert await _identities(s) == 1
    assert await _count("SELECT count(*) AS n FROM public.identities_player WHERE discord_id = :d", d=int(d)) == 1


async def test_add_member_attaches_steam_to_null_steam_identity(shared_db):
    from database import create_user
    s, d = ids(71)
    assert await ensure_player_identity("zz_test_nosteam2", None, d)
    assert await create_user("zz_test_nosteam2", s, d)
    assert await _identities(s) == 1
    assert await _count("SELECT count(*) AS n FROM public.identities_player WHERE discord_id = :d", d=int(d)) == 1


async def test_create_user_without_steam(shared_db):
    from database import create_user
    _, d = ids(74)
    assert await create_user("zz_test_nosteam3", None, None) is None  # nothing to identify them by
    user = await create_user("zz_test_nosteam3", None, d, rank="EN2")
    assert user["steam_id"] is None and user["rank"] == "EN2"
    assert (await get_user_info(d))["steam_id"] is None


async def test_set_steam_id_outcomes(shared_db):
    from database import set_steam_id
    s, d = ids(72)
    s2, _ = ids(73)
    assert await set_steam_id(d, s) == "no_identity"
    assert await ensure_player_identity("zz_test_ss", None, d)
    assert await set_steam_id(d, s) == "updated"
    assert await set_steam_id(d, s) == "already_set"
    assert await set_steam_id(d, s2) == "different_steam"
    s3, d3 = ids(74)
    assert await ensure_player_identity("zz_test_ss2", None, d3)
    assert await set_steam_id(d3, s) == "steam_in_use"
    assert await set_steam_id("abc", s) == "error"


async def test_create_service_record_only(shared_db):
    from database import create_service_record
    s, d = ids(75)
    assert await create_service_record(d, "EN2") == "no_identity"
    assert await ensure_player_identity("zz_test_sr", s, d)
    assert await create_service_record(d, "EN2") == "created"
    assert await _records(s) == 1 and await _events(s) == 0  # record only, no enlisted event
    assert await create_service_record(d, "EN2") == "already_exists"
    assert await create_service_record("abc", "EN2") == "error"
    assert await create_service_record(d, "XX") == "error"
    assert await enlist_member(d) == "enlisted"  # enlisting an existing record just adds the event
    assert await _records(s) == 1 and await _events(s) == 1
