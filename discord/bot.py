"""
Discord bot initialization and configuration.
"""

import logging
import os

from dotenv import load_dotenv

import nextcord
from nextcord.ext import application_checks, commands
from nextcord import Interaction

from .config import TESTING_GUILD_ID, load_settings

logger = logging.getLogger(__name__)


def create_bot():
    """Create and configure the Discord bot instance."""
    intents = nextcord.Intents.all()
    bot = commands.Bot(intents=intents)

    @bot.event
    async def on_ready():
        logger.info(f'Logged in as {bot.user}')
        # Load settings from database
        await load_settings()
        logger.info("Settings loaded from database")

    @bot.event
    async def on_application_command(ctx: Interaction):
        logger.info(f"/{ctx.application_command.qualified_name} by {ctx.user} ({ctx.user.id})")

    @bot.event
    async def on_application_command_error(ctx: Interaction, error):
        if isinstance(error, (commands.MissingRole, application_checks.ApplicationMissingRole)):
            msg = "You do not have the correct role to use this command."
        elif isinstance(error, commands.MissingPermissions):
            msg = "You do not have the correct permissions to use this command."
        elif isinstance(error, commands.MemberNotFound):
            msg = "Member not found."
        else:
            msg = f"An error occurred: {error}"
            logger.error(f"Unhandled error in /{ctx.application_command.qualified_name} by {ctx.user} ({ctx.user.id})",
                         exc_info=error)
        # Commands defer for slow DB calls, so the first response may already be used.
        send = ctx.followup.send if ctx.response.is_done() else ctx.response.send_message
        await send(msg, ephemeral=True)

    return bot


def load_extensions(bot):
    """Load all bot extensions (listeners and commands)."""
    # Listeners
    bot.load_extension("discord.listeners.BorderOfficerMonitor")
    bot.load_extension("discord.listeners.OfficeHoursMonitor")
    bot.load_extension("discord.listeners.JoinLeaveHandler")

    # Commands
    bot.load_extension("discord.commands.Checkpoint")
    bot.load_extension("discord.commands.Enlistment")
    bot.load_extension("discord.commands.Session")
    bot.load_extension("discord.commands.LOA")
    bot.load_extension("discord.commands.SettingsManagement")
    bot.load_extension("discord.commands.UserManagement")
    bot.load_extension("discord.commands.Info")
    bot.load_extension("discord.commands.Attendance")
    bot.load_extension("discord.commands.RecordAdmin")
    bot.load_extension("discord.commands.TestMsg")


def run_bot():
    """Create the bot, load extensions, and run it."""
    # Load environment variables
    load_dotenv()
    
    # Create bot instance
    bot = create_bot()
    
    # Load all extensions
    load_extensions(bot)
    
    # Run the bot
    bot.run(os.getenv('DISCORD_TOKEN'))


if __name__ == "__main__":
    run_bot()
