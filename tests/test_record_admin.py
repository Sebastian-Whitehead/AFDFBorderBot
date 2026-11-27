import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.helpers import ids

pytestmark = pytest.mark.asyncio


def _env(monkeypatch, **patches):
    import afdfbot.commands.RecordAdmin as ra
    mocks = {}
    for name, ret in patches.items():
        mocks[name] = AsyncMock(return_value=ret)
        monkeypatch.setattr(ra, name, mocks[name])
    i = MagicMock()
    i.response.defer = AsyncMock()
    i.followup.send = AsyncMock()
    i.edit_original_response = AsyncMock()
    return ra, ra.RecordAdmin(bot=MagicMock()), i, mocks


def _text(i):
    return i.followup.send.call_args.args[0]


async def test_edit_event_passes_only_given_fields(monkeypatch):
    ra, cog, i, m = _env(monkeypatch, update_service_event="updated")
    await ra.RecordAdmin.edit_service_event.callback(cog, i, 9, "n", None, "EN3", "2026-11-20 19:00", '{"a": 1}')
    kw = m["update_service_event"].await_args.kwargs
    assert m["update_service_event"].await_args.args == (9,)
    assert kw["notes"] == "n" and kw["status"] is None and kw["rank"] == "EN3" and kw["details"] == '{"a": 1}'
    assert kw["occured_at"].isoformat() == "2026-11-20T19:00:00+00:00"
    assert "notes, rank, occured_at, details" in _text(i)
    i.response.defer.assert_awaited_once_with(ephemeral=True)


async def test_edit_event_bad_input_and_statuses(monkeypatch):
    ra, cog, i, m = _env(monkeypatch, update_service_event="not_found")
    await ra.RecordAdmin.edit_service_event.callback(cog, i, 9, None, None, None, "soon", None)
    assert "Date must look" in _text(i)
    await ra.RecordAdmin.edit_service_event.callback(cog, i, 9, None, None, None, None, "[1]")
    assert "JSON object" in _text(i)
    m["update_service_event"].assert_not_awaited()
    for status, text in [("not_found", "No service event with id 9"), ("no_changes", "Nothing to change"), ("error", "Database error")]:
        m["update_service_event"].return_value = status
        await ra.RecordAdmin.edit_service_event.callback(cog, i, 9, "n", None, None, None, None)
        assert text in _text(i)


async def test_delete_event_confirmed(monkeypatch):
    t = datetime.datetime(2026, 1, 2, 3, 4, tzinfo=datetime.timezone.utc)
    ra, cog, i, m = _env(monkeypatch, get_service_event=("ok", {"event_type": "enlisted", "occured_at": t}),
                         delete_service_event="deleted", confirm=True)
    await ra.RecordAdmin.delete_service_event.callback(cog, i, 4)
    args = m["confirm"].await_args
    assert args.args[1] == "delete_service_event_warning.json"
    assert args.args[2] == {"{event_id}": "4", "{event_type}": "enlisted", "{date}": "2026-01-02 03:04 UTC"}
    m["delete_service_event"].assert_awaited_once_with(4)
    assert "deleted" in i.edit_original_response.call_args.kwargs["content"]


async def test_delete_event_declined_missing_and_error(monkeypatch):
    ra, cog, i, m = _env(monkeypatch, get_service_event=("ok", {"event_type": "enlisted", "occured_at": datetime.datetime(2026, 1, 1)}),
                         delete_service_event="deleted", confirm=False)
    await ra.RecordAdmin.delete_service_event.callback(cog, i, 4)
    m["delete_service_event"].assert_not_awaited()
    m["get_service_event"].return_value = ("not_found", None)
    await ra.RecordAdmin.delete_service_event.callback(cog, i, 4)
    assert "No service event" in _text(i)
    m["get_service_event"].return_value = ("error", None)
    await ra.RecordAdmin.delete_service_event.callback(cog, i, 4)
    assert "Database error" in _text(i)
    m["get_service_event"].return_value = ("ok", {"event_type": "enlisted", "occured_at": datetime.datetime(2026, 1, 1)})
    m["confirm"].return_value = True
    m["delete_service_event"].return_value = "error"
    await ra.RecordAdmin.delete_service_event.callback(cog, i, 4)
    assert "Database error" in i.edit_original_response.call_args.kwargs["content"]


def _member():
    return MagicMock(id=123, mention="<@123>")


async def test_set_rank_success_swaps_roles(monkeypatch):
    ra, cog, i, m = _env(monkeypatch, set_member_rank=("ok", "EN2"), sync_rank_roles=None)
    member = _member()
    await ra.RecordAdmin.set_rank.callback(cog, i, member, "EN4", None)
    args = m["set_member_rank"].await_args.args
    assert args[:2] == ("123", "EN4") and "Rank set to" in args[2]
    m["sync_rank_roles"].assert_awaited_once_with(i.guild, member, "EN2", "EN4")
    assert "set from EN2" in _text(i)
    await ra.RecordAdmin.set_rank.callback(cog, i, member, "EN4", "typo fix")
    assert m["set_member_rank"].await_args.args[2] == "typo fix"


async def test_set_rank_role_failure_keeps_db(monkeypatch):
    ra, cog, i, m = _env(monkeypatch, set_member_rank=("ok", "EN2"))
    monkeypatch.setattr(ra, "sync_rank_roles", AsyncMock(side_effect=RuntimeError("Forbidden")))
    await ra.RecordAdmin.set_rank.callback(cog, i, _member(), "EN4", None)
    assert "could not be updated: Forbidden" in _text(i)


async def test_set_rank_no_record_same_and_error(monkeypatch):
    ra, cog, i, m = _env(monkeypatch, set_member_rank=("no_record", None), sync_rank_roles=None)
    for status, text in [("no_record", "no service record"), ("same_rank", "already"), ("error", "Database error")]:
        m["set_member_rank"].return_value = (status, "EN4")
        await ra.RecordAdmin.set_rank.callback(cog, i, _member(), "EN4", None)
        assert text in _text(i)
    m["sync_rank_roles"].assert_not_awaited()


async def test_edit_member(monkeypatch):
    ra, cog, i, m = _env(monkeypatch, update_member="updated")
    await ra.RecordAdmin.edit_member.callback(cog, i, _member(), " Bob ", "hi")
    m["update_member"].assert_awaited_once_with("123", "Bob", "hi")
    assert "name, notes" in _text(i)
    m["update_member"].reset_mock()
    await ra.RecordAdmin.edit_member.callback(cog, i, _member(), "  ", None)
    assert "blank" in _text(i)
    m["update_member"].assert_not_awaited()
    for status, text in [("no_changes", "Nothing to change"), ("no_identity", "no player record"), ("error", "Database error")]:
        m["update_member"].return_value = status
        await ra.RecordAdmin.edit_member.callback(cog, i, _member(), None, None)
        assert text in _text(i)


# --- DB functions against the shadow DB ---

async def _event_ids(d):
    from database import get_service_events
    return [e["id"] for e in await get_service_events(d, 20)]


async def test_db_event_edit_delete(shared_db):
    from database import create_user
    from database.record_functions import get_service_event, update_service_event, delete_service_event
    s, d = ids(120)
    assert await create_user("zz_test_ev", s, d, "EN2", enlisted=True)
    [eid] = await _event_ids(d)
    when = datetime.datetime(2026, 5, 6, 7, 8, tzinfo=datetime.timezone.utc)
    assert await update_service_event(eid, notes="n", rank="EN4", status=None, occured_at=when, details='{"k": 1}') == "updated"
    status, ev = await get_service_event(eid)
    assert status == "ok" and ev["event_type"] == "enlisted" and ev["rank"] == "EN4" and ev["occured_at"] == when
    assert await update_service_event(eid) == "no_changes"
    assert await update_service_event(eid, event_type="discharged") == "error"  # event_type is not editable
    assert await update_service_event(eid, rank="XX") == "error"  # check constraint
    assert await update_service_event(eid + 100000, notes="x") == "not_found"
    assert await get_service_event(eid + 100000) == ("not_found", None)
    assert await delete_service_event(eid) == "deleted"
    assert await delete_service_event(eid) == "not_found"


async def test_db_set_member_rank(shared_db):
    from database import create_user, get_user_info
    from database.record_functions import set_member_rank
    s, d = ids(121)
    assert await set_member_rank(d, "EN4") == ("no_record", None)
    assert await create_user("zz_test_rk", s, d, "EN5", enlisted=True)
    assert await set_member_rank(d, "EN5") == ("same_rank", "EN5")
    assert await set_member_rank(d, "XX") == ("error", None)
    assert await set_member_rank(d, "EN2", "fix") == ("ok", "EN5")  # a demotion: no ordering rules
    assert (await get_user_info(d))["rank"] == "EN2"
    from database import get_service_events
    top = (await get_service_events(d, 1))[0]
    assert top["event_type"] == "rank_changed" and top["rank"] == "EN2" and top["notes"] == "fix"


async def test_db_update_member(shared_db):
    from database import ensure_player_identity, get_user_info
    from database.record_functions import update_member
    s, d = ids(122)
    assert await update_member(d, "zz_test_x") == "no_identity"
    assert await ensure_player_identity("zz_test_old", s, d)
    assert await update_member(d) == "no_changes"
    assert await update_member(d, notes="hello") == "updated"
    assert await update_member(d, name="zz_test_new") == "updated"
    from database.db_manager import get_shared_db_manager
    db = await get_shared_db_manager()
    row = (await db.execute_raw_query("SELECT alias, details->>'notes' AS notes FROM public.identities_player WHERE discord_id = :d", {"d": int(d)}))[0]
    assert row["alias"] == "zz_test_new" and row["notes"] == "hello"
