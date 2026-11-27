"""
Discord bot initialization and configuration.
"""

import logging
import os

from dotenv import load_dotenv

import discord
from discord import Interaction, app_commands
from discord.ext import commands

from .config import TESTING_GUILD_ID, load_settings

logger = logging.getLogger(__name__)


class _Tree(app_commands.CommandTree):
    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.type is discord.InteractionType.application_command and interaction.command:
            logger.info(f"/{interaction.command.qualified_name} by {interaction.user} ({interaction.user.id})")
        return True

    async def on_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingRole):
            msg = "You do not have the correct role to use this command."
        elif isinstance(error, app_commands.MissingPermissions):
            msg = "You do not have the correct permissions to use this command."
        elif isinstance(error, app_commands.TransformerError) and error.type is discord.AppCommandOptionType.user:
            msg = "Member not found."
        else:
            msg = f"An error occurred: {getattr(error, 'original', error)}"
            name = interaction.command.qualified_name if interaction.command else "?"
            logger.error(f"Unhandled error in /{name} by {interaction.user} ({interaction.user.id})", exc_info=error)
        # Commands defer for slow DB calls, so the first response may already be used.
        send = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
        await send(msg, ephemeral=True)


class _Bot(commands.Bot):
    async def setup_hook(self):
        await load_extensions(self)
        if TESTING_GUILD_ID:
            # Guild commands update instantly. Never also sync globally, or every command shows twice.
            guild = discord.Object(id=TESTING_GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()


def create_bot():
    """Create and configure the Discord bot instance."""
    intents = discord.Intents.all()
    bot = _Bot(command_prefix=commands.when_mentioned, help_command=None,  # slash-only
               intents=intents, tree_cls=_Tree)

    @bot.event
    async def on_ready():
        logger.info(f'Logged in as {bot.user}')
        # Load settings from database
        await load_settings()
        logger.info("Settings loaded from database")

    return bot


async def load_extensions(bot):
    """Load all bot extensions (listeners and commands)."""
    # Listeners
    await bot.load_extension("afdfbot.listeners.BorderOfficerMonitor")
    await bot.load_extension("afdfbot.listeners.OfficeHoursMonitor")
    await bot.load_extension("afdfbot.listeners.JoinLeaveHandler")

    # Commands
    await bot.load_extension("afdfbot.commands.Checkpoint")
    await bot.load_extension("afdfbot.commands.Enlistment")
    await bot.load_extension("afdfbot.commands.Session")
    await bot.load_extension("afdfbot.commands.LOA")
    await bot.load_extension("afdfbot.commands.SettingsManagement")
    await bot.load_extension("afdfbot.commands.UserManagement")
    await bot.load_extension("afdfbot.commands.Info")
    await bot.load_extension("afdfbot.commands.Attendance")
    await bot.load_extension("afdfbot.commands.RecordAdmin")
    await bot.load_extension("afdfbot.commands.TestMsg")


def run_bot():
    """Create the bot, load extensions, and run it."""
    # Load environment variables
    load_dotenv()
    
    # Create bot instance
    bot = create_bot()
    
    # Run the bot (main.py already configures logging); extensions load in setup_hook
    bot.run(os.getenv('DISCORD_TOKEN'), log_handler=None)


if __name__ == "__main__":
    run_bot()
