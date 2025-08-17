import datetime
import json
import os
import random
import sys
from pathlib import Path
import importlib.util

from dotenv import load_dotenv

import nextcord
from nextcord.ext import commands
from nextcord import Member, NotFound, Interaction

# Load environment variables
load_dotenv()

# Load config from discord folder
config_path = Path(__file__).parent / "discord" / "config.py"
spec = importlib.util.spec_from_file_location("config", config_path)
config_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config_module)

TESTING_GUILD_ID = getattr(config_module, 'TESTING_GUILD_ID', None)

intents = nextcord.Intents.all()
bot = commands.Bot(intents=intents)


@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')


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


# ---- Load extensions ----
# Listeners
bot.load_extension("discord.listeners.BorderOfficerMonitor")
bot.load_extension("discord.listeners.JoinLeaveHandler")
#bot.load_extension("discord.listeners.GuildEventListener")  # DEPRECATED: Converted to commands

# Commands
bot.load_extension("discord.commands.Checkpoint")
bot.load_extension("discord.commands.Enlistment")
bot.load_extension("discord.commands.GuildEvent")

bot.run(os.getenv('DISCORD_TOKEN'))