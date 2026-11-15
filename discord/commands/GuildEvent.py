# GuildEvent.py
import datetime
import nextcord
from nextcord.ext import commands
from nextcord import Interaction, slash_command

from ..config import TESTING_GUILD_ID, LEADERSHIP_ROLE_ID, EVENTS_CHANNEL_ID, CIVIL_SERVANT_ROLE_ID, LOG_CHANNEL_ID

class GuildEvent(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Disabled for now: /create_weekend_events is wrong right now.
    # @slash_command(description="Create the standard set of three weekend events", guild_ids=[TESTING_GUILD_ID] if TESTING_GUILD_ID else None)
    # @commands.has_role(LEADERSHIP_ROLE_ID)
    # async def create_weekend_events(self, interaction: Interaction, friday_hour: int, saturday_hour: int, sunday_hour: int):
    #     # Check if required configuration is available
    #     if not EVENTS_CHANNEL_ID:
    #         await interaction.response.send_message("❌ Bot configuration error - events channel not configured!", ephemeral=True)
    #         return
            
    #     guild = interaction.guild
    #     next_friday, next_saturday, next_sunday = self.get_next_weekend(friday_hour, saturday_hour, sunday_hour)
        
    #     event_channel = guild.get_channel(EVENTS_CHANNEL_ID)
    #     if not event_channel:
    #         await interaction.response.send_message("❌ Could not find events channel in this server!", ephemeral=True)
    #         return
        
    #     await guild.create_scheduled_event(name="Friday", start_time=next_friday, description="Optional Event 1.", channel=event_channel, entity_type=nextcord.ScheduledEventEntityType.voice)
    #     await guild.create_scheduled_event(name="Saturday", start_time=next_saturday, description="Optional Event 2.", channel=event_channel, entity_type=nextcord.ScheduledEventEntityType.voice)
    #     await guild.create_scheduled_event(name="Sunday", start_time=next_sunday, description="Optional Event 3.", channel=event_channel, entity_type=nextcord.ScheduledEventEntityType.voice)
        
    #     await interaction.response.send_message("✅ Event series created successfully!", ephemeral=True)
        
    def get_next_weekend(self, fri: int, sat: int, sun: int):
        today = datetime.datetime.now()
        days_until_friday = (4 - today.weekday() + 7) % 7 or 7
        
        next_friday = today + datetime.timedelta(days=days_until_friday)
        next_friday = next_friday.replace(hour=fri, minute=0, second=0, microsecond=0)
        
        next_saturday = next_friday + datetime.timedelta(days=1)
        next_saturday = next_saturday.replace(hour=sat, minute=0, second=0, microsecond=0)
        
        next_sunday = next_friday + datetime.timedelta(days=2)
        next_sunday = next_sunday.replace(hour=sun, minute=0, second=0, microsecond=0)
        
        return next_friday, next_saturday, next_sunday

    @slash_command(description="Takes attendance of players present in discord vc", guild_ids=[TESTING_GUILD_ID] if TESTING_GUILD_ID else None)
    @commands.has_role(CIVIL_SERVANT_ROLE_ID)
    async def attendance(self, interaction: Interaction):
        # Check if required configuration is available
        if not LOG_CHANNEL_ID or not EVENTS_CHANNEL_ID:
            await interaction.response.send_message("❌ Bot configuration error - missing required channels!", ephemeral=True)
            return
            
        guild = interaction.guild

        log_text = guild.get_channel(LOG_CHANNEL_ID)
        event_voice = guild.get_channel(EVENTS_CHANNEL_ID)
        
        if not log_text or not event_voice:
            await interaction.response.send_message("❌ Could not find required channels in this server!", ephemeral=True)
            return
        
        # Get members in voice channel
        present = event_voice.members
        
        # convert the present list into a bullet point list
        present_list = "\n".join([f"- {member.mention}" for member in present])
        
        await log_text.send(f"**Attendance for {datetime.datetime.now().strftime('%A %B %d, %Y')}**\n{present_list}")
        await interaction.response.send_message("✅ Attendance Registered and Logged", ephemeral=True)
        
# Function to set up the Cog
def setup(bot):
    bot.add_cog(GuildEvent(bot))
