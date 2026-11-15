import asyncio
import contextlib
import inspect
import io
import os
import re
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from database.db_manager import get_db_manager, get_shared_db_manager
from database.user_functions import get_user_info
from tests.helpers import ids

pytestmark = pytest.mark.asyncio

SCRIPT = Path(__file__).resolve().parent.parent / "migration" / "migrate_to_supabase.py"
A, B, C, D, E, OTHER = 40, 41, 42, 43, 44, 45
NAMES = {A: "zz_test_a", B: "zz_test_b", C: "zz_test_c", D: "zz_test_game", E: "zz_test_e"}
COUNT_TABLES = ("public.identities_player", "military.service_records",
                "military.service_events", "military.leave_requests")


def _run(argv):
    """Call main(argv) (sync or async) off the test loop; return (exit_code, stdout)."""
    from migration.migrate_to_supabase import main
    buf, code = io.StringIO(), 0
    with contextlib.redirect_stdout(buf):
        try:
            r = main(argv)
            if inspect.iscoroutine(r):
                r = asyncio.run(r)
            code = r or 0
        except SystemExit as e:
            code = e.code or 0
    return code, buf.getvalue()


async def _migrate(*extra, target=None):
    argv = ["--source-url", os.getenv("TEST_LOCAL_DATABASE_URL", "postgresql+asyncpg://x@localhost/x"),
            "--target-url", target or os.environ["TEST_SHARED_DATABASE_URL"], *extra]
    return await asyncio.to_thread(_run, argv)


def _n(report, label):
    """First count next to `label` ('created 2' or '2 created'); report format is under-specified."""
    m = re.search(rf"{label}\D{{0,20}}?(\d+)", report, re.I) or re.search(rf"(\d+)\s+{label}", report, re.I)
    assert m, f"no '{label}' count in report:\n{report}"
    return int(m.group(1))


async def _seed():
    """Local rows A-E + LOA1-5; shadow pre-state for D and E."""
    loc, shared = await get_db_manager(), await get_shared_db_manager()
    u = ("INSERT INTO users (name, steam_id, discord_id, enlisted_at, money, rank, notes, achievements, "
         "last_death, deaths, reprimands) VALUES (:n, :s, :d, :e, :m, :r, :notes, CAST(:ach AS text[]), "
         ":ld, :deaths, CAST(:rep AS jsonb))")
    base = dict(e=None, m=0, r=0, notes=None, ach=None, ld=None, deaths=0, rep=None)
    rows = {
        A: dict(base, s=ids(A)[0], d=ids(A)[1]),
        B: dict(base, s=ids(B)[0], d=ids(B)[1], e=datetime(2025, 3, 1, 12, 0), m=123.60, r=10, notes="n",
                ach=["x", "y"], ld=date(2025, 6, 1), deaths=2, rep='[{"r": 1}]'),
        C: dict(base, s="STEAM_0:1:1", d=ids(C)[1]),
        D: dict(base, s=ids(D)[0], d=ids(D)[1]),
        E: dict(base, s=ids(E)[0], d=ids(E)[1]),
    }
    for k, row in rows.items():
        await loc.execute_dml_query(u, dict(row, n=NAMES[k]))
    # LOA owners: A (LOA1, LOA4), B (LOA2), C (LOA3, skipped at parse, before the record lookup), D (LOA5)
    loa = ("INSERT INTO loa_requests (discord_id, username, start_date, end_date, reason, status) "
           "VALUES (:d, :u, :s, :e, 'r', :st)")
    for k, s, e, st in ((A, date(2025, 1, 1), "2030-01-31", "active"),
                        (B, date(2025, 1, 1), "01/31/2030", "active"),
                        (C, date(2025, 1, 1), "next week", "active"),
                        (A, date(2025, 1, 1), "2030-02-28", "cancelled"),
                        (D, date(1999, 12, 1), "2000-01-01", "active")):
        await loc.execute_dml_query(loa, {"d": ids(k)[1], "u": NAMES[k], "s": s, "e": e, "st": st})
    await shared.execute_raw_query("SELECT public.fab_ensure_player_account('zz_test_game', :s, NULL)",
                                   {"s": int(ids(D)[0])})
    await shared.execute_raw_query("SELECT public.fab_ensure_player_account('zz_test_other', :s, :d)",
                                   {"s": int(ids(OTHER)[0]), "d": int(ids(E)[1])})


async def _counts(tables=COUNT_TABLES):
    db = await get_shared_db_manager()
    return {t: (await db.execute_raw_query(f"SELECT count(*) AS c FROM {t}"))[0]["c"] for t in tables}


async def _loas(n):
    db = await get_shared_db_manager()
    return await db.execute_raw_query(
        "SELECT lr.status, lr.end_date FROM military.leave_requests lr "
        "JOIN military.service_records sr ON sr.id = lr.service_record_id "
        "JOIN public.identities_player p ON p.id = sr.player_identity_id WHERE p.discord_id = :d "
        "ORDER BY lr.id", {"d": int(ids(n)[1])})


def _utc(dt):
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def _check_m1(report):
    assert _n(report, "created") == 2
    assert _n(report, "adopted") == 1
    assert _n(report, "skipped") >= 2
    assert "non-numeric steam_id" in report
    assert "discord_id used by identity" in report


async def test_m1_report(local_db, shared_db):
    await _seed()
    code, out = await _migrate()
    assert code == 0, out
    _check_m1(out)
    other = (await (await get_shared_db_manager()).execute_raw_query(
        "SELECT id FROM public.identities_player WHERE steam_id = :s", {"s": int(ids(OTHER)[0])}))[0]["id"]
    assert f"discord_id used by identity {other}" in out


async def test_m2_parity_and_m3_adopt(local_db, shared_db):
    await _seed()
    await _migrate()
    loc = await get_db_manager()
    for k in (A, B, D):
        row = (await loc.execute_raw_query("SELECT * FROM users WHERE steam_id = :s", {"s": ids(k)[0]}))[0]
        got = await get_user_info(ids(k)[1])
        assert got, k
        assert got["name"] == row["name"] and got["steam_id"] == row["steam_id"]
        assert got["discord_id"] == row["discord_id"] and got["rank"] == row["rank"]
        assert got["enlisted"] == (row["enlisted_at"] is not None)
        assert got["notes"] == row["notes"]
        assert (got["achievements"] or None) == (list(row["achievements"]) if row["achievements"] else None)
        assert (got["deaths"] or 0) == (row["deaths"] or 0) and got["last_death"] == row["last_death"]
        if row["enlisted_at"]:
            assert _utc(got["enlisted_at"]) == _utc(row["enlisted_at"])
    db = await get_shared_db_manager()
    rows = await db.execute_raw_query("SELECT discord_id FROM public.identities_player WHERE steam_id = :s",
                                      {"s": int(ids(D)[0])})
    assert len(rows) == 1 and str(rows[0]["discord_id"]) == ids(D)[1]  # M3


async def test_m4_no_money(local_db, shared_db):
    await _seed()
    t = ("economy.transactions", "economy.transactions_entries")
    before = await _counts(t)
    await _migrate()
    assert await _counts(t) == before
    src = SCRIPT.read_text(encoding="utf-8")
    assert "economy." not in src and "post_economy" not in src


async def test_m5_loas(local_db, shared_db):
    await _seed()
    code, out = await _migrate()
    assert code == 0, out
    for k in (A, B):  # LOA1, LOA2 (A's cancelled LOA4 must not appear: exactly one row)
        r = await _loas(k)
        assert [(x["status"], x["end_date"]) for x in r] == [("active", date(2030, 1, 31))], k
    r = await _loas(D)
    assert len(r) == 1 and r[0]["status"] == "expired"
    assert "unparseable end_date 'next week'" in out
    assert await _loas(C) == []


async def test_m6_idempotent(local_db, shared_db):
    await _seed()
    await _migrate()
    before = await _counts()
    code, out = await _migrate()
    assert code == 0, out
    assert await _counts() == before


async def test_m7_dry_run(local_db, shared_db):
    await _seed()
    before = await _counts()
    code, out = await _migrate("--dry-run")
    assert code == 0, out
    _check_m1(out)
    assert "DRY RUN" in out
    assert await _counts() == before
    db = await get_shared_db_manager()
    assert await db.execute_raw_query(
        "SELECT 1 FROM public.identities_player WHERE steam_id IN (:a, :b)",
        {"a": int(ids(A)[0]), "b": int(ids(B)[0])}) == []


async def test_m8_remote_refused():
    code, out = await _migrate(target="postgresql+asyncpg://u:p@db.example.com:5432/postgres")
    assert code == 2, out
