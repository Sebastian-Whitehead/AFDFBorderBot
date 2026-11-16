from unittest.mock import AsyncMock, MagicMock

import pytest

from database.db_manager import get_shared_db_manager
from database.session_functions import create_session, delete_session, get_session_for_delete
from database.user_functions import create_user
from tests.helpers import ids

pytestmark = pytest.mark.asyncio


def _env(monkeypatch, info=("found", {"session_name": "Op", "attendance_count": 0}), confirmed=True, deleted="deleted"):
    import discord.commands.Session as ge
    m = {"info": AsyncMock(return_value=info), "confirm": AsyncMock(return_value=confirmed),
         "delete": AsyncMock(return_value=deleted)}
    monkeypatch.setattr(ge, "get_session_for_delete", m["info"])
    monkeypatch.setattr(ge, "confirm", m["confirm"])
    monkeypatch.setattr(ge, "delete_session_row", m["delete"])
    i = MagicMock()
    i.response.defer = AsyncMock()
    i.followup.send = AsyncMock()
    i.edit_original_message = AsyncMock()
    return ge, i, m


async def _run(ge, i):
    await ge.Session.delete_session.callback(ge.Session(bot=MagicMock()), i, 5)


async def test_role_check_present():
    import discord.commands.Session as ge
    assert ge.Session.delete_session.callback.__commands_checks__


async def test_delete_confirmed(monkeypatch):
    ge, i, m = _env(monkeypatch)
    await _run(ge, i)
    i.response.defer.assert_awaited_once_with(ephemeral=True)
    m["confirm"].assert_awaited_once()
    assert m["confirm"].await_args.args[1] == "delete_session_warning.json"
    assert m["confirm"].await_args.args[2]["{attendance_count}"] == "0"
    m["delete"].assert_awaited_once_with(5)
    assert "deleted" in i.edit_original_message.call_args.kwargs["content"]


async def test_declined_deletes_nothing(monkeypatch):
    ge, i, m = _env(monkeypatch, confirmed=False)
    await _run(ge, i)
    m["delete"].assert_not_awaited()


async def test_attendance_blocks_before_prompt(monkeypatch):
    ge, i, m = _env(monkeypatch, info=("found", {"session_name": "Op", "attendance_count": 3}))
    await _run(ge, i)
    m["confirm"].assert_not_awaited()
    m["delete"].assert_not_awaited()
    assert "3 attendance" in i.followup.send.call_args.args[0]


async def test_not_found_and_errors(monkeypatch):
    ge, i, m = _env(monkeypatch, info=("not_found", None))
    await _run(ge, i)
    assert "No session" in i.followup.send.call_args.args[0]
    ge, i, m = _env(monkeypatch, info=("error", None))
    await _run(ge, i)
    assert "Database error" in i.followup.send.call_args.args[0]
    for status, text in [("blocked", "meanwhile"), ("not_found", "No session"), ("error", "Database error")]:
        ge, i, m = _env(monkeypatch, deleted=status)
        await _run(ge, i)
        assert text in i.edit_original_message.call_args.kwargs["content"]


async def test_db_delete_and_blocked(shared_db):
    s, d = ids(160)
    assert await create_user("zz_test_del", s, d, rank="EN0")
    db = await get_shared_db_manager()
    sid = await create_session("zz_test_del")
    assert (await get_session_for_delete(sid))[1]["attendance_count"] == 0
    assert await delete_session(sid) == "deleted"
    assert await delete_session(sid) == "not_found"
    assert (await get_session_for_delete(sid))[0] == "not_found"
    sid = await create_session("zz_test_del2")
    from database.attendance_functions import submit_attendance
    assert (await submit_attendance(sid, [{"discord_id": d, "status": "present"}], "1"))["saved"] == [d]
    status, row = await get_session_for_delete(sid)
    assert status == "found" and row["attendance_count"] == 1
    assert await delete_session(sid) == "blocked"
    await db.execute_raw_query("DELETE FROM military.attendance WHERE session_id = :s", {"s": sid})
    assert await delete_session(sid) == "deleted"
