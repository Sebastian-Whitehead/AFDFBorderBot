from afdfbot.listeners.OfficeHoursMonitor import in_office_hours


def test_in_office_hours():
    assert in_office_hours(9, 9, 17) and in_office_hours(16, 9, 17)
    assert not in_office_hours(17, 9, 17) and not in_office_hours(3, 9, 17)
    # wraps past midnight
    assert in_office_hours(23, 22, 6) and in_office_hours(2, 22, 6) and not in_office_hours(12, 22, 6)


async def test_loop_posts_and_removes_warning(monkeypatch):
    from unittest.mock import AsyncMock, MagicMock
    import afdfbot.listeners.OfficeHoursMonitor as m

    sent = MagicMock(delete=AsyncMock(), id=1)
    channel = MagicMock(send=AsyncMock(), fetch_message=AsyncMock())
    channel.history = lambda limit: _aiter([])
    bot = MagicMock()
    bot.get_guild.return_value.get_channel.return_value = channel
    monkeypatch.setattr(m, "TESTING_GUILD_ID", 1)
    monkeypatch.setattr(m, "CHECKPOINT_CHANNEL_ID", 2)
    monkeypatch.setattr(m, "send_processed_embed", AsyncMock(return_value=sent))
    state = {"office-hours-enabled": True, "office-hours-start": 9, "office-hours-end": 17}
    monkeypatch.setattr(m, "get_setting", lambda k, d=None: state.get(k, d))
    cog = m.OfficeHoursMonitor.__new__(m.OfficeHoursMonitor)
    cog.bot, cog.msg = bot, None

    class Clock:  # fixed UTC hour
        hour = 3
    monkeypatch.setattr(m, "datetime", MagicMock(now=lambda tz: Clock))
    await m.OfficeHoursMonitor.check_office_hours.coro(cog)   # closed -> posts
    assert cog.msg is sent
    await m.OfficeHoursMonitor.check_office_hours.coro(cog)   # still closed -> no second post
    assert m.send_processed_embed.await_count == 1
    Clock.hour = 10
    await m.OfficeHoursMonitor.check_office_hours.coro(cog)   # open -> deletes
    sent.delete.assert_awaited_once()
    assert cog.msg is None


async def _aiter(items):
    for i in items:
        yield i
