"""
Discord bot initialization and configuration.
"""

import datetime
import json
import os
import random
import sys
from pathlib import Path

from dotenv import load_dotenv

import nextcord
from nextcord.ext import commands
from nextcord import Member, NotFound, Interaction

from .config import TESTING_GUILD_ID, load_settings


def create_bot():
    """Create and configure the Discord bot instance."""
    intents = nextcord.Intents.all()
    bot = commands.Bot(intents=intents)

    @bot.event
    async def on_ready():
        print(f'We have logged in as {bot.user}')
        # Load settings from database
        await load_settings()
        print("Settings loaded from database")

    @bot.slash_command(description="My first slash command", guild_ids=[TESTING_GUILD_ID] if TESTING_GUILD_ID else None)
    async def ping(ctx: Interaction):
        random_number = random.randint(1, 50)
        if random_number == 3:
            await ctx.response.send_message("PONG! (╯°□°)╯︵ ┻━┻", ephemeral=True)
            return
        await ctx.response.send_message("Pong!", ephemeral=True)

    @bot.event
    async def on_application_command_error(ctx: Interaction, error):
        if isinstance(error, commands.MissingRole):
            await ctx.response.send_message("You do not have the correct role to use this command.", ephemeral=True)
        elif isinstance(error, commands.MissingPermissions):
            await ctx.response.send_message("You do not have the correct permissions to use this command.", ephemeral=True)
        elif isinstance(error, commands.MemberNotFound):
            await ctx.response.send_message("Member not found.", ephemeral=True)
        else:
            await ctx.response.send_message(f"An error occurred: {error}", ephemeral=True)

    return bot


def load_extensions(bot):
    """Load all bot extensions (listeners and commands)."""
    # Listeners
    bot.load_extension("discord.listeners.BorderOfficerMonitor")
    bot.load_extension("discord.listeners.JoinLeaveHandler")
    #bot.load_extension("discord.listeners.GuildEventListener")  # DEPRECATED: Converted to commands

    # Commands
    bot.load_extension("discord.commands.Checkpoint")
    bot.load_extension("discord.commands.Enlistment")
    bot.load_extension("discord.commands.GuildEvent")
    bot.load_extension("discord.commands.LOA")
    bot.load_extension("discord.commands.SettingsManagement")
    #bot.load_extension("discord.commands.UserManagement")


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
