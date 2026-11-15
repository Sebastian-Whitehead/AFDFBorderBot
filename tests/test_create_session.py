from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.asyncio


def _env(monkeypatch, result=7):
    import discord.commands.GuildEvent as ge
    create = AsyncMock(return_value=result)
    monkeypatch.setattr(ge, "create_session_row", create)
    i = MagicMock()
    i.response.defer = AsyncMock()
    i.followup.send = AsyncMock()
    return ge, ge.GuildEvent(bot=MagicMock()), i, create


async def _run(ge, cog, i, name="Op Night", start=None, ext=None, timeline="A"):
    await ge.GuildEvent.create_session.callback(cog, i, name, None, None, start, ext, timeline)


async def test_creates_with_defaults(monkeypatch):
    ge, cog, i, create = _env(monkeypatch)
    await _run(ge, cog, i)
    create.assert_awaited_once_with("Op Night", None, None, None, None, "A")
    assert "id 7" in i.followup.send.call_args.args[0]


async def test_external_id_and_start_passed(monkeypatch):
    ge, cog, i, create = _env(monkeypatch)
    await _run(ge, cog, i, start="2026-11-20 19:00", ext="123")
    args = create.await_args.args
    assert args[3].isoformat() == "2026-11-20T19:00:00+00:00" and args[4] == "123"


async def test_timeline_passed(monkeypatch):
    ge, cog, i, create = _env(monkeypatch)
    await _run(ge, cog, i, timeline="B")
    assert create.await_args.args[5] == "B"


async def test_bad_start_and_blank_name_rejected(monkeypatch):
    ge, cog, i, create = _env(monkeypatch)
    await _run(ge, cog, i, start="tomorrow")
    await _run(ge, cog, i, name="  ")
    create.assert_not_awaited()


async def test_end_session_messages(monkeypatch):
    import datetime
    import discord.commands.GuildEvent as ge
    t = datetime.datetime(2026, 11, 20, 21, 0, tzinfo=datetime.timezone.utc)
    row = {"id": 3, "session_name": "Op", "start_at": t, "end_at": t}
    monkeypatch.setattr(ge, "confirm", AsyncMock(return_value=True))
    for status, row_, text in [("ended", row, "ended at"), ("none_open", None, "No open"),
                               ("before_start", row, "before"), ("error", None, "Database error")]:
        monkeypatch.setattr(ge, "end_latest_session", AsyncMock(return_value=(status, row_)))
        i = MagicMock()
        i.response.defer = AsyncMock()
        i.followup.send = AsyncMock()
        i.edit_original_message = AsyncMock()
        await ge.GuildEvent.end_session.callback(ge.GuildEvent(bot=MagicMock()), i, None)
        assert text in i.edit_original_message.call_args.kwargs["content"]


async def test_end_session_not_confirmed(monkeypatch):
    import discord.commands.GuildEvent as ge
    monkeypatch.setattr(ge, "confirm", AsyncMock(return_value=False))
    end = AsyncMock()
    monkeypatch.setattr(ge, "end_latest_session", end)
    i = MagicMock()
    i.response.defer = AsyncMock()
    i.followup.send = AsyncMock()
    i.edit_original_message = AsyncMock()
    await ge.GuildEvent.end_session.callback(ge.GuildEvent(bot=MagicMock()), i, None)
    end.assert_not_awaited()


async def test_db_error(monkeypatch):
    ge, cog, i, create = _env(monkeypatch, result=None)
    await _run(ge, cog, i)
    assert "Database error" in i.followup.send.call_args.args[0]


async def test_session_list_table_and_paging(monkeypatch):
    import datetime
    import discord.commands.GuildEvent as ge
    t = datetime.datetime(2026, 11, 20, 19, 0, tzinfo=datetime.timezone.utc)
    rows = [{"id": 4, "timeline": "A", "session_name": "Op Night", "operation": None, "start_at": t, "end_at": None}]
    lister = AsyncMock(return_value=(rows, 11))
    monkeypatch.setattr(ge, "list_sessions", lister)
    i = MagicMock()
    i.response.defer = AsyncMock()
    i.followup.send = AsyncMock()
    await ge.GuildEvent.session_list.callback(ge.GuildEvent(bot=MagicMock()), i, "A", 2)
    lister.assert_awaited_once_with("A", 2)
    emb = i.followup.send.call_args.kwargs["embeds"][0]
    assert "Page 2/2" in emb.footer.text and "11 total" in emb.footer.text and "A" in emb.title
    assert "| 11 | 4  | A" in emb.description and "Op Night" in emb.description and "open" in emb.description
    lister.return_value = ([], 11)
    await ge.GuildEvent.session_list.callback(ge.GuildEvent(bot=MagicMock()), i, "A", 9)
    assert "No sessions on page 9" in i.followup.send.call_args.args[0]
    lister.return_value = None
    await ge.GuildEvent.session_list.callback(ge.GuildEvent(bot=MagicMock()), i, "A", 1)
    assert "Database error" in i.followup.send.call_args.args[0]


async def test_edit_session(monkeypatch):
    import discord.commands.GuildEvent as ge
    upd = AsyncMock(return_value=("updated", {"session_name": "New"}))
    monkeypatch.setattr(ge, "update_session", upd)

    async def run(*args):
        i = MagicMock()
        i.response.defer = AsyncMock()
        i.followup.send = AsyncMock()
        await ge.GuildEvent.edit_session.callback(ge.GuildEvent(bot=MagicMock()), i, *args)
        return i.followup.send.call_args.args[0]

    # session_id, name, operation, description, timeline, start, end
    out = await run(4, " New ", None, None, "b", None, "2026-11-20 21:00")
    kw = upd.await_args.kwargs
    assert upd.await_args.args == (4,) and kw["session_name"] == "New" and kw["timeline"] == "b"
    assert kw["end_at"].isoformat() == "2026-11-20T21:00:00+00:00" and kw["operation"] is None and "start_at" not in kw
    assert "updated: session_name, timeline, end_at" in out
    upd.reset_mock()
    assert "blank" in await run(4, "  ", None, None, None, None, None)
    assert "must look like" in await run(4, None, None, None, None, "soon", None)
    upd.assert_not_awaited()
    for status, text in [("no_changes", "Nothing to change"), ("not_found", "No session"),
                         ("bad_dates", "before the start"), ("error", "Database error")]:
        upd.return_value = (status, None)
        assert text in await run(4, None, None, None, None, None, None)
