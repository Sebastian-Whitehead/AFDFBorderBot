import logging

import nextcord
from nextcord.ext import application_checks, commands, tasks

from ..config import LEADERSHIP_ROLE_ID, TESTING_GUILD_ID, BORDER_OFFICER_ROLE_ID, CHECKPOINT_CHANNEL_ID, get_setting

logger = logging.getLogger(__name__)

DEFAULT_CHECK_INTERVAL = 300  # 5 minutes (in seconds)
CLOSED_MSG = ":roundel2: The Aegean Federation immigration department is closing shop for the night, apologies for any inconveniences. :roundel2:"


class BorderOfficerMonitor(commands.Cog):
    def __init__(self, bot):
        self.LastOnlineStatus = None  # None = unknown, so the first check always acts
        self.bot = bot
        self.msg = None  # Initialize the message attribute
        self.check_count = 0
        self.current_interval = DEFAULT_CHECK_INTERVAL  # Track current interval
        self.check_online_status.start()  # Start the online status checking loop

    def cog_unload(self):
        self.check_online_status.cancel()  # Cancel the online status checking loop

    @tasks.loop(seconds=DEFAULT_CHECK_INTERVAL)
    async def check_online_status(self):
        # Check if border officer monitoring is enabled first
        if not get_setting('listen-for-border-officer', False):
            # Monitoring switched off: take down the closing message and re-evaluate when re-enabled
            if self.msg:
                try:
                    await self.msg.delete()
                except nextcord.HTTPException:
                    pass  # already gone or not deletable; don't keep retrying
                self.msg = None
            self.LastOnlineStatus = None
            return

        # Re-read the interval setting every 10th iteration to reduce overhead
        if self.check_count % 10 == 0 and self.update_check_interval():
            return  # Exit this iteration to let the new interval take effect
        self.check_count += 1

        # Check if required config is available
        if not TESTING_GUILD_ID or not BORDER_OFFICER_ROLE_ID or not CHECKPOINT_CHANNEL_ID:
            logger.warning("BorderOfficerMonitor: Missing required configuration")
            return

        guild = self.bot.get_guild(TESTING_GUILD_ID)  # Get the guild by ID
        if not guild:
            logger.warning(f"Guild with ID {TESTING_GUILD_ID} not found!")
            return

        role = guild.get_role(BORDER_OFFICER_ROLE_ID)  # Get the role by ID
        if not role:
            logger.warning(f"Role with ID {BORDER_OFFICER_ROLE_ID} not found!")
            return

        check_channel = guild.get_channel(CHECKPOINT_CHANNEL_ID)  # Get the channel by ID
        if not check_channel:
            logger.error(f"BorderOfficerMonitor: channel {CHECKPOINT_CHANNEL_ID} not found, stopping loop")
            self.check_online_status.cancel()
            return

        # Fetch members to ensure the cache is populated
        await guild.chunk()  # This ensures that all members are loaded
        members = role.members
        online_members = []

        # Check the online status of each member
        for member in members:
            #print(member.name, member.raw_status)
            if member.status not in [nextcord.Status.offline, nextcord.Status.invisible]:
                online_members.append(member)

        
        current_status = len(online_members) > 0  # Determine if any members are online

        # Closing message deleted by hand: forget it and treat state as unknown so it is reposted
        if self.msg and not current_status:
            try:
                await check_channel.fetch_message(self.msg.id)
            except nextcord.NotFound:
                self.msg = None
                self.LastOnlineStatus = None
            except nextcord.HTTPException:
                pass

        if self.LastOnlineStatus == current_status:
            logger.debug(f"{self.check_count} - No change in status")
            return

        logger.info(f"Status changed! to {current_status}")

        # Send or delete the message based on the current status
        try:
            # Recover a closing message left over from before a restart
            if not self.msg:
                async for m in check_channel.history(limit=50):
                    if m.author == self.bot.user and m.content == CLOSED_MSG:
                        self.msg = m
                        break

            if not current_status:
                if not self.msg:
                    self.msg = await check_channel.send(CLOSED_MSG)
            elif self.msg:
                await self.msg.delete()
                self.msg = None
            self.LastOnlineStatus = current_status  # Only after success, so failures retry next check
        except nextcord.NotFound:
            self.msg = None  # Message already gone, which is the state we wanted when going online
            self.LastOnlineStatus = current_status
        except nextcord.HTTPException:
            logger.exception("BorderOfficerMonitor: failed to update closing message, will retry")
            return
        logger.debug(f"{self.check_count} - check complete. {len(online_members)} Online border agents")
        

    @check_online_status.error
    async def check_online_status_error(self, error):
        # Without this the loop stops silently on any unhandled exception
        logger.error("BorderOfficerMonitor: loop stopped by an unhandled error; use /border_officer_monitor_start to restart", exc_info=error)

    @check_online_status.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()  # Wait until the bot is ready before starting the loop

    @nextcord.slash_command(
        name="border_officer_monitor_start",
        description="Restart the border officer monitor loop if it has stopped",
        guild_ids=[TESTING_GUILD_ID] if TESTING_GUILD_ID else None,
    )
    @application_checks.has_role(LEADERSHIP_ROLE_ID)
    async def monitor_start(self, interaction: nextcord.Interaction):
        if self.check_online_status.is_running():
            await interaction.response.send_message("The monitor is already running.", ephemeral=True)
            return
        self.LastOnlineStatus = None  # re-evaluate state on the first check
        self.check_online_status.start()
        await interaction.response.send_message("Border officer monitor restarted.", ephemeral=True)

    def update_check_interval(self):
        """Apply the check interval from settings; returns True if the loop interval changed."""
        check_interval = get_setting('border-officer-check-interval', DEFAULT_CHECK_INTERVAL)
        if self.current_interval != check_interval:
            logger.info(f"BorderOfficerMonitor: Updating check interval from {self.current_interval}s to {check_interval}s")
            self.current_interval = check_interval
            self.check_online_status.change_interval(seconds=check_interval)
            return True
        return False


def setup(bot):
    bot.add_cog(BorderOfficerMonitor(bot))
