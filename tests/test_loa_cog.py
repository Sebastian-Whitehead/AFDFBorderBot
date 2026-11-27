from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.asyncio


@pytest.fixture
def env(monkeypatch):
    import afdfbot.commands.LOA as m
    monkeypatch.setattr(m, "LOA_CHANNEL_ID", None)
    monkeypatch.setattr(m, "send_processed_embed", AsyncMock())
    create = AsyncMock(return_value=(False, "submitted"))
    monkeypatch.setattr(m.LOAManager, "create_or_update_loa", create)
    i = MagicMock()
    i.response.defer = AsyncMock(); i.followup.send = AsyncMock()
    i.user.id = 1
    return m, m.LOA(bot=MagicMock()), i, create


async def _loa(m, cog, i, start, end=None):
    await m.LOA.loa_command.callback(cog, i, start, end, None)


async def test_single_date_is_one_day(env):
    m, cog, i, create = env
    await _loa(m, cog, i, "2099-05-04")
    args = create.await_args
    assert args.args[2] == "2099-05-04" and args.kwargs["start_date"] == "2099-05-04"


async def test_start_and_end(env):
    m, cog, i, create = env
    await _loa(m, cog, i, "2099-05-04", "2099-05-10")
    assert create.await_args.args[2] == "2099-05-10" and create.await_args.kwargs["start_date"] == "2099-05-04"


async def test_end_before_start_rejected(env):
    m, cog, i, create = env
    await _loa(m, cog, i, "2099-05-10", "2099-05-04")
    create.assert_not_awaited()
    assert i.followup.send.call_args.kwargs["ephemeral"] is True
