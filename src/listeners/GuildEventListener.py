import nextcord
from nextcord.ext import commands
from nextcord import Interaction, Member, NotFound, slash_command

from src.config import MAIN_CHANNEL_ID, ENABLE_EVENT_START


class GuildEventListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_event_start(self, event: nextcord.ScheduledEvent):
        # Check if event listening is enabled
        if not ENABLE_EVENT_START:
            return
            
        # Check if main channel is configured
        if not MAIN_CHANNEL_ID:
            return
            
        guild = event.guild
        main_channel = guild.get_channel(MAIN_CHANNEL_ID)
        
        if not main_channel:
            return

        members = await event.fetch_users()        
        await main_channel.send(f"{event.name} IS STARTING!: {', '.join([member.mention for member in members])}")
        
# Function to set up the Cog
def setup(bot):
    bot.add_cog(GuildEventListener(bot))