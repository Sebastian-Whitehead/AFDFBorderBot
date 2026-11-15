import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.asyncio

LOA = {"discord_id": "3", "end_date": "2999-01-01", "reason": "trip", "start_date": datetime.date(2000, 1, 1)}


def _i(members=()):
    i = MagicMock()
    i.user.id = 99
    i.user.voice.channel.members = [MagicMock(id=m, bot=False) for m in members]
    i.response.defer = AsyncMock()
    i.followup.send = AsyncMock()
    i.edit_original_message = AsyncMock()
    return i


def _user(uid):
    return MagicMock(id=uid, mention=f"<@{uid}>")


@pytest.fixture
def env(monkeypatch):
    import discord.commands.Attendance as am
    monkeypatch.setattr(am.LOAManager, "get_all_active_loas", AsyncMock(return_value=[LOA]))
    monkeypatch.setattr(am, "get_open_session", AsyncMock(return_value={"id": 5, "session_name": "Op"}))
    monkeypatch.setattr(am, "find_unaccounted", AsyncMock(return_value=[]))
    monkeypatch.setattr(am, "submit_attendance", AsyncMock(return_value={"saved": ["1"], "skipped": []}))
    return am, am.Attendance(bot=MagicMock())


async def test_start_adds_vc_members_and_loa(env):
    am, cog = env
    await am.Attendance.start_attendance.callback(cog, _i([1, 3]))
    e = cog.active["entries"]
    assert e["1"]["status"] == "present" and e["1"]["loa"] is None
    assert e["3"]["status"] == "present" and e["3"]["loa"] is LOA  # in VC: stays present, LOA noted


async def test_start_puts_absent_loa_member_on_leave(env):
    am, cog = env
    await am.Attendance.start_attendance.callback(cog, _i([1]))
    assert cog.active["entries"]["3"]["status"] == "on_leave"


async def test_start_needs_voice_and_no_active_list(env):
    am, cog = env
    i = _i()
    i.user.voice = None
    await am.Attendance.start_attendance.callback(cog, i)
    assert cog.active is None and "voice" in i.followup.send.call_args.args[0]
    await am.Attendance.start_attendance.callback(cog, _i([1]))
    i = _i([2])
    await am.Attendance.start_attendance.callback(cog, i)
    assert "already active" in i.followup.send.call_args.args[0] and "2" not in cog.active["entries"]


async def test_start_needs_open_session(env):
    am, cog = env
    am.get_open_session.return_value = None
    i = _i([1])
    await am.Attendance.start_attendance.callback(cog, i)
    assert cog.active is None and "No open session" in i.followup.send.call_args.args[0]


async def test_add_remove_discard(env):
    am, cog = env
    await am.Attendance.add_attendance.callback(cog, _i(), _user(7), "present")
    assert cog.active is None
    await am.Attendance.start_attendance.callback(cog, _i([1]))
    await am.Attendance.add_attendance.callback(cog, _i(), _user(7), "excused")
    assert cog.active["entries"]["7"]["status"] == "excused"
    await am.Attendance.remove_attendance.callback(cog, _i(), _user(7))
    assert "7" not in cog.active["entries"]
    i = _i()
    await am.Attendance.remove_attendance.callback(cog, i, _user(7))
    assert "not on the list" in i.followup.send.call_args.args[0]
    await am.Attendance.discard_attendance.callback(cog, _i())
    assert cog.active is None


async def test_submit_direct(env):
    am, cog = env
    await am.Attendance.start_attendance.callback(cog, _i([1]))
    i = _i()
    await am.Attendance.submit_attendance.callback(cog, i)
    sid, rows, by = am.submit_attendance.await_args.args
    assert sid == 5 and by == "99" and {r["discord_id"]: r["status"] for r in rows} == {"1": "present", "3": "on_leave"}
    assert cog.active is None and "saved" in i.edit_original_message.call_args.kwargs["content"]


@pytest.mark.parametrize("saved", [True, False])
async def test_submit_unaccounted_prompt(env, monkeypatch, saved):
    am, cog = env
    am.find_unaccounted.return_value = ["8"]
    ask = AsyncMock(return_value=saved)
    monkeypatch.setattr(am, "confirm", ask)
    await am.Attendance.start_attendance.callback(cog, _i([1]))
    i = _i()
    await am.Attendance.submit_attendance.callback(cog, i)
    assert ask.await_args.args[1] == "attendance_absent_warning.json" and "- <@8>" in ask.await_args.args[2]["{absent_list}"]
    assert am.submit_attendance.await_count == (1 if saved else 0)
    assert (cog.active is None) == saved
    if saved:
        assert {"discord_id": "8", "status": "absent", "notes": None} in am.submit_attendance.await_args.args[1]


async def test_submit_without_list_or_session(env):
    am, cog = env
    i = _i()
    await am.Attendance.submit_attendance.callback(cog, i)
    assert "No active" in i.followup.send.call_args.args[0]
    await am.Attendance.start_attendance.callback(cog, _i([1]))
    am.get_open_session.return_value = None
    await am.Attendance.submit_attendance.callback(cog, i)
    assert "No open session" in i.followup.send.call_args.args[0] and cog.active


async def test_modify_loads_saved_attendance_and_submits_to_that_session(env, monkeypatch):
    am, cog = env
    monkeypatch.setattr(am, "load_session_attendance", AsyncMock(return_value=(
        {"id": 12, "session_name": "Old Op"}, [{"discord_id": "1", "status": "absent", "notes": "late"}])))
    i = _i()
    await am.Attendance.modify_attendance.callback(cog, i, 12)
    assert cog.active["entries"]["1"]["status"] == "absent" and "Old Op" in i.followup.send.call_args.args[0]
    await am.Attendance.add_attendance.callback(cog, _i(), _user(2), "present")
    am.get_open_session.return_value = None  # must not matter: the session is already chosen
    await am.Attendance.submit_attendance.callback(cog, _i())
    sid, rows, _ = am.submit_attendance.await_args.args
    assert sid == 12 and {r["discord_id"]: (r["status"], r["notes"]) for r in rows} == {"1": ("absent", "late"), "2": ("present", None)}


async def test_modify_errors(env, monkeypatch):
    am, cog = env
    load = AsyncMock(return_value=(None, []))
    monkeypatch.setattr(am, "load_session_attendance", load)
    i = _i()
    await am.Attendance.modify_attendance.callback(cog, i, 99)
    assert "No session with id 99" in i.followup.send.call_args.args[0] and cog.active is None
    load.return_value = None
    await am.Attendance.modify_attendance.callback(cog, i, 99)
    assert "Database error" in i.followup.send.call_args.args[0]
    await am.Attendance.start_attendance.callback(cog, _i([1]))
    await am.Attendance.modify_attendance.callback(cog, i, 99)
    assert "already active" in i.followup.send.call_args.args[0]


async def test_view_attendance(env):
    am, cog = env
    i = _i()
    await am.Attendance.view_attendance.callback(cog, i)
    assert "No active" in i.followup.send.call_args.args[0]
    await am.Attendance.start_attendance.callback(cog, _i([1]))
    await am.Attendance.view_attendance.callback(cog, i)
    assert "<@1> — present" in i.followup.send.call_args.args[0]
    assert cog.active is not None  # viewing doesn't change anything
