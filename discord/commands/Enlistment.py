# Enlistment.py
from typing import Optional

from nextcord import Interaction, Member, NotFound, SlashOption, slash_command
from nextcord.ext import commands

from database import enlist_member, discharge_member, get_user_info
from ..utils import RankManager, send_processed_embed
from ..config import (get_setting, MILITARY_MAIN_CHANNEL_ID, LOA_CHANNEL_ID, ANNOUNCEMENTS_CHANNEL_ID,
                      INFORMATION_DB_CHANNEL_ID, EVENTS_TXT_CHANNEL_ID, VIETNAM_CAMPAIGN_CHANNEL_ID,
                      ENLISTED_ROLE_IDS, LEADERSHIP_ROLE_ID, TESTING_GUILD_ID, MILITARY_PERSONNEL_ROLE_ID,
                      DISTINGUISHED_CITIZEN_ROLE_ID)

# Fallback until `/settings set-modpack-url` is used
DEFAULT_MODPACK_URL = "https://discord.com/channels/1140569342619168778/1229466005059801179"

class Enlistment(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.rank_manager = RankManager()

    async def _rank_role_id(self, user: Member) -> Optional[int]:
        """Discord role id for the member's current rank (None if the rank has no role)."""
        info = await get_user_info(str(user.id))
        rank = self.rank_manager.get_rank(info["rank"]) if info else None
        return int(rank["role_id"]) if rank and rank.get("role_id") else None

    @slash_command(description="Enlist in the army", guild_ids=[TESTING_GUILD_ID] if TESTING_GUILD_ID else None)
    @commands.has_role(LEADERSHIP_ROLE_ID)
    async def enlist(self, ctx: Interaction, user: Member,
                     msg: Optional[bool] = SlashOption(description="Send the welcome tour (default: server setting)", required=False)):
        await ctx.response.defer(ephemeral=True)
        # Check if required roles are configured
        if not ENLISTED_ROLE_IDS or not LEADERSHIP_ROLE_ID:
            await ctx.followup.send("❌ Bot configuration error - missing required roles!", ephemeral=True)
            return
            
        if len(ENLISTED_ROLE_IDS) < 2:
            await ctx.followup.send("❌ Bot configuration error - not enough enlisted roles configured!", ephemeral=True)
            return

        result = await enlist_member(str(user.id))
        if result == "no_identity":
            await ctx.followup.send(f"❌ {user.mention} has no player record yet. Approve them (or /add_member) first.", ephemeral=True)
            return
        if result == "error":
            await ctx.followup.send("❌ Database error, roles not changed.", ephemeral=True)
            return

        try:
            enlistment_role = ctx.guild.get_role(ENLISTED_ROLE_IDS[0])
            mil_dep_role = ctx.guild.get_role(ENLISTED_ROLE_IDS[1])
            
            if not enlistment_role or not mil_dep_role:
                await ctx.followup.send("❌ Could not find required roles in this server!", ephemeral=True)
                return
                
            if result == "already_enlisted":
                await ctx.followup.send(f"ℹ️ {user.mention} is already enlisted.", ephemeral=True)
                return
            roles = [enlistment_role, mil_dep_role]
            if result == "reinstated":  # back to their previous rank, not the base rank
                rank_role = ctx.guild.get_role(await self._rank_role_id(user) or 0)
                roles = [mil_dep_role] + ([rank_role] if rank_role else [enlistment_role])
            await user.add_roles(*roles)
            verb = "reinstated at their previous rank" if result == "reinstated" else "enlisted in the army"
            await ctx.followup.send(f"✅ {user.mention} has been {verb}!")

            # Tour only for brand-new enlistments, not reinstated members
            if result == "enlisted" and (get_setting('enlist-welcome', True) if msg is None else msg):
                channel = ctx.guild.get_channel(MILITARY_MAIN_CHANNEL_ID) if MILITARY_MAIN_CHANNEL_ID else None
                if channel:
                    await send_processed_embed(channel, 'enlist-welcome.json', {
                        '{user}': user.mention,
                        '{username}': user.display_name,
                        '{announcements}': str(ANNOUNCEMENTS_CHANNEL_ID),
                        '{information_db}': str(INFORMATION_DB_CHANNEL_ID),
                        '{events}': str(EVENTS_TXT_CHANNEL_ID),
                        '{vietnam_campaign}': str(VIETNAM_CAMPAIGN_CHANNEL_ID),
                        '{loa}': str(LOA_CHANNEL_ID),
                        '{modpack_url}': get_setting('modpack-url', DEFAULT_MODPACK_URL),
                    })

        except NotFound:
            await ctx.followup.send("❌ User not found", ephemeral=True)
        except Exception as e:
            await ctx.followup.send(f"❌ An error occurred: {str(e)}", ephemeral=True)
    
    @slash_command(description="Discharge a member: marks their service record inactive", guild_ids=[TESTING_GUILD_ID] if TESTING_GUILD_ID else None)
    @commands.has_role(LEADERSHIP_ROLE_ID)
    async def discharge(self, ctx: Interaction, user: Member,
                        reason: Optional[str] = SlashOption(description="Reason (optional)", required=False)):
        await ctx.response.defer(ephemeral=True)
        result = await discharge_member(str(user.id), reason)
        if result != "discharged":
            msg = {"no_record": f"❌ {user.mention} has no service record.",
                   "not_enlisted": f"ℹ️ {user.mention} is not currently enlisted.",
                   "error": "❌ Database error, roles not changed."}[result]
            await ctx.followup.send(msg, ephemeral=True)
            return
        rank_role_id = await self._rank_role_id(user)
        roles = [r for r in (ctx.guild.get_role(i) for i in [*ENLISTED_ROLE_IDS, rank_role_id] if i) if r]
        try:
            await user.remove_roles(*roles)
        except Exception as e:
            await ctx.followup.send(f"⚠️ {user.mention} was discharged, but removing roles failed: {e}")
            return
        await ctx.followup.send(f"✅ {user.mention} has been discharged.")

    @slash_command(description="Retire a member: marks their service record retired and gives Distinguished Citizen", guild_ids=[TESTING_GUILD_ID] if TESTING_GUILD_ID else None)
    @commands.has_role(LEADERSHIP_ROLE_ID)
    async def retire(self, ctx: Interaction, user: Member,
                     reason: Optional[str] = SlashOption(description="Reason (optional)", required=False)):
        await ctx.response.defer(ephemeral=True)
        if not DISTINGUISHED_CITIZEN_ROLE_ID:
            await ctx.followup.send("❌ Bot configuration error - distinguished citizen role missing!", ephemeral=True)
            return
        result = await discharge_member(str(user.id), reason, kind="retired")
        if result != "retired":
            msg = {"no_record": f"❌ {user.mention} has no service record.",
                   "not_enlisted": f"ℹ️ {user.mention} is not currently enlisted.",
                   "error": "❌ Database error, roles not changed."}[result]
            await ctx.followup.send(msg, ephemeral=True)
            return
        rank_role_id = await self._rank_role_id(user)
        remove = [r for r in (ctx.guild.get_role(i) for i in (rank_role_id, MILITARY_PERSONNEL_ROLE_ID) if i) if r]
        add = ctx.guild.get_role(DISTINGUISHED_CITIZEN_ROLE_ID)
        try:
            if remove:
                await user.remove_roles(*remove)
            if add:
                await user.add_roles(add)
        except Exception as e:
            await ctx.followup.send(f"⚠️ {user.mention} was retired, but updating roles failed: {e}")
            return
        await ctx.followup.send(f"✅ {user.mention} has been retired. Thank you for your service!")


# Function to set up the Cog
def setup(bot):
    bot.add_cog(Enlistment(bot))
