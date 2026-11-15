import os

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

pytestmark = [pytest.mark.asyncio, pytest.mark.db_shared]

STEAM = 76561190000000001
DISCORD = 900000000000000001


@pytest_asyncio.fixture
async def conn():
    url = os.getenv("TEST_SHARED_DATABASE_URL")
    if not url:
        pytest.skip("TEST_SHARED_DATABASE_URL not set")
    engine = create_async_engine(url)
    try:
        async with engine.connect() as c:
            trans = await c.begin()
            try:
                yield c
            finally:
                await trans.rollback()
    finally:
        await engine.dispose()


async def _ensure(c):
    await c.execute(text("SELECT public.fab_ensure_player_account('zz_test_p', :s, :d)"), {"s": STEAM, "d": DISCORD})


async def _player_count(c):
    r = await c.execute(text("SELECT count(*) FROM public.identities_player WHERE discord_id = :d"), {"d": DISCORD})
    return r.scalar_one()


async def test_sh1_ensure_player_account_idempotent(conn):
    await _ensure(conn)
    assert await _player_count(conn) == 1
    await _ensure(conn)
    assert await _player_count(conn) == 1


async def _insert_record(c, rank):
    await c.execute(
        text(
            "INSERT INTO military.service_records (player_identity_id, organization_id, current_rank, service_status) "
            "SELECT p.id, o.id, :r, 'active' FROM public.identities_player p, public.identities_organizations o "
            "WHERE p.discord_id = :d AND o.name = 'AFDF - Para Raiders'"
        ),
        {"r": rank, "d": DISCORD},
    )


async def test_sh2_service_record_rank_check(conn):
    await _ensure(conn)
    async with conn.begin_nested():
        await _insert_record(conn, "PRES")
    with pytest.raises(IntegrityError, match="service_records_current_rank_check"):
        async with conn.begin_nested():
            await _insert_record(conn, "XX")


async def _insert_leave(c, status):
    await c.execute(
        text(
            "INSERT INTO military.leave_requests (service_record_id, end_date, status) "
            "SELECT sr.id, current_date + 7, :s FROM military.service_records sr "
            "JOIN public.identities_player p ON p.id = sr.player_identity_id WHERE p.discord_id = :d"
        ),
        {"d": DISCORD, "s": status},
    )


async def test_sh3_one_active_leave_per_service_record(conn):
    await _ensure(conn)
    await _insert_record(conn, "EN1")
    await _insert_leave(conn, "active")
    with pytest.raises(IntegrityError, match="leave_requests_one_active"):
        async with conn.begin_nested():
            await _insert_leave(conn, "active")
    await _insert_leave(conn, "cancelled")


async def test_sh4_discord_id_unique(conn):
    await _ensure(conn)
    with pytest.raises(IntegrityError, match="identities_player_discord_id_uniq"):
        async with conn.begin_nested():
            await conn.execute(
                text("INSERT INTO public.identities_player (discord_id) VALUES (:d)"), {"d": DISCORD}
            )


async def test_sh5_single_para_raiders_org(conn):
    r = await conn.execute(text("SELECT count(*) FROM public.identities_organizations WHERE name = 'AFDF - Para Raiders'"))
    assert r.scalar_one() == 1
