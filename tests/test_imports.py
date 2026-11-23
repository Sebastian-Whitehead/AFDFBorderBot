"""T2: every cog module and the core packages import cleanly."""
import importlib
import pkgutil

import pytest

import discord.commands
import discord.listeners


def _names():
    names = ["database", "discord.bot"]
    for pkg in (discord.commands, discord.listeners):
        names += [f"{pkg.__name__}.{m.name}" for m in pkgutil.iter_modules(pkg.__path__)]
    return names


@pytest.mark.parametrize("name", _names())
def test_import(name):
    importlib.import_module(name)


def test_no_prefix_role_checks_on_slash_commands():
    # commands.has_role is ignored by slash commands; only application_checks.has_role is enforced
    import pathlib
    for p in pathlib.Path("discord").rglob("*.py"):
        assert "commands.has_role" not in p.read_text(encoding="utf-8").replace("application_checks.has_role", ""), p
