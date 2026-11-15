import nextcord
from nextcord.ext import commands, tasks

from ..config import TESTING_GUILD_ID, BORDER_OFFICER_ROLE_ID, CHECKPOINT_CHANNEL_ID, get_setting

DEFAULT_CHECK_INTERVAL = 300  # 5 minutes (in seconds)


class BorderOfficerMonitor(commands.Cog):
    def __init__(self, bot):
        self.LastOnlineStatus = False  # Initialize the last known online status
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
            return
        
        # Check and update interval setting (only check every 10th iteration to reduce overhead)
        if self.check_count % 10 == 0:  # Check every 10 cycles
            check_interval = get_setting('border-officer-check-interval', DEFAULT_CHECK_INTERVAL)
            
            # Update the loop interval if it has changed
            if self.current_interval != check_interval:
                print(f"BorderOfficerMonitor: Updating check interval from {self.current_interval}s to {check_interval}s")
                self.current_interval = check_interval
                self.check_online_status.change_interval(seconds=check_interval)
                return  # Exit this iteration to let the new interval take effect
        if not get_setting('listen-for-border-officer', False):
            return
            
        # Check if required config is available
        if not TESTING_GUILD_ID or not BORDER_OFFICER_ROLE_ID or not CHECKPOINT_CHANNEL_ID:
            print("BorderOfficerMonitor: Missing required configuration")
            return
            
        self.check_count += 1
        #print(f"{datetime.datetime.now().strftime()}Checking online status... ")

        guild = self.bot.get_guild(TESTING_GUILD_ID)  # Get the guild by ID
        if not guild:
            print(f"Guild with ID {TESTING_GUILD_ID} not found!")
            return

        role = guild.get_role(BORDER_OFFICER_ROLE_ID)  # Get the role by ID
        if not role:
            print(f"Role with ID {BORDER_OFFICER_ROLE_ID} not found!")
            return

        check_channel = guild.get_channel(CHECKPOINT_CHANNEL_ID)  # Get the channel by ID
        if not check_channel:
            print("Channel not found!")
            return  # Exit if the channel is not found

        # Fetch members to ensure the cache is populated
        await guild.chunk()  # This ensures that all members are loaded
        members = role.members
        online_members = []

        # Check the online status of each member
        for member in members:
            #print(member.name, member.raw_status)
            if member.status not in [nextcord.Status.offline, nextcord.Status.invisible, nextcord.Status.dnd]:
                online_members.append(member)

        
        current_status = len(online_members) > 0  # Determine if any members are online
        if self.LastOnlineStatus == current_status:
            print(f"{self.check_count} - No change in status")
            return

        print(f"Status changed! to {current_status}")
        self.LastOnlineStatus = current_status  # Update the last known online status

        # Send or delete the message based on the current status
        if not current_status:
            if not self.msg:
                self.msg = await check_channel.send(":roundel2: The Aegean Federation immigration department is closing shop for the night, apologies for any inconveniences. :roundel2:")
        else:
            if self.msg:
                await self.msg.delete()
                self.msg = None
        print(f"{self.check_count} - check complete. {len(online_members)} Online border agents")
        

    @check_online_status.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()  # Wait until the bot is ready before starting the loop

    def update_check_interval(self):
        """Force an immediate update of the check interval from settings."""
        check_interval = get_setting('border-officer-check-interval', DEFAULT_CHECK_INTERVAL)
        if self.current_interval != check_interval:
            print(f"BorderOfficerMonitor: Force updating check interval from {self.current_interval}s to {check_interval}s")
            self.current_interval = check_interval
            self.check_online_status.change_interval(seconds=check_interval)


def setup(bot):
    bot.add_cog(BorderOfficerMonitor(bot))
