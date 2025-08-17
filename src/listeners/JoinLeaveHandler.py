import json

import nextcord
from nextcord.ext import commands
from nextcord import Member

from src.config import JOIN_ROLE_ID, ENABLE_JOIN_LEAVE

class JoinLeaveHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: Member):
        # Check if join/leave listening is enabled
        if not ENABLE_JOIN_LEAVE:
            return
            
        # Check if join role is configured
        if not JOIN_ROLE_ID:
            return
            
        # Adjust the target user's roles
        role_to_add = member.guild.get_role(JOIN_ROLE_ID)
        if role_to_add:
            await member.add_roles(role_to_add)
        
        # Send embed from embeds
        with open('embeds/member_join-welcome.json') as embed_file:
            embed_dict = json.load(embed_file)
            # TODO: Create and send embed to welcome channel

    @commands.Cog.listener()
    async def on_member_remove(self, member: Member):
        # Check if join/leave listening is enabled
        if not ENABLE_JOIN_LEAVE:
            return
            
        # Send embed from embeds
        with open('embeds/member_leave-welcome.json') as embed_file:
            embed_dict = json.load(embed_file)
            # TODO: Create and send embed to log channel

# Function to set up the Cog
def setup(bot):
    bot.add_cog(JoinLeaveHandler(bot))