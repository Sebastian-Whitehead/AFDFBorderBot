import json

import nextcord
from nextcord.ext import commands
from nextcord import Member

from src.config import ROLES
JOINING_ROLE = ROLES['join_role']

class JoinLeaveHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()  # Uncomment this to activate this feature.
    async def on_member_join(self, member: Member):
        # Adjust the target user's roles
        role_to_add = member.guild.get_role(JOINING_ROLE)
        await member.add_roles(role_to_add)
        
        # Send embed from embeds
        with open('embeds/member_join-welcome.json') as embed_file:
            embed_dict = json.load(embed_file)
            # TODO: Create and send embed to welcome channel

    @commands.Cog.listener()  # If not work use on_raw_member_remove
    async def on_member_remove(self, member: Member):
        # Send embed from embeds
        with open('embeds/member_leave-welcome.json') as embed_file:
            embed_dict = json.load(embed_file)
            # TODO: Create and send embed to log channel

# Function to set up the Cog
def setup(bot):
    bot.add_cog(JoinLeaveHandler(bot))