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
