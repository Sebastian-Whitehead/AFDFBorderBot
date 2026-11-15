def test_g0_cog_imports():
    import discord.commands.UserManagement  # noqa: F401


import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

STEAM = "76561190000000001"
DISCORD = "900000000000000001"


@pytest.fixture
def env():
    import discord.commands.UserManagement as um
    interaction = MagicMock()
    interaction.id = 42
    interaction.response.send_message = AsyncMock()
    user = MagicMock(id=int(DISCORD), mention="<@x>")
    return um, interaction, user, um.UserManagement(bot=MagicMock())


def _sent(interaction):
    return interaction.response.send_message.call_args


def _member(rank=2, **kw):
    return {"name": "zz_test_bob", "rank": rank, "steam_id": STEAM, "deaths": 0,
            "joined_at": None, "enlisted_at": None, "last_death": None,
            "achievements": [], "notes": None, **kw}


async def _add(um, cog, interaction, user, rank=0, steam=STEAM):
    await um.UserManagement.add_member.callback(cog, interaction, "zz_test_bob", steam, user, rank, None)


async def test_g1_add_member_new(env, monkeypatch):
    um, i, user, cog = env
    create = AsyncMock(return_value={"id": 1})
    monkeypatch.setattr(um, "get_user_info", AsyncMock(return_value=None))
    monkeypatch.setattr(um, "create_user", create)
    await _add(um, cog, i, user)
    kw = create.await_args.kwargs
    assert kw["steam_id"] == STEAM and kw["discord_id"] == DISCORD and kw["rank"] == 0
    assert _sent(i).kwargs["embed"].title == "✅ Member Added Successfully"


async def test_g2_add_member_non_numeric_steam(env, monkeypatch):
    um, i, user, cog = env
    create = AsyncMock()
    monkeypatch.setattr(um, "get_user_info", AsyncMock(return_value=None))
    monkeypatch.setattr(um, "create_user", create)
    await _add(um, cog, i, user, steam="abc")
    assert "numeric" in _sent(i).args[0] and _sent(i).kwargs["ephemeral"] is True
    create.assert_not_awaited()


async def test_g3_add_member_exists(env, monkeypatch):
    um, i, user, cog = env
    create = AsyncMock()
    monkeypatch.setattr(um, "get_user_info", AsyncMock(return_value=_member()))
    monkeypatch.setattr(um, "create_user", create)
    await _add(um, cog, i, user)
    assert "already exists" in _sent(i).args[0] and _sent(i).kwargs["ephemeral"] is True
    create.assert_not_awaited()


async def test_g4_add_member_create_fails(env, monkeypatch):
    um, i, user, cog = env
    monkeypatch.setattr(um, "get_user_info", AsyncMock(return_value=None))
    monkeypatch.setattr(um, "create_user", AsyncMock(return_value=None))
    await _add(um, cog, i, user)
    assert "Failed to add member" in _sent(i).args[0] and _sent(i).kwargs["ephemeral"] is True


async def test_g5_promote(env, monkeypatch):
    um, i, user, cog = env
    modify = AsyncMock(return_value=True)
    monkeypatch.setattr(um, "get_user_info", AsyncMock(return_value=_member(2)))
    monkeypatch.setattr(um, "modify_user", modify)
    await um.UserManagement.promote_member.callback(cog, i, user, 3, None)
    assert modify.await_args.kwargs["rank"] == 3
    assert "Promoted" in modify.await_args.kwargs["reason"]
    assert _sent(i).kwargs["embed"].title == "🎉 Promotion Successful"


async def test_g6_promote_too_far(env, monkeypatch):
    um, i, user, cog = env
    modify = AsyncMock(return_value=True)
    monkeypatch.setattr(um, "get_user_info", AsyncMock(return_value=_member(2)))
    monkeypatch.setattr(um, "modify_user", modify)
    await um.UserManagement.promote_member.callback(cog, i, user, 6, None)
    assert "Invalid rank progression" in _sent(i).args[0] and _sent(i).kwargs["ephemeral"] is True
    modify.assert_not_awaited()


async def test_g7_demote(env, monkeypatch):
    um, i, user, cog = env
    modify = AsyncMock(return_value=True)
    monkeypatch.setattr(um, "get_user_info", AsyncMock(return_value=_member(3)))
    monkeypatch.setattr(um, "modify_user", modify)
    await um.UserManagement.demote_member.callback(cog, i, user, 3, "because")
    modify.assert_not_awaited()
    assert _sent(i).kwargs["ephemeral"] is True
    await um.UserManagement.demote_member.callback(cog, i, user, 2, "because")
    assert "because" in modify.await_args.kwargs["reason"]
    assert modify.await_args.kwargs["rank"] == 2


def test_g8_no_money(env):
    um, _, _, cog = env
    assert not hasattr(cog, "give_money")
    assert "money" not in Path(um.__file__).read_text(encoding="utf-8").lower()


async def test_g9_profile(env, monkeypatch):
    um, i, user, cog = env
    monkeypatch.setattr(um, "get_user_info", AsyncMock(return_value=_member(2)))
    await um.UserManagement.view_profile.callback(cog, i, user)
    embed = _sent(i).kwargs["embed"]
    assert "Money" not in [f.name for f in embed.fields]


async def test_g10_leaderboard_rank(env, monkeypatch):
    um, i, user, cog = env
    monkeypatch.setattr(um, "get_user_count_by_rank", AsyncMock(return_value={0: 1, 3: 2}))
    await um.UserManagement.leaderboard.callback(cog, i, "rank", 10)
    ranks = json.loads((Path(um.__file__).parents[2] / "ids.json").read_text())["roles"]["ranks"]
    desc = _sent(i).kwargs["embed"].description
    assert ranks["0"]["name"] in desc and ranks["3"]["name"] in desc


async def test_g11_flow_shared_db(shared_db, env):
    from database.user_functions import get_user_info
    from tests.helpers import ids
    um, i, user, cog = env
    steam, discord_id = ids(1)
    user.id = int(discord_id)
    await _add(um, cog, i, user, rank=2, steam=steam)
    assert _sent(i).kwargs["embed"].title == "✅ Member Added Successfully"
    await um.UserManagement.promote_member.callback(cog, i, user, 3, None)
    assert _sent(i).kwargs["embed"].title == "🎉 Promotion Successful"
    await um.UserManagement.view_profile.callback(cog, i, user)
    assert "Money" not in [f.name for f in _sent(i).kwargs["embed"].fields]
    assert (await get_user_info(discord_id))["rank"] == 3


def test_add_steam_parse():
    from discord.utils.steam import parse_steam_id
    s = "76561198150696236"
    assert parse_steam_id(s) == s
    assert parse_steam_id(f"https://steamcommunity.com/profiles/{s}/") == s
    assert parse_steam_id(f"steamcommunity.com/profiles/{s}") == s
    assert parse_steam_id("https://steamcommunity.com/id/someone") is None
    assert parse_steam_id("abc") is None
    assert parse_steam_id("12345") == "12345"  # bare numeric passes through as before


async def test_add_steam_command(env, monkeypatch):
    um, i, user, cog = env
    called = AsyncMock(return_value="updated")
    monkeypatch.setattr(um, "set_steam_id", called)
    await um.UserManagement.add_steam.callback(cog, i, user, "https://steamcommunity.com/profiles/76561198150696236")
    called.assert_awaited_once_with(DISCORD, "76561198150696236")
    assert "added" in _sent(i).args[0]
    called.reset_mock()
    await um.UserManagement.add_steam.callback(cog, i, user, "https://steamcommunity.com/id/vanity")
    called.assert_not_awaited()
    assert _sent(i).kwargs["ephemeral"] is True


async def test_add_member_accepts_steam_url(env, monkeypatch):
    um, i, user, cog = env
    create = AsyncMock(return_value={"name": "zz_test_bob", "steam_id": STEAM, "discord_id": DISCORD, "rank": 0})
    monkeypatch.setattr(um, "get_user_info", AsyncMock(return_value=None))
    monkeypatch.setattr(um, "create_user", create)
    await _add(um, cog, i, user, steam=f"https://steamcommunity.com/profiles/{STEAM}")
    assert create.await_args.kwargs["steam_id"] == STEAM
