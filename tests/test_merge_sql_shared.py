"""fab_merge_player_identities (004) and fab_merge_service_records (005) on the shadow DB."""
import json

import pytest
from sqlalchemy import text

from database.db_manager import get_shared_db_manager
from tests.helpers import ids

pytestmark = pytest.mark.asyncio


async def q(sql, **p):
    """Run SQL in its own transaction; returns the first column of the first row (None if no rows)."""
    db = await get_shared_db_manager()
    async with db.get_session() as s:
        res = await s.execute(text(sql), p)
        row = res.first() if res.returns_rows else None
        await s.commit()
        v = row[0] if row else None
        return json.loads(v) if isinstance(v, str) and v[:1] == "{" else v


async def merge(steam, discord, force=False):
    return await q("SELECT public.fab_merge_player_identities(:s, :d, :f)", s=steam, d=discord, f=force)


async def code(coro):
    try:
        await coro
    except Exception as e:
        return str(e)
    return None


async def ident(n, steam=True, discord=True, alias=None, rank=None, money=0):
    """Test identity in slot n (+ optional AFDF record); returns (identity id, record id or None)."""
    s, d = ids(n)
    pid = await q("INSERT INTO public.identities_player (alias, steam_id, discord_id) VALUES (:a, :s, :d) RETURNING id",
                  a=alias or f"zz_test_{n}", s=int(s) if steam else None, d=int(d) if discord else None)
    await q("UPDATE economy.accounts SET money = :m WHERE player_identity_id = :p", m=money, p=pid)
    rec = None
    if rank:
        rec = await q("""INSERT INTO military.service_records (player_identity_id, organization_id, current_rank, service_status)
                         VALUES (:p, 1, :r, 'active') RETURNING id""", p=pid, r=rank)
    return pid, rec


async def row(pid):
    return (await (await get_shared_db_manager()).execute_raw_query(
        "SELECT * FROM public.identities_player WHERE id = :p", {"p": pid}))


async def accounts(pid):
    return {r["account_name"]: r["money"] for r in await (await get_shared_db_manager()).execute_raw_query(
        "SELECT account_name, money FROM economy.accounts WHERE player_identity_id = :p", {"p": pid})}


# ---- 004 ----

async def test_004_invalid_and_missing(shared_db):
    s, d = ids(1)
    assert "no_identity" in await code(merge(int(s), int(d)))
    assert "invalid_player_identifier" in await code(q("SELECT public.fab_merge_player_identities(NULL, NULL)"))


async def test_004_already_linked(shared_db):
    pid, _ = await ident(2)
    s, d = ids(2)
    assert (await merge(int(s), int(d))) == {"result": "already_linked", "identity_id": pid}


async def test_004_steam_missing_links_discord_identity(shared_db):
    pid, _ = await ident(3, steam=False)
    s, d = ids(3)
    assert (await merge(int(s), int(d))) == {"result": "linked", "identity_id": pid}
    assert (await row(pid))[0]["steam_id"] == int(s)
    # discord identity with a different steam id: error unless forced
    pid2, _ = await ident(4)
    s4, d4 = ids(4)
    s5, _ = ids(5)
    assert "different_steam" in await code(merge(int(s5), int(d4)))
    assert (await merge(int(s5), int(d4), True))["result"] == "linked"
    assert (await row(pid2))[0]["steam_id"] == int(s5)


async def test_004_discord_missing_links_steam_identity(shared_db):
    pid, _ = await ident(6, discord=False)
    s, d = ids(6)
    assert (await merge(int(s), int(d)))["result"] == "linked"
    assert (await row(pid))[0]["discord_id"] == int(d)
    pid2, _ = await ident(7)
    s7, _ = ids(7)
    _, d8 = ids(8)
    assert "steam_linked_to_other_discord" in await code(merge(int(s7), int(d8)))
    assert (await merge(int(s7), int(d8), True))["result"] == "linked"
    assert (await row(pid2))[0]["discord_id"] == int(d8)


async def test_004_merge_steam_only_into_discord_only(shared_db):
    """Neither has a record: Discord identity survives, steam's alias/details win, accounts keep separate balances."""
    a, _ = await ident(10, discord=False, alias="zz_test_steamname", money=50)
    await q("UPDATE public.identities_player SET details = CAST(:d AS jsonb) WHERE id = :p", d='{"k":1,"n":"a"}', p=a)
    b, _ = await ident(11, steam=False, alias="zz_test_dname", money=7)
    await q("UPDATE public.identities_player SET details = CAST(:d AS jsonb) WHERE id = :p", d='{"n":"b","x":2}', p=b)
    s, _ = ids(10)
    _, d = ids(11)
    res = await merge(int(s), int(d))
    assert res["result"] == "merged" and res["identity_id"] == b and res["accounts_moved"] == 1
    assert res["removed"]["id"] == a and res["removed"]["alias"] == "zz_test_steamname"
    r = (await row(b))[0]
    assert (r["steam_id"], r["discord_id"], r["alias"]) == (int(s), int(d), "zz_test_steamname")
    assert r["details"] == {"k": 1, "n": "a", "x": 2}
    assert await row(a) == []
    assert await accounts(b) == {"Main": 7, f"Main (merged from {a})": 50}


async def test_004_survivor_is_identity_with_record(shared_db):
    # steam side has the record -> steam identity survives
    a, ra = await ident(12, discord=False, rank="EN2", money=5)
    b, _ = await ident(13, steam=False, money=9)
    s, _ = ids(12)
    _, d = ids(13)
    res = await merge(int(s), int(d))
    assert res["identity_id"] == a and res["removed"]["id"] == b
    assert (await row(a))[0]["discord_id"] == int(d)
    assert await accounts(a) == {"Main": 5, f"Main (merged from {b})": 9}
    # discord side has the record -> discord identity survives
    a2, _ = await ident(14, discord=False)
    b2, rb = await ident(15, steam=False, rank="EN1")
    s, _ = ids(14)
    _, d = ids(15)
    res = await merge(int(s), int(d))
    assert res["identity_id"] == b2 and (await row(b2))[0]["steam_id"] == int(s)


async def test_004_both_records_conflict_even_forced(shared_db):
    await ident(16, discord=False, rank="EN1")
    await ident(17, steam=False, rank="EN2")
    s, _ = ids(16)
    _, d = ids(17)
    assert "service_record_conflict" in await code(merge(int(s), int(d)))
    assert "service_record_conflict" in await code(merge(int(s), int(d), True))


async def test_004_guards_and_force(shared_db):
    a, _ = await ident(18, alias="zz_test_old")           # has steam + discord
    b, _ = await ident(19)                                 # has steam + discord
    s18, d18 = ids(18)
    s19, d19 = ids(19)
    assert "steam_linked_to_other_discord" in await code(merge(int(s18), int(d19)))
    c, _ = await ident(20, discord=False)                  # steam only
    s20, _ = ids(20)
    assert "different_steam" in await code(merge(int(s20), int(d19)))
    # force: b survives (neither has a record), takes steam 20 and keeps discord 19; old steam 19 is gone
    res = await merge(int(s20), int(d19), True)
    assert res["identity_id"] == b
    r = (await row(b))[0]
    assert (r["steam_id"], r["discord_id"]) == (int(s20), int(d19))
    # force over an identity that holds both a different discord and steam
    c2, _ = await ident(21)
    s21, d21 = ids(21)
    res = await merge(int(s18), int(d21), True)            # a (steam 18, discord 18) vs c2 (steam 21, discord 21)
    assert res["identity_id"] == c2
    assert (await row(c2))[0]["steam_id"] == int(s18) and (await row(c2))[0]["discord_id"] == int(d21)
    assert await row(a) == []


async def test_004_lost_discord_account(shared_db):
    old, rec = await ident(22, rank="EN3", money=1000)    # steam + old discord + record + money
    _, newd = ids(23)
    new, _ = await ident(23, steam=False)                 # new empty discord-only identity
    s, _ = ids(22)
    res = await merge(int(s), int(newd), True)
    assert res["identity_id"] == old and res["removed"]["id"] == new
    assert (await row(old))[0]["discord_id"] == int(newd)
    assert (await accounts(old))["Main"] == 1000
    assert await q("SELECT player_identity_id FROM military.service_records WHERE id = :r", r=rec) == old


async def test_004_lost_discord_no_new_identity(shared_db):
    old, _ = await ident(24, rank="EN3", money=1000)
    s, _ = ids(24)
    _, newd = ids(25)
    res = await merge(int(s), int(newd), True)
    assert res["result"] == "linked" and res["identity_id"] == old
    assert (await row(old))[0]["discord_id"] == int(newd) and (await accounts(old))["Main"] == 1000


# ---- 005 ----

async def mr(f, t):
    return await q("SELECT public.fab_merge_service_records(:f, :t)", f=f, t=t)


async def pair(n, from_rank="EN1", to_rank="EN2"):
    _, f = await ident(n, discord=False, rank=from_rank)
    _, t = await ident(n + 1, steam=False, rank=to_rank)
    return f, t


async def test_005_errors(shared_db):
    f, t = await pair(30)
    assert "same_record" in await code(mr(f, f))
    assert "record_not_found" in await code(mr(f, 999999999))
    await q("INSERT INTO public.identities_organizations (name) VALUES ('zz_test_org')")
    try:
        pid, _ = await ident(32)
        other = await q("""INSERT INTO military.service_records (player_identity_id, organization_id, current_rank, service_status)
                           VALUES (:p, (SELECT id FROM public.identities_organizations WHERE name = 'zz_test_org'), 'EN0', 'active')
                           RETURNING id""", p=pid)
        assert "different_organization" in await code(mr(f, other))
        await q("DELETE FROM military.service_records WHERE id = :r", r=other)
    finally:
        await q("DELETE FROM economy.accounts WHERE organization_id IN (SELECT id FROM public.identities_organizations WHERE name = 'zz_test_org')")
        await q("DELETE FROM public.identities_organizations WHERE name = 'zz_test_org'")


async def test_005_rank_status_and_events(shared_db):
    f, t = await pair(33)  # steam EN1, discord EN2
    await q("UPDATE military.service_records SET service_status = 'discharged' WHERE id = :r", r=f)
    for r in (f, t):
        await q("INSERT INTO military.service_events (service_record_id, event_type, occured_at) VALUES (:r, 'reprimand', now())", r=r)
    res = await mr(f, t)
    assert res["events_moved"] == 1
    assert res["previous"] == {"current_rank": "EN2", "service_status": "active"}
    assert res["removed"] == {"id": f, "current_rank": "EN1", "service_status": "discharged"}
    cur = await q("SELECT current_rank || '/' || service_status FROM military.service_records WHERE id = :r", r=t)
    assert cur == "EN1/discharged"
    assert await q("SELECT count(*) FROM military.service_records WHERE id = :r", r=f) == 0
    assert await q("SELECT count(*) FROM military.service_events WHERE service_record_id = :r", r=t) == 2


async def test_005_attendance_steam_wins(shared_db):
    f, t = await pair(35)
    s1 = await q("INSERT INTO military.sessions (session_name) VALUES ('zz_test_s1') RETURNING id")
    s2 = await q("INSERT INTO military.sessions (session_name) VALUES ('zz_test_s2') RETURNING id")
    ins = "INSERT INTO military.attendance (service_record_id, session_id, attendance_status) VALUES (:r, :s, :st)"
    await q(ins, r=f, s=s1, st="present")
    await q(ins, r=t, s=s1, st="absent")
    await q(ins, r=f, s=s2, st="present")
    res = await mr(f, t)
    assert (res["attendance_replaced"], res["attendance_moved"]) == (1, 2)
    rows = await (await get_shared_db_manager()).execute_raw_query(
        "SELECT session_id, attendance_status::text AS st FROM military.attendance WHERE service_record_id = :r", {"r": t})
    assert {(r["session_id"], r["st"]) for r in rows} == {(s1, "present"), (s2, "present")}


async def test_005_leave_requests(shared_db):
    f, t = await pair(37)
    ins = """INSERT INTO military.leave_requests (service_record_id, end_date, status, reason)
             VALUES (:r, current_date + 5, 'active', :why)"""
    await q(ins, r=f, why="steam")
    await q(ins, r=t, why="discord")
    res = await mr(f, t)
    assert (res["leave_cancelled"], res["leave_moved"]) == (1, 1)
    rows = await (await get_shared_db_manager()).execute_raw_query(
        "SELECT reason, status FROM military.leave_requests WHERE service_record_id = :r", {"r": t})
    assert {(r["reason"], r["status"]) for r in rows} == {("steam", "active"), ("discord", "cancelled")}
