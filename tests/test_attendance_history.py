import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from database.attendance_functions import get_attendance_history, submit_attendance
from database.db_manager import get_shared_db_manager
from database.user_functions import create_user
from tests.helpers import ids

pytestmark = pytest.mark.asyncio

NAMES = ["Op A", "Op B", "Op C"]


@pytest_asyncio.fixture
async def hist_db(shared_db):
    """Three sessions (oldest first) + cleanup of attendance/sessions that cleanup_shared does not know."""
    db = await get_shared_db_manager()
    sids = []
    for n, name in enumerate(NAMES):
        await db.execute_raw_query(
            "INSERT INTO military.sessions (session_name, start_at) VALUES (:n, :t)",
            {"n": "zz_test_hist_" + name, "t": datetime.datetime(2030, 1, 1 + n, 12, tzinfo=datetime.timezone.utc)})
    rows = await db.execute_raw_query(
        "SELECT id FROM military.sessions WHERE session_name LIKE 'zz_test_hist_%' ORDER BY start_at")
    sids = [r["id"] for r in rows]
    yield sids
    await db.execute_raw_query(
        "DELETE FROM military.attendance WHERE session_id IN (SELECT id FROM military.sessions WHERE session_name LIKE 'zz_test_hist_%')")
    await db.execute_raw_query("DELETE FROM military.sessions WHERE session_name LIKE 'zz_test_hist_%'")


async def test_history_counts_order_limit(hist_db):
    s, d = ids(140)
    assert await create_user("zz_test_h", s, d)
    for sid, st, note in zip(hist_db, ["present", "absent", "present"], [None, "late", None]):
        await submit_attendance(sid, [{"discord_id": d, "status": st, "notes": note}], "1")
    h = await get_attendance_history(d, 2)
    assert h["has_record"] and h["counts"] == {"present": 2, "absent": 1}
    assert [r["session_name"] for r in h["recent"]] == ["zz_test_hist_Op C", "zz_test_hist_Op B"]  # newest first, limited
    assert h["recent"][1]["status"] == "absent" and h["recent"][1]["notes"] == "late"


async def test_history_member_without_attendance_and_unknown(hist_db):
    s, d = ids(141)
    assert await create_user("zz_test_h", s, d)
    assert await get_attendance_history(d, 5) == {"has_record": True, "counts": {}, "recent": []}
    assert await get_attendance_history(ids(142)[1], 5) == {"has_record": False, "counts": {}, "recent": []}


# --- cog (mocked) ---

def _i():
    i = MagicMock()
    i.response.defer = AsyncMock()
    i.followup.send = AsyncMock()
    return i


@pytest.fixture
def env(monkeypatch):
    import afdfbot.commands.Attendance as am
    hist = {"has_record": True, "counts": {"present": 3, "absent": 1},
            "recent": [{"session_name": "Op", "start_at": datetime.datetime(2030, 1, 2, 23, tzinfo=datetime.timezone.utc),
                        "status": "absent", "notes": "late"}]}
    monkeypatch.setattr(am, "get_attendance_history", AsyncMock(return_value=hist))
    return am, am.Attendance(bot=MagicMock())


def _user():
    return MagicMock(id=7, mention="<@7>", display_name="Bob")


async def test_cog_has_role_check():
    import afdfbot.commands.Attendance as am
    assert am.Attendance.attendance_history.checks


async def test_cog_embed(env):
    am, cog = env
    i = _i()
    await am.Attendance.attendance_history.callback(cog, i, _user(), 10)
    i.response.defer.assert_awaited_with(ephemeral=True)
    am.get_attendance_history.assert_awaited_with("7", 10)
    d = i.followup.send.call_args.kwargs["embed"].description
    assert "present 3 · absent 1" in d and "75%" in d and "2030-01-02 · absent · late" in d


@pytest.mark.parametrize("ret,msg", [
    (None, "Database error"),
    ({"has_record": False, "counts": {}, "recent": []}, "no service record"),
    ({"has_record": True, "counts": {}, "recent": []}, "No attendance recorded"),
])
async def test_cog_messages(env, ret, msg):
    am, cog = env
    am.get_attendance_history.return_value = ret
    i = _i()
    await am.Attendance.attendance_history.callback(cog, i, _user(), 10)
    assert msg in i.followup.send.call_args.args[0]
