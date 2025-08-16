# checkpointManagement.py
import json

import nextcord
from nextcord.ext import commands
from nextcord import Interaction, Member, NotFound, slash_command

from config import IDS, ROLES, CHANNELS

# Replace these with the actual IDs or import them if defined elsewhere
JOINING_ROLE = ROLES['join_role']
BORDER_OFFICER_ROLE = ROLES['border_officer']
BORDER_APPROVED_ROLE = ROLES['citizen']
MAIN_CHANNEL = CHANNELS['main_txt']


class checkpointManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(description="Let them through the border", guild_ids=[IDS['testing_guild']])
    @commands.has_role(BORDER_OFFICER_ROLE)
    async def approve(self, ctx: Interaction, user: Member):
        try:
            # Adjust the target user's roles
            role_to_remove = ctx.guild.get_role(JOINING_ROLE)
            role_to_add = ctx.guild.get_role(BORDER_APPROVED_ROLE[0])
            role_to_add1 = ctx.guild.get_role(BORDER_APPROVED_ROLE[1])

            await user.add_roles(role_to_add, role_to_add1)
            await user.remove_roles(role_to_remove)
            guild = ctx.guild
            main_channel = guild.get_channel(MAIN_CHANNEL)

            await ctx.response.send_message(
                f"{user.mention}'s request to enter the border has been Accepted! Welcome to the Federation")

            with open('embeds/newcitizen-main.json') as embed_file:
                embed_dict = json.load(embed_file)
                
                
                embed_dict['title'] = embed_dict['title'].format(username=user.global_name)

                # Catch none value for global_name
                if user.global_name is None:
                    embed_dict['title'] = "A NEW CITIZEN HAS ARRIVED!"
                
                embed_dict['description'] = embed_dict['description'].format(username=user.mention)
                embed_dict['thumbnail']['url'] = embed_dict['thumbnail']['url'].format(profile_picture=user.avatar.url)
            citizen_embed = nextcord.Embed.from_dict(embed_dict)

            await main_channel.send(content=user.mention, embed=citizen_embed)

        except NotFound:
            await ctx.response.send_message("Member not found.", ephemeral=True)

# Function to set up the Cog
def setup(bot):
    bot.add_cog(checkpointManagement(bot))
