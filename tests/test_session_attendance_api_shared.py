"""fab_create_session / fab_log_attendance (006) on the shadow DB."""
import pytest

from database.db_manager import get_shared_db_manager
from tests.helpers import ids
from tests.test_merge_sql_shared import code, ident, q

pytestmark = pytest.mark.asyncio


async def statuses(sid):
    rows = await (await get_shared_db_manager()).execute_raw_query(
        "SELECT p.alias, a.attendance_status::text AS st, a.notes FROM military.attendance a "
        "JOIN military.service_records sr ON sr.id = a.service_record_id "
        "JOIN public.identities_player p ON p.id = sr.player_identity_id WHERE a.session_id = :s", {"s": sid})
    return {r["alias"]: (r["st"], r["notes"]) for r in rows}


async def test_create_session(shared_db):
    sid = (await q("SELECT public.fab_create_session('zz_test_api', 'B', 'op')"))["session_id"]
    row = (await (await get_shared_db_manager()).execute_raw_query(
        "SELECT timeline, operation FROM military.sessions WHERE id = :i", {"i": sid}))[0]
    assert (row["timeline"], row["operation"]) == ("B", "op")
    assert "name_required" in await code(q("SELECT public.fab_create_session('  ')"))


async def test_log_attendance(shared_db):
    _, here = await ident(41, rank="EN1")
    _, loa = await ident(42, rank="EN1")
    _, gone = await ident(43, rank="EN1")
    _, both = await ident(44, rank="EN1")      # in the list AND on LOA -> present, LOA noted
    _, out = await ident(45, rank="EN1")       # discharged -> ignored
    await q("UPDATE military.service_records SET service_status = 'discharged' WHERE id = :r", r=out)
    for r in (loa, both):
        await q("INSERT INTO military.leave_requests (service_record_id, end_date, reason) VALUES (:r, current_date + 3, 'trip')", r=r)
    sid = (await q("SELECT public.fab_create_session('zz_test_log')"))["session_id"]
    nobody = int(ids(46)[0])  # steam id with no service record
    res = await q("SELECT public.fab_log_attendance(:s, :l)", s=sid,
                  l=[int(ids(n)[0]) for n in (41, 44, 45)] + [nobody])
    assert (res["present"], res["on_leave"], res["absent"]) == (2, 1, 1)
    assert res["unknown_steam_ids"] == sorted([int(ids(45)[0]), nobody])
    got = await statuses(sid)
    assert got["zz_test_41"] == ("present", None)
    assert got["zz_test_42"] == ("on_leave", "LOA until " + str(await q("SELECT current_date + 3")) + ": trip")
    assert got["zz_test_43"] == ("absent", None)
    assert got["zz_test_44"][0] == "present" and got["zz_test_44"][1].startswith("LOA until")
    assert "zz_test_45" not in got
    # re-run: last call wins, no duplicate rows
    res = await q("SELECT public.fab_log_attendance(:s, :l)", s=sid, l=[int(ids(43)[0])])
    assert (res["present"], res["on_leave"], res["absent"]) == (1, 2, 1)
    assert (await statuses(sid))["zz_test_41"][0] == "absent"
    assert await q("SELECT count(*) FROM military.attendance WHERE session_id = :s", s=sid) == 4


async def test_log_attendance_errors(shared_db):
    assert "session_not_found" in await code(q("SELECT public.fab_log_attendance(-1, ARRAY[1]::bigint[])"))
