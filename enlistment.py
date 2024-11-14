# enlistment.py
import json

from nextcord import Interaction, Member, NotFound, slash_command
from nextcord.ext import commands

with open('config.json') as config_file:
    config = json.load(config_file)

MILITARY_MANAGEMENT_ROLE = 1215619605834371093
ENLISTED_ROLE = 1206596239379005490


class enlistment(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(description="Enlist in the army", guild_ids=[config['testing_guild']])
    @commands.has_role(MILITARY_MANAGEMENT_ROLE)
    async def enlist(self, ctx: Interaction, user: Member):
        try:
            enlistment_role = ctx.guild.get_role(ENLISTED_ROLE)
            await user.add_roles(enlistment_role)
            await ctx.response.send_message(f"{user.mention} has been enlisted in the army!")

        except NotFound:
            await ctx.response.send_message(f"User not found", ephemeral=True)


# Function to set up the Cog
def setup(bot):
    bot.add_cog(enlistment(bot))
