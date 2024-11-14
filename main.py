import json
import nextcord
from nextcord.ext import commands

TESTING_GUILD_ID = 629027778347532298  # Replace with your guild ID

bot = commands.Bot()


@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')


@bot.slash_command(description="My first slash command", guild_ids=[TESTING_GUILD_ID])
async def hello(interaction: nextcord.Interaction):
    await interaction.send("Hello!")

@bot.slash_command(description="Let them throught the boarder", guild_ids=[TESTING_GUILD_ID])
async def approve(interaction: nextcord.Interaction, user: nextcord.User):
    await interaction.respond.send_message


# ---- Load token and run ----
with open('config.json') as config_file:
    config = json.load(config_file)

bot.run(config['token'])
# -------------------
