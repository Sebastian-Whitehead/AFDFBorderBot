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
