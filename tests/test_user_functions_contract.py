import pytest

from database.user_functions import (
    create_user, get_user_info, modify_user,
)

try:
    from tests.helpers import ids
except ImportError:
    try:
        from tests.conftest import ids
    except ImportError:
        from helpers import ids

DISCORD_BASE = 900000000000000000

pytestmark = pytest.mark.asyncio


async def test_u1_create_user(shared_db):
    s, d = ids(1)
    u = await create_user(name="zz_test_a", steam_id=s, discord_id=d)
    assert {"id", "name", "steam_id", "discord_id", "rank", "enlisted"} <= set(u)
    assert u["name"] == "zz_test_a"
    assert u["steam_id"] == s and isinstance(u["steam_id"], str)
    assert u["discord_id"] == d and isinstance(u["discord_id"], str)
    assert u["rank"] == "EN0"
    assert u["enlisted"] is False


async def test_u2_create_enlisted(shared_db):
    s, d = ids(2)
    assert await create_user(name="zz_test_a", steam_id=s, discord_id=d, rank="EN3", enlisted=True)
    info = await get_user_info(d)
    assert info["rank"] == "EN3"
    assert info["enlisted"] is True
    assert info["enlisted_at"] is not None


async def test_u3_duplicates(shared_db):
    s, d = ids(3)
    s2, _ = ids(4)
    assert await create_user(name="zz_test_a", steam_id=s, discord_id=d)
    assert await create_user(name="zz_test_a", steam_id=s, discord_id=ids(5)[1]) is None
    assert await create_user(name="zz_test_a", steam_id=s2, discord_id=d) is None


async def test_u4_get_user_info(shared_db):
    s, d = ids(6)
    assert await create_user(name="zz_test_a", steam_id=s, discord_id=d)
    by_d = await get_user_info(d)
    by_s = await get_user_info(s)
    assert by_d["id"] == by_s["id"]
    assert {"id", "name", "steam_id", "discord_id", "joined_at", "enlisted_at", "rank",
            "notes", "achievements", "last_death", "deaths", "reprimands",
            "extra_data", "enlisted"} <= set(by_d)
    assert await get_user_info(str(DISCORD_BASE + 999)) is None


async def test_u5_modify_user(shared_db):
    s, d = ids(7)
    assert await create_user(name="zz_test_a", steam_id=s, discord_id=d)

    assert await modify_user(d, name="zz_test_b") is True
    assert (await get_user_info(d))["name"] == "zz_test_b"
    assert await modify_user(d, rank="EN4") is True
    assert (await get_user_info(d))["rank"] == "EN4"
    assert await modify_user(d, notes="hello") is True
    assert (await get_user_info(d))["notes"] == "hello"

    assert await modify_user(d, enlisted=False) is True
    info = await get_user_info(d)
    assert info["enlisted"] is False and info["enlisted_at"] is None
    assert await modify_user(d, enlisted=True) is True
    assert (await get_user_info(d))["enlisted"] is True

    assert await modify_user(str(DISCORD_BASE + 999), name="x") is False
