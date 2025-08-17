import datetime
import json
import os
import random
from src.config import TESTING_GUILD_ID

from dotenv import load_dotenv

import nextcord
from nextcord.ext import commands
from nextcord import Member, NotFound, Interaction

# Load environment variables
load_dotenv()

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
bot.load_extension("src.listeners.BorderOfficerMonitor")
bot.load_extension("src.listeners.JoinLeaveHandler")
#bot.load_extension("src.listeners.GuildEventListener")  # DEPRECATED: Converted to commands

# Commands
bot.load_extension("src.commands.Checkpoint")
bot.load_extension("src.commands.Enlistment")
bot.load_extension("src.commands.GuildEvent")

bot.run(os.getenv('DISCORD_TOKEN'))