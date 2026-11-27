"""Every non-public slash command enforces an app_commands role check."""
import discord
from discord import app_commands
from discord.ext import commands

from afdfbot.bot import load_extensions

# open to every member on purpose
PUBLIC = {"ping", "ranks", "profile", "service_record", "loa", "loa_list", "loa_cancel", "session_list"}


async def test_every_non_public_slash_command_enforces_a_role():
    async with commands.Bot(command_prefix="!", intents=discord.Intents.none()) as bot:
        await load_extensions(bot)  # same list the real bot loads
        leaves = [c for c in bot.tree.walk_commands() if isinstance(c, app_commands.Command)]
        for name in list(bot.extensions):
            await bot.unload_extension(name)  # stops the background loops
    assert len(leaves) > 30
    unprotected = {c.qualified_name for c in leaves if not c.checks} - PUBLIC
    assert not unprotected, f"no enforced role check: {sorted(unprotected)}"
