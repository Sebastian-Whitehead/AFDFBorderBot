from unittest.mock import AsyncMock, MagicMock

import nextcord
import pytest

pytestmark = pytest.mark.asyncio


@pytest.fixture
def env(monkeypatch):
    import discord.listeners.JoinLeaveHandler as m
    monkeypatch.setattr(m, "JOIN_ROLE_ID", 111)
    monkeypatch.setattr(m, "WELCOME_CHANNEL_ID", 222)
    monkeypatch.setattr(m, "get_setting", lambda k, d=None: True)
    sent = AsyncMock()
    monkeypatch.setattr(m, "send_processed_embed", sent)
    member = MagicMock(id=5, mention="<@5>", display_name="bob")
    member.add_roles = AsyncMock()
    member.guild.get_role.return_value = MagicMock()
    member.guild.get_channel.return_value = MagicMock()
    return m, m.JoinLeaveHandler(bot=MagicMock()), member, sent


async def test_join_adds_role_and_welcomes(env):
    m, cog, member, sent = env
    await cog.on_member_join(member)
    member.add_roles.assert_awaited_once()
    assert sent.await_args.args[1] == "member_join.json"


async def test_join_welcome_still_sent_if_role_fails(env):
    m, cog, member, sent = env
    member.add_roles.side_effect = nextcord.Forbidden(MagicMock(status=403, reason="x"), "missing perms")
    await cog.on_member_join(member)
    assert sent.await_args.args[1] == "member_join.json"


async def test_leave_sends_goodbye(env):
    m, cog, member, sent = env
    cog.bot.get_guild.return_value = member.guild
    await cog.on_raw_member_remove(MagicMock(user=member, guild_id=1))
    assert sent.await_args.args[1] == "member_leave.json"


async def test_disabled_setting_does_nothing(env, monkeypatch):
    m, cog, member, sent = env
    monkeypatch.setattr(m, "get_setting", lambda k, d=None: False)
    await cog.on_member_join(member)
    await cog.on_raw_member_remove(MagicMock(user=member, guild_id=1))
    member.add_roles.assert_not_awaited()
    sent.assert_not_awaited()


def test_join_embed_has_no_stray_placeholders():
    import json
    import re
    from pathlib import Path
    text = Path(__file__).parent.parent.joinpath("embeds", "member_join.json").read_text(encoding="utf-8")
    strings = []
    def walk(x):
        if isinstance(x, str):
            strings.append(x)
        elif isinstance(x, dict):
            [walk(v) for v in x.values()]
        elif isinstance(x, list):
            [walk(v) for v in x]
    walk(json.loads(text))
    left = {m for t in strings for m in re.findall(r"\{[A-Za-z ]+\}", t)}
    assert left <= {"{user}"}, left
