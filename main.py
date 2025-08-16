import datetime
import json
import os
import random
from config import IDS

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


@bot.slash_command(description="My first slash command", guild_ids=[IDS['testing_guild']])
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
bot.load_extension("src.Routines.BorderOfficerMonitor")
bot.load_extension("src.Routines.JoinLeaveMonitor")
bot.load_extension("src.checkpointManagement")
bot.load_extension("src.enlistment")
#bot.load_extension("src.events")  # DEPRECATED: Module deprecated as of v1.0.0

bot.run(os.getenv('DISCORD_TOKEN'))
# -------------------