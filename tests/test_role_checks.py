"""Slash commands only enforce application_checks (checks attach when a cog is bound to a bot)."""
import importlib
import pkgutil

import nextcord
from nextcord.ext import commands

import discord.commands
import discord.listeners
from discord.listeners.BorderOfficerMonitor import BorderOfficerMonitor

# open to every member on purpose
PUBLIC = {"ping", "ranks", "profile", "service_record", "loa", "loa_list", "loa_cancel", "session_list"}


def _all(cmds):
    for c in cmds:
        yield c
        yield from _all(getattr(c, "children", {}).values())


def test_every_non_public_slash_command_enforces_a_role():
    bot = commands.Bot(intents=nextcord.Intents.none())
    BorderOfficerMonitor.check_online_status.start = lambda self: None  # no event loop in a sync test
    for pkg in (discord.commands, discord.listeners):
        for m in pkgutil.iter_modules(pkg.__path__):
            importlib.import_module(f"{pkg.__name__}.{m.name}").setup(bot)
    leaves = [c for c in _all(bot.get_all_application_commands()) if not getattr(c, "children", None)]
    assert len(leaves) > 30
    unprotected = {c.qualified_name for c in leaves if not c.checks} - PUBLIC
    assert not unprotected, f"no enforced role check: {sorted(unprotected)}"
