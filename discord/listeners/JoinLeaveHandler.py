import logging

import nextcord
from nextcord.ext import commands
from nextcord import Member

from ..config import JOIN_ROLE_ID, WELCOME_CHANNEL_ID, get_setting
from ..utils import send_processed_embed, member_replacements

logger = logging.getLogger(__name__)


class JoinLeaveHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: Member):
        logger.info(f"Member joined: {member} ({member.id})")
        if not get_setting('listen-for-join-leave', True):
            logger.info("Join handling skipped: listen-for-join-leave is off")
            return

        # Check if join role is configured
        if JOIN_ROLE_ID:
            role_to_add = member.guild.get_role(JOIN_ROLE_ID)
            if role_to_add:
                try:
                    await member.add_roles(role_to_add)
                except nextcord.HTTPException as e:  # e.g. Forbidden: bot role below the join role
                    logger.error(f"Could not give join role to {member.id}: {e}")
        
        # Send welcome embed
        welcome_channel = member.guild.get_channel(WELCOME_CHANNEL_ID) if WELCOME_CHANNEL_ID else None
        if not welcome_channel:
            logger.warning(f"Join message skipped: welcome channel {WELCOME_CHANNEL_ID} not found")
            return
        sent = await send_processed_embed(welcome_channel, 'member_join.json', member_replacements(member))
        logger.info(f"Join message for {member.id} {'sent' if sent else 'FAILED'}")

    @commands.Cog.listener()
    async def on_raw_member_remove(self, payload: nextcord.RawMemberRemoveEvent):
        # Raw event: on_member_remove is skipped when the member isn't in the cache
        user = payload.user
        logger.info(f"Member left: {user} ({user.id})")
        if not get_setting('listen-for-join-leave', True):
            logger.info("Leave message skipped: listen-for-join-leave is off")
            return

        guild = self.bot.get_guild(payload.guild_id)
        welcome_channel = guild.get_channel(WELCOME_CHANNEL_ID) if guild and WELCOME_CHANNEL_ID else None
        if not welcome_channel:
            logger.warning(f"Leave message skipped: welcome channel {WELCOME_CHANNEL_ID} not found")
            return
        sent = await send_processed_embed(welcome_channel, 'member_leave.json', member_replacements(user))
        logger.info(f"Leave message for {user.id} {'sent' if sent else 'FAILED'}")

# Function to set up the Cog
def setup(bot):
    bot.add_cog(JoinLeaveHandler(bot))