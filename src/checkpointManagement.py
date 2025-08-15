# checkpointManagement.py
import json

import nextcord
from nextcord.ext import commands
from nextcord import Interaction, Member, NotFound, slash_command

with open('config.json') as config_file:
    config = json.load(config_file)

# Replace these with the actual IDs or import them if defined elsewhere
JOINING_ROLE = 1206607575899181168
# BORDER_OFFICER_ROLE = "Border Officer"
BORDER_OFFICER_ROLE = config['roles']['border_officer']
BORDER_APPROVED_ROLE = [1140584332247957615, 1140616787050889286]

MAIN_CHANNEL = config['channels']['main_txt']


class checkpointManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(description="Let them through the border", guild_ids=[config['testing_guild']])
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

    #@commands.Cog.listener() # Uncomment this to activate this feature.
    async def on_member_join(self, member: Member):
        # Adjust the target user's roles
        role_to_add = member.guild.get_role(JOINING_ROLE)
        await member.add_roles(role_to_add)
        
        #Send embed from embeds
        with open('embeds/member_join-welcome.json') as embed_file:
                embed_dict = json.load(embed_file)

    #If not work use on_raw_member_remove
    #@commands.Cog.listener() # Uncomment this to activate this feature.
    async def on_member_remove(self, member: Member):
        
        #Send embed from embeds
        with open('embeds/member_leave-welcome.json') as embed_file:
                embed_dict = json.load(embed_file)


# Function to set up the Cog
def setup(bot):
    bot.add_cog(checkpointManagement(bot))
