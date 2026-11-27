import pytest

from database.db_manager import get_db_manager
from database.settings_manager import (
    get_all_settings,
    get_setting,
    get_settings_manager,
    update_setting,
)

KEY = "zz_test_setting"


@pytest.fixture
async def clean_settings(local_db):
    async def wipe():
        db = await get_db_manager()
        await db.execute_raw_query("DELETE FROM bot_settings WHERE setting_key LIKE 'zz_test_%'")
        (await get_settings_manager())._cache.pop(KEY, None)

    await wipe()
    yield
    await wipe()


async def test_s1_setting_round_trip(clean_settings):
    assert await get_setting(KEY, "missing") == "missing"

    assert await update_setting(KEY, {"a": 1, "b": [1, 2]}) is True
    assert await get_setting(KEY) == {"a": 1, "b": [1, 2]}

    # Overwrite, then drop the cache so the value must come back from the DB.
    assert await update_setting(KEY, "second") is True
    (await get_settings_manager())._cache.pop(KEY, None)
    assert await get_setting(KEY) is None
    assert (await get_all_settings())[KEY] == "second"
    assert await get_setting(KEY) == "second"


async def test_config_update_setting_false_when_db_write_fails(monkeypatch):
    import afdfbot.config as cfg

    async def fail(key, value):
        return False

    monkeypatch.setattr(cfg, "update_db_setting", fail)
    monkeypatch.setitem(cfg.SETTINGS, KEY, "old")
    assert await cfg.update_setting(KEY, "new") is False
    assert cfg.get_setting(KEY) == "old"


def test_leadership_commands_enforce_role(monkeypatch):
    from unittest.mock import AsyncMock
    import asyncio
    import discord
    from discord.ext import commands
    from afdfbot.commands.SettingsManagement import SettingsManagement
    from afdfbot.listeners.BorderOfficerMonitor import BorderOfficerMonitor
    bot = commands.Bot(command_prefix="!", intents=discord.Intents.none())

    async def load():  # add_cog is async in discord.py
        await bot.add_cog(SettingsManagement(bot))
        await bot.add_cog(BorderOfficerMonitor(bot))

    monkeypatch.setattr(BorderOfficerMonitor.check_online_status, "start", lambda *a: None, raising=False)
    monkeypatch.setattr(BorderOfficerMonitor, "cog_load", AsyncMock(), raising=False)
    asyncio.run(load())
    cmds = {c.qualified_name: c for c in bot.tree.get_commands()}
    subs = list(cmds["settings"].commands) + [cmds["border_officer_monitor_start"]]
    assert len(subs) == 6
    for c in subs:
        assert c.checks, f"{c.qualified_name} has no enforced role check"
