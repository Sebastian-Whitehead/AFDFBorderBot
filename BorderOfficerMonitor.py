import datetime
import json

import nextcord
from nextcord.ext import commands, tasks

with open('config.json') as config_file:
    config = json.load(config_file)

BORDER_OFFICER_ROLE = 1205844937233666049  # Replace with your role ID
CHECK_CHANNEL_ID = 1205850873616539709
CHECK_INTERVAL = 60  # 1 minute


class BorderOfficerMonitor(commands.Cog):
    """
    A Discord bot cog that monitors the online status of members with a specific role
    and sends a message to a designated channel if no members are online.
    Attributes:
        bot (commands.Bot): The bot instance.
        LastOnlineStatus (bool): The last known online status of the monitored role members.
        msg (nextcord.Message): The message sent to the channel when no members are online.
    Methods:
        cog_unload():
            Cancels the online status checking loop when the cog is unloaded.
        check_online_status():
            Periodically checks the online status of members with the specified role
            and updates the channel message accordingly.
        before_check():
            Waits until the bot is ready before starting the online status checking loop.
    """

    def __init__(self, bot):
        self.LastOnlineStatus = False  # Initialize the last known online status
        self.bot = bot
        self.check_online_status.start()  # Start the online status checking loop
        self.msg = None  # Initialize the message attribute
        self.check_count = 0

    def cog_unload(self):
        self.check_online_status.cancel()  # Cancel the online status checking loop

    @tasks.loop(seconds=CHECK_INTERVAL)
    async def check_online_status(self):
        self.check_count += 1
        #print(f"{datetime.datetime.now().strftime()}Checking online status... ")

        guild = self.bot.get_guild(config['testing_guild'])  # Get the guild by ID
        if not guild:
            print(f"Guild with ID {config['testing_guild']} not found!")
            return

        role = guild.get_role(BORDER_OFFICER_ROLE)  # Get the role by ID
        if not role:
            print(f"Role with ID {BORDER_OFFICER_ROLE} not found!")
            return

        check_channel = guild.get_channel(CHECK_CHANNEL_ID)  # Get the channel by ID
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
                self.msg = await check_channel.send(f":roundel2: The Aegean Federation immigration department is closing shop for the night, apologies for any inconveniences. :roundel2:")
        else:
            if self.msg:
                await self.msg.delete()
                self.msg = None
        print(f"{self.check_count} - check complete. {len(online_members)} Online border agents")
        

    @check_online_status.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()  # Wait until the bot is ready before starting the loop


def setup(bot):
    bot.add_cog(BorderOfficerMonitor(bot))
