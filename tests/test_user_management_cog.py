def test_g0_cog_imports():
    import discord.commands.UserManagement as um
    assert um


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
    interaction.response.defer = AsyncMock(); interaction.followup.send = AsyncMock()
    user = MagicMock(id=int(DISCORD), mention="<@x>", global_name="zz_test_bob")
    return um, interaction, user, um.UserManagement(bot=MagicMock())


def _sent(interaction):
    return interaction.followup.send.call_args


def _member(rank="EN2", **kw):
    return {"name": "zz_test_bob", "rank": rank, "steam_id": STEAM, "deaths": 0,
            "joined_at": None, "enlisted_at": None, "last_death": None,
            "achievements": [], "notes": None, **kw}


async def _add(um, cog, interaction, user, rank=None, steam=STEAM, service_record=False):
    await um.UserManagement.add_member.callback(cog, interaction, user, steam, service_record, rank, None)


async def test_g1_add_member_new(env, monkeypatch):
    um, i, user, cog = env
    create = AsyncMock(return_value={"id": 1})
    monkeypatch.setattr(um, "get_user_info", AsyncMock(return_value=None))
    monkeypatch.setattr(um, "create_user", create)
    await _add(um, cog, i, user)
    kw = create.await_args.kwargs
    assert kw["steam_id"] == STEAM and kw["discord_id"] == DISCORD and kw["service_record"] is False  # identity only by default
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


def test_g8_no_money(env):
    um, _, _, cog = env
    assert not hasattr(cog, "give_money")
    assert "money" not in Path(um.__file__).read_text(encoding="utf-8").lower()


async def test_g9_profile(env, monkeypatch):
    _, i, user, _ = env
    import discord.commands.Info as info
    monkeypatch.setattr(info, "get_user_info", AsyncMock(return_value=_member("EN2")))
    await info.Info.view_profile.callback(info.Info(bot=MagicMock()), i, user)
    embed = _sent(i).kwargs["embed"]
    assert "(EN2)" in {f.name: f.value for f in embed.fields}["Rank"]
    assert "Money" not in [f.name for f in embed.fields]


async def test_g11_flow_shared_db(shared_db, env, monkeypatch):
    from database.user_functions import get_user_info
    from tests.helpers import ids
    um, i, user, cog = env
    steam, discord_id = ids(1)
    user.id = int(discord_id)
    await _add(um, cog, i, user, rank="EN2", steam=steam, service_record=True)
    assert _sent(i).kwargs["embed"].title == "✅ Member Added Successfully"
    import discord.commands.Info as info
    await info.Info.view_profile.callback(info.Info(bot=MagicMock()), i, user)
    assert "Money" not in [f.name for f in _sent(i).kwargs["embed"].fields]
    assert (await get_user_info(discord_id))["rank"] == "EN2"


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
    called = AsyncMock(return_value="linked")
    monkeypatch.setattr(um, "merge_identities", called)
    await um.UserManagement.add_steam.callback(cog, i, user, "https://steamcommunity.com/profiles/76561198150696236")
    called.assert_awaited_once_with(DISCORD, "76561198150696236")
    assert "linked" in _sent(i).args[0]
    called.reset_mock()
    monkeypatch.setattr(um, "resolve_steam_id", AsyncMock(return_value=None))
    await um.UserManagement.add_steam.callback(cog, i, user, "https://steamcommunity.com/id/vanity")
    called.assert_not_awaited()
    assert _sent(i).kwargs["ephemeral"] is True


async def test_add_member_accepts_steam_url(env, monkeypatch):
    um, i, user, cog = env
    create = AsyncMock(return_value={"name": "zz_test_bob", "steam_id": STEAM, "discord_id": DISCORD, "rank": "EN0"})
    monkeypatch.setattr(um, "get_user_info", AsyncMock(return_value=None))
    monkeypatch.setattr(um, "create_user", create)
    await _add(um, cog, i, user, steam=f"https://steamcommunity.com/profiles/{STEAM}")
    assert create.await_args.kwargs["steam_id"] == STEAM


async def test_create_service_record_command(env, monkeypatch):
    um, i, user, cog = env
    create = AsyncMock(return_value="created")
    monkeypatch.setattr(um, "create_service_record", create)
    await um.UserManagement.create_service_record_cmd.callback(cog, i, user, "OF1")
    create.assert_awaited_once_with(DISCORD, "OF1")
    assert "created" in _sent(i).args[0]
    create.return_value = "no_identity"
    await um.UserManagement.create_service_record_cmd.callback(cog, i, user, "OF1")
    assert _sent(i).kwargs["ephemeral"] is True


def test_rank_options_have_22_choices(env):
    import inspect
    um, _, _, _ = env
    for cmd, param in [(um.UserManagement.add_member, "rank"), (um.UserManagement.create_service_record_cmd, "rank")]:
        opt = inspect.signature(cmd.callback).parameters[param].default
        assert len(opt.choices) == 22


@pytest.mark.parametrize("result,text", [("recorded", "Reprimand logged"), ("no_record", "no service record"), ("error", "Database error")])
async def test_reprimand_messages(env, monkeypatch, result, text):
    um, i, user, cog = env
    i.user.id = 1
    add = AsyncMock(return_value=result)
    monkeypatch.setattr(um, "add_reprimand", add)
    await um.UserManagement.reprimand.callback(cog, i, user, "late")
    add.assert_awaited_once_with(DISCORD, "late", "1")
    assert text in _sent(i).args[0]
    assert _sent(i).kwargs["ephemeral"] == (result != "recorded")


async def test_service_record_table(env, monkeypatch):
    import datetime
    import discord.commands.Info as info
    _, i, user, _ = env
    ev = [{"id": 5, "occured_at": datetime.datetime(2026, 1, 2), "event_type": "reprimand", "rank": "EN2", "notes": "late\nagain"},
          {"id": 4, "occured_at": datetime.datetime(2026, 1, 1), "event_type": "enlisted", "rank": None, "notes": None}]
    get = AsyncMock(return_value=ev)
    monkeypatch.setattr(info, "get_service_events", get)
    await info.Info.service_record.callback(info.Info(bot=MagicMock()), i, user, 10)
    get.assert_awaited_once_with(DISCORD, 10)
    out = _sent(i).args[0]
    assert "| 5  | 2026-01-02 | reprimand | EN2  | late again |" in out and out.count("```") == 2 and len(out) < 2000
    monkeypatch.setattr(info, "get_service_events", AsyncMock(return_value=None))
    await info.Info.service_record.callback(info.Info(bot=MagicMock()), i, user, 10)
    assert "no service record" in _sent(i).args[0] and _sent(i).kwargs["ephemeral"]


async def test_add_member_without_steam(env, monkeypatch):
    um, i, user, cog = env
    create = AsyncMock(return_value={"id": 1})
    monkeypatch.setattr(um, "get_user_info", AsyncMock(return_value=None))
    monkeypatch.setattr(um, "create_user", create)
    await _add(um, cog, i, user, steam=None)
    assert create.await_args.kwargs["steam_id"] is None and create.await_args.kwargs["discord_id"] == DISCORD
    assert _sent(i).kwargs["embed"].title == "✅ Member Added Successfully"



async def test_add_member_with_service_record(env, monkeypatch):
    um, i, user, cog = env
    create = AsyncMock(return_value={"id": 1})
    monkeypatch.setattr(um, "get_user_info", AsyncMock(return_value=None))
    monkeypatch.setattr(um, "create_user", create)
    await _add(um, cog, i, user, rank="EN3", service_record=True)
    kw = create.await_args.kwargs
    assert kw["service_record"] is True and kw["rank"] == "EN3"


async def test_add_member_rank_without_service_record_rejected(env, monkeypatch):
    um, i, user, cog = env
    create = AsyncMock()
    monkeypatch.setattr(um, "create_user", create)
    await _add(um, cog, i, user, rank="EN3")
    create.assert_not_awaited()
    assert _sent(i).kwargs["ephemeral"] is True


URL = "https://steamcommunity.com/profiles/76561198150696236"


def _side(sr_id=None, rank=None, status=None):
    return MagicMock(id=1, alias="a", steam_id=1, discord_id=2, sr_id=sr_id, current_rank=rank, service_status=status, accounts=1)


def _merge_env(um, monkeypatch, approve, steam=None, discord=None):
    monkeypatch.setattr(um, "resolve_steam_id", AsyncMock(return_value="76561198150696236"))
    monkeypatch.setattr(um, "get_merge_preview", AsyncMock(return_value={"steam": steam, "discord": discord, "survivor": "discord"}))
    monkeypatch.setattr(um, "confirm", AsyncMock(return_value=approve))
    i_edit = AsyncMock()
    return i_edit


async def test_force_merge_declined(env, monkeypatch):
    um, i, user, cog = env
    _merge_env(um, monkeypatch, False, _side(), _side())
    merge = AsyncMock()
    monkeypatch.setattr(um, "merge_identities", merge)
    await um.UserManagement.force_merge.callback(cog, i, user, URL)
    merge.assert_not_awaited()


async def test_force_merge_approved_and_conflict(env, monkeypatch):
    um, i, user, cog = env
    _merge_env(um, monkeypatch, True, _side(), _side())
    i.edit_original_message = AsyncMock()
    merge = AsyncMock(return_value="merged")
    monkeypatch.setattr(um, "merge_identities", merge)
    await um.UserManagement.force_merge.callback(cog, i, user, URL)
    merge.assert_awaited_once_with(DISCORD, "76561198150696236", force=True)
    assert "merged" in i.edit_original_message.call_args.kwargs["content"]
    merge.return_value = "service_record_conflict"
    await um.UserManagement.force_merge.callback(cog, i, user, URL)
    assert "/merge_service_records" in i.edit_original_message.call_args.kwargs["content"]


async def test_force_merge_no_identity_skips_prompt(env, monkeypatch):
    um, i, user, cog = env
    _merge_env(um, monkeypatch, True, None, None)
    await um.UserManagement.force_merge.callback(cog, i, user, URL)
    um.confirm.assert_not_awaited()
    assert _sent(i).kwargs["ephemeral"] is True


async def test_merge_service_records_no_record(env, monkeypatch):
    um, i, user, cog = env
    _merge_env(um, monkeypatch, True, _side(5, "EN1", "active"), _side())
    merge = AsyncMock()
    monkeypatch.setattr(um, "merge_service_records", merge)
    await um.UserManagement.merge_service_records_cmd.callback(cog, i, user, URL)
    merge.assert_not_awaited()
    um.confirm.assert_not_awaited()


async def test_merge_service_records_declined_and_approved(env, monkeypatch):
    um, i, user, cog = env
    _merge_env(um, monkeypatch, False, _side(5, "EN1", "active"), _side(6, "EN2", "active"))
    merge = AsyncMock(return_value="merged")
    monkeypatch.setattr(um, "merge_service_records", merge)
    await um.UserManagement.merge_service_records_cmd.callback(cog, i, user, URL)
    merge.assert_not_awaited()
    um.confirm.return_value = True
    i.edit_original_message = AsyncMock()
    await um.UserManagement.merge_service_records_cmd.callback(cog, i, user, URL)
    merge.assert_awaited_once_with(DISCORD, "76561198150696236")
    msg = i.edit_original_message.call_args.kwargs["content"]
    assert "EN1" in msg and "EN2" in msg and "/set_rank" in msg
