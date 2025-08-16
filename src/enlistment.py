# enlistment.py
import json

from nextcord import Interaction, Member, NotFound, slash_command
from nextcord.ext import commands

from config import ROLES, IDS
ENLISTED_ROLE = ROLES['enlisted']
MILITARY_MANAGEMENT_ROLE = ROLES['leadership']

class enlistment(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(description="Enlist in the army", guild_ids=[IDS['testing_guild']])
    @commands.has_role(MILITARY_MANAGEMENT_ROLE)
    async def enlist(self, ctx: Interaction, user: Member):
        try:
            enlistment_role = ctx.guild.get_role(ENLISTED_ROLE[0])
            mil_dep_role = ctx.guild.get_role(ENLISTED_ROLE[1])
            await user.add_roles(enlistment_role, mil_dep_role)
            await ctx.response.send_message(f"{user.mention} has been enlisted in the army!")

        except NotFound:
            await ctx.response.send_message(f"User not found", ephemeral=True)
    


# Function to set up the Cog
def setup(bot):
    bot.add_cog(enlistment(bot))
