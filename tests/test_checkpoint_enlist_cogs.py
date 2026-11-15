from unittest.mock import AsyncMock, MagicMock

import pytest

STEAM = "76561190000000068"
DISCORD = "900000000000000068"


def _setup(monkeypatch, mod):
    """Make config constants truthy and wire a guild whose roles/channel exist."""
    for name, val in (("JOIN_ROLE_ID", 1), ("CITIZEN_ROLE_IDS", [2, 3]), ("MAIN_CHANNEL_ID", 4),
                      ("ENLISTED_ROLE_IDS", [5, 6]), ("LEADERSHIP_ROLE_ID", 7)):
        if hasattr(mod, name):
            monkeypatch.setattr(mod, name, val)
    order = MagicMock()  # parent mock records relative call order
    i = MagicMock()
    i.response.send_message = AsyncMock()
    i.guild.get_role.side_effect = lambda rid: MagicMock(name=f"role{rid}")
    i.guild.get_channel.return_value = MagicMock(send=AsyncMock())
    user = MagicMock(id=int(DISCORD), mention="<@x>", global_name="Bob")
    user.name = "bob"
    user.add_roles = AsyncMock()
    user.remove_roles = AsyncMock()
    order.attach_mock(user.add_roles, "add_roles")
    return i, user, order


def _ephemeral_sent(i):
    return any(c.kwargs.get("ephemeral") is True for c in i.response.send_message.call_args_list)


async def _approve(cog_mod, cog, i, user, steam):
    try:
        await cog_mod.Checkpoint.approve.callback(cog, i, user, steam)
    except Exception:
        pass  # post-role steps read embed files / avatar; only the DB call and role ordering matter here


@pytest.fixture
def checkpoint():
    import discord.commands.Checkpoint as m
    return m, m.Checkpoint(bot=MagicMock())


@pytest.fixture
def enlistment():
    import discord.commands.Enlistment as m
    return m, m.Enlistment(bot=MagicMock())


async def test_c1_approve_db_before_roles(checkpoint, monkeypatch):
    m, cog = checkpoint
    i, user, order = _setup(monkeypatch, m)
    ensure = AsyncMock(return_value=True)
    order.attach_mock(ensure, "ensure")
    monkeypatch.setattr(m, "ensure_player_identity", ensure)
    await _approve(m, cog, i, user, STEAM)
    ensure.assert_awaited_once()
    args = list(ensure.await_args.args) + list(ensure.await_args.kwargs.values())
    assert STEAM in args and DISCORD in args
    names = [c[0] for c in order.mock_calls if c[0] in ("ensure", "add_roles")]
    assert names[:2] == ["ensure", "add_roles"]


async def test_c2_approve_identity_false_aborts(checkpoint, monkeypatch):
    m, cog = checkpoint
    i, user, _ = _setup(monkeypatch, m)
    monkeypatch.setattr(m, "ensure_player_identity", AsyncMock(return_value=False))
    await _approve(m, cog, i, user, STEAM)
    user.add_roles.assert_not_awaited()
    assert _ephemeral_sent(i)


async def test_c3_approve_non_numeric_steam(checkpoint, monkeypatch):
    m, cog = checkpoint
    i, user, _ = _setup(monkeypatch, m)
    ensure = AsyncMock(return_value=True)
    monkeypatch.setattr(m, "ensure_player_identity", ensure)
    await _approve(m, cog, i, user, "abc")
    user.add_roles.assert_not_awaited()
    assert _ephemeral_sent(i)


async def test_e1_enlist_db_before_roles(enlistment, monkeypatch):
    m, cog = enlistment
    i, user, order = _setup(monkeypatch, m)
    enlist = AsyncMock(return_value="enlisted")
    order.attach_mock(enlist, "enlist")
    monkeypatch.setattr(m, "enlist_member", enlist)
    await m.Enlistment.enlist.callback(cog, i, user)
    enlist.assert_awaited_once()
    args = list(enlist.await_args.args) + list(enlist.await_args.kwargs.values())
    assert DISCORD in args
    names = [c[0] for c in order.mock_calls if c[0] in ("enlist", "add_roles")]
    assert names[:2] == ["enlist", "add_roles"]


@pytest.mark.parametrize("result", ["no_identity", "error"])
async def test_e2_enlist_failure_aborts(enlistment, monkeypatch, result):
    m, cog = enlistment
    i, user, _ = _setup(monkeypatch, m)
    monkeypatch.setattr(m, "enlist_member", AsyncMock(return_value=result))
    await m.Enlistment.enlist.callback(cog, i, user)
    user.add_roles.assert_not_awaited()
    assert _ephemeral_sent(i)


async def test_c_approve_url_converted_before_db(checkpoint, monkeypatch):
    m, cog = checkpoint
    i, user, _ = _setup(monkeypatch, m)
    ensure = AsyncMock(return_value=True)
    monkeypatch.setattr(m, "ensure_player_identity", ensure)
    await _approve(m, cog, i, user, f"https://steamcommunity.com/profiles/{STEAM}")
    assert ensure.await_args.kwargs["steam_id"] == STEAM
