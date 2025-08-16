# GuildEvent.py
import datetime
import nextcord
from nextcord.ext import commands
from nextcord import Interaction, slash_command

from src.config import IDS, ROLES, CHANNELS
LEADERSHIP_ROLE = ROLES['leadership']
EVENT_CHANNEL = CHANNELS['events_vc']

class GuildEvent(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(description="Create the standard set of three weekend events", guild_ids=[IDS['testing_guild']])
    @commands.has_role(LEADERSHIP_ROLE)
    async def create_weekend_events(self, interaction: Interaction, friday_hour: int, saturday_hour: int, sunday_hour: int):
        guild = interaction.guild
        next_friday, next_saturday, next_sunday = self.get_next_weekend(friday_hour, saturday_hour, sunday_hour)
        
        event_channel = guild.get_channel(EVENT_CHANNEL)
        
        await guild.create_scheduled_event(name="Friday", start_time=next_friday, description="Optional Event 1.", channel=event_channel, entity_type=nextcord.ScheduledEventEntityType.voice)
        await guild.create_scheduled_event(name="Saturday", start_time=next_saturday, description="Optional Event 2.", channel=event_channel, entity_type=nextcord.ScheduledEventEntityType.voice)
        await guild.create_scheduled_event(name="Sunday", start_time=next_sunday, description="Optional Event 3.", channel=event_channel, entity_type=nextcord.ScheduledEventEntityType.voice)
        
        await interaction.response.send_message("Event series created successfully!", ephemeral=True)
        
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

    @slash_command(description="Takes attendance of players present in discord vc", guild_ids=[IDS['testing_guild']])
    @commands.has_role(IDS['roles']['civil_servant'])
    async def attendance(self, interaction: Interaction):
        guild = interaction.guild

        log_text = guild.get_channel(IDS['channels']['log_txt'])
        event_voice = guild.get_channel(EVENT_CHANNEL)
        
        # Get members in voice channel
        present = event_voice.members
        
        # convert the present list into a bullet point list
        present_list = "\n".join([f"- {member.mention}" for member in present])
        
        await log_text.send(f"**Attendance for {datetime.datetime.now().strftime('%A %B %d, %Y')}**\n{present_list}")
        await interaction.response.send_message("Attendance Registered and Logged", ephemeral=True)
        
# Function to set up the Cog
def setup(bot):
    bot.add_cog(GuildEvent(bot))
