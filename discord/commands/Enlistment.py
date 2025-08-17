# Enlistment.py
from nextcord import Interaction, Member, NotFound, slash_command
from nextcord.ext import commands

from ..config import ENLISTED_ROLE_IDS, LEADERSHIP_ROLE_ID, TESTING_GUILD_ID

class Enlistment(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(description="Enlist in the army", guild_ids=[TESTING_GUILD_ID] if TESTING_GUILD_ID else None)
    @commands.has_role(LEADERSHIP_ROLE_ID)
    async def enlist(self, ctx: Interaction, user: Member):
        # Check if required roles are configured
        if not ENLISTED_ROLE_IDS or not LEADERSHIP_ROLE_ID:
            await ctx.response.send_message("❌ Bot configuration error - missing required roles!", ephemeral=True)
            return
            
        if len(ENLISTED_ROLE_IDS) < 2:
            await ctx.response.send_message("❌ Bot configuration error - not enough enlisted roles configured!", ephemeral=True)
            return
            
        try:
            enlistment_role = ctx.guild.get_role(ENLISTED_ROLE_IDS[0])
            mil_dep_role = ctx.guild.get_role(ENLISTED_ROLE_IDS[1])
            
            if not enlistment_role or not mil_dep_role:
                await ctx.response.send_message("❌ Could not find required roles in this server!", ephemeral=True)
                return
                
            await user.add_roles(enlistment_role, mil_dep_role)
            await ctx.response.send_message(f"✅ {user.mention} has been enlisted in the army!")

        except NotFound:
            await ctx.response.send_message(f"❌ User not found", ephemeral=True)
        except Exception as e:
            await ctx.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)
    


# Function to set up the Cog
def setup(bot):
    bot.add_cog(Enlistment(bot))
