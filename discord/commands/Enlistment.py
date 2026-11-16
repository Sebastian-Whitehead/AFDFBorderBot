# Enlistment.py
from typing import Optional

from nextcord import Interaction, Member, NotFound, SlashOption, slash_command
from nextcord.ext import commands

from database import enlist_member, discharge_member, get_user_info
from ..utils import RankManager
from ..config import ENLISTED_ROLE_IDS, LEADERSHIP_ROLE_ID, TESTING_GUILD_ID

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
    async def enlist(self, ctx: Interaction, user: Member):
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


# Function to set up the Cog
def setup(bot):
    bot.add_cog(Enlistment(bot))
