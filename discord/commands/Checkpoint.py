# Checkpoint.py
from typing import Optional

from nextcord.ext import commands
from nextcord import Interaction, Member, NotFound, SlashOption, slash_command

from database import ensure_player_identity
from ..utils import send_processed_embed, member_replacements
from ..utils.steam import resolve_steam_id
from ..config import get_setting, TESTING_GUILD_ID, JOIN_ROLE_ID, BORDER_OFFICER_ROLE_ID, CITIZEN_ROLE_IDS, MAIN_CHANNEL_ID


class Checkpoint(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(description="Let them through the border", guild_ids=[TESTING_GUILD_ID] if TESTING_GUILD_ID else None)
    @commands.has_role(BORDER_OFFICER_ROLE_ID)
    async def approve(self, ctx: Interaction, user: Member,
                      steam_id: Optional[str] = SlashOption(description="SteamID64 or Steam profile URL (optional)", required=False, default=None)):
        # Check if required roles/channels are configured
        if not JOIN_ROLE_ID or not CITIZEN_ROLE_IDS or not MAIN_CHANNEL_ID:
            await ctx.response.send_message("❌ Bot configuration error - missing required roles or channels!", ephemeral=True)
            return
            
        if len(CITIZEN_ROLE_IDS) < 2:
            await ctx.response.send_message("❌ Bot configuration error - not enough citizen roles configured!", ephemeral=True)
            return

        await ctx.response.defer(ephemeral=True)

        if steam_id:
            steam_id = await resolve_steam_id(steam_id)
            if steam_id is None:
                await ctx.followup.send("❌ Steam ID must be numeric (SteamID64) or a Steam profile link that can be resolved.", ephemeral=True)
                return

        if not await ensure_player_identity(name=user.global_name or user.name, steam_id=steam_id, discord_id=str(user.id)):
            await ctx.followup.send("❌ Could not save the player in the database (Steam or Discord ID already linked to someone else).", ephemeral=True)
            return

        try:
            # Adjust the target user's roles
            role_to_remove = ctx.guild.get_role(JOIN_ROLE_ID)
            role_to_add = ctx.guild.get_role(CITIZEN_ROLE_IDS[0])
            role_to_add1 = ctx.guild.get_role(CITIZEN_ROLE_IDS[1])
            
            if not role_to_remove or not role_to_add or not role_to_add1:
                await ctx.followup.send("❌ Could not find required roles in this server!", ephemeral=True)
                return

            await user.add_roles(role_to_add, role_to_add1)
            await user.remove_roles(role_to_remove)
            guild = ctx.guild
            welcome = get_setting('new-citizen-welcome', True)
            main_channel = guild.get_channel(MAIN_CHANNEL_ID) if welcome else None

            if welcome and not main_channel:
                await ctx.followup.send("❌ Could not find main channel!", ephemeral=True)
                return

            await ctx.followup.send(
                f"✅ {user.mention}'s request to enter the border has been Accepted! Welcome to the Federation")

            if not welcome:
                return

            await send_processed_embed(main_channel, 'newcitizen-main.json', member_replacements(user))

        except NotFound:
            await ctx.followup.send("Member not found.", ephemeral=True)

# Function to set up the Cog
def setup(bot):
    bot.add_cog(Checkpoint(bot))
