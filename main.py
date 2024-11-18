import datetime
import json
import os
import random

import nextcord
from nextcord.ext import commands
from nextcord import Member, NotFound, Interaction

with open('config.json') as config_file:
    config = json.load(config_file)


intents = nextcord.Intents.all()
bot = commands.Bot(intents=intents)

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')


@bot.slash_command(description="My first slash command", guild_ids=[config['testing_guild']])
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


# ---- Load token and run ----
bot.load_extension("checkpointManagement")
bot.load_extension("enlistment")
bot.load_extension("BorderOfficerMonitor")

bot.run(config['token'])
# -------------------
