# GuildEvent.py
import datetime
from typing import Optional
from nextcord.ext import commands
from nextcord import Interaction, slash_command, SlashOption

from database import create_session as create_session_row, end_latest_session
from database.attendance_functions import list_sessions, update_session, PAGE_SIZE
from ..utils import load_embeds
from ..utils.confirm import confirm

from ..config import TESTING_GUILD_ID, EVENTS_CHANNEL_ID, CIVIL_SERVANT_ROLE_ID, LOG_CHANNEL_ID

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
        
    @slash_command(description="Create a session record", guild_ids=[TESTING_GUILD_ID] if TESTING_GUILD_ID else None)
    @commands.has_role(CIVIL_SERVANT_ROLE_ID)
    async def create_session(
        self,
        interaction: Interaction,
        name: str = SlashOption(description="Session name"),
        operation: Optional[str] = SlashOption(description="Operation name", required=False),
        description: Optional[str] = SlashOption(description="Description", required=False),
        start: Optional[str] = SlashOption(description="Start time in UTC, YYYY-MM-DD HH:MM (default: now)", required=False),
        external_event_id: Optional[str] = SlashOption(description="Discord scheduled event ID to link (optional)", required=False),
        timeline: str = SlashOption(description="Timeline (default A)", default="A"),
    ):
        """Create a row in military.sessions."""
        await interaction.response.defer(ephemeral=True)
        if not name.strip():
            await interaction.followup.send("❌ Session name can't be blank.")
            return
        start_at = None
        if start:
            try:
                start_at = datetime.datetime.strptime(start, "%Y-%m-%d %H:%M").replace(tzinfo=datetime.timezone.utc)
            except ValueError:
                await interaction.followup.send("❌ Start must look like `2026-11-20 19:00` (UTC).")
                return
        new_id = await create_session_row(name.strip(), operation, description, start_at, external_event_id, timeline.strip() or "A")
        if new_id is None:
            await interaction.followup.send("❌ Database error, nothing changed.")
            return
        await interaction.followup.send(f"✅ Session **{name.strip()}** created (id {new_id}).")

    @slash_command(description="End the most recently started open session", guild_ids=[TESTING_GUILD_ID] if TESTING_GUILD_ID else None)
    @commands.has_role(CIVIL_SERVANT_ROLE_ID)
    async def end_session(
        self,
        interaction: Interaction,
        end: Optional[str] = SlashOption(description="End time in UTC, YYYY-MM-DD HH:MM (default: now)", required=False),
    ):
        """Set end_at on the open session with the latest start time."""
        await interaction.response.defer(ephemeral=True)
        end_at = None
        if end:
            try:
                end_at = datetime.datetime.strptime(end, "%Y-%m-%d %H:%M").replace(tzinfo=datetime.timezone.utc)
            except ValueError:
                await interaction.followup.send("❌ End must look like `2026-11-20 21:00` (UTC).")
                return
        if not await confirm(interaction, "end_session_warning.json",
                             declined="↩️ Session not ended.", timed_out="⌛ Timed out, session not ended."):
            return
        status, row = await end_latest_session(end_at)
        messages = {
            "ended": lambda: f"✅ Session **{row['session_name']}** (id {row['id']}) ended at {row['end_at']:%Y-%m-%d %H:%M} UTC.",
            "none_open": lambda: "❌ No open session to end.",
            "before_start": lambda: f"❌ End time is before **{row['session_name']}** started ({row['start_at']:%Y-%m-%d %H:%M} UTC).",
            "error": lambda: "❌ Database error, nothing changed.",
        }
        await interaction.edit_original_message(content=messages[status](), embeds=[], view=None)

    @slash_command(description="List sessions, 10 per page (newest first)", guild_ids=[TESTING_GUILD_ID] if TESTING_GUILD_ID else None)
    async def session_list(
        self,
        interaction: Interaction,
        timeline: str = SlashOption(description="Timeline (default A)", default="A"),
        page: int = SlashOption(description="Page number (default 1)", default=1, min_value=1),
    ):
        await interaction.response.defer()
        result = await list_sessions(timeline.strip(), page)
        if result is None:
            await interaction.followup.send("❌ Database error.")
            return
        rows, total = result
        if not rows:
            await interaction.followup.send(f"No sessions on page {page} for timeline **{timeline}** ({total} total).")
            return
        fmt = "%Y-%m-%d %H:%M"
        table = [("#", "ID", "Timeline", "Name", "Operation", "Start", "End")] + [
            (str((page - 1) * PAGE_SIZE + n), str(r["id"]), r["timeline"], r["session_name"][:24], (r["operation"] or "-")[:24],
             r["start_at"].strftime(fmt), r["end_at"].strftime(fmt) if r["end_at"] else "open")
            for n, r in enumerate(rows, 1)]
        w = [max(len(r[i]) for r in table) for i in range(7)]
        lines = ["| " + " | ".join(c.ljust(w[i]) for i, c in enumerate(r)) + " |" for r in table]
        lines.insert(1, "|" + "|".join("-" * (n + 2) for n in w) + "|")
        pages = -(-total // PAGE_SIZE)
        await interaction.followup.send(embeds=load_embeds("session_list.json", {
            "{timeline}": timeline, "{table}": "\n".join(lines), "{page}": str(page), "{pages}": str(pages), "{total}": str(total)}))

    @slash_command(description="Edit an existing session (only the fields you give are changed)", guild_ids=[TESTING_GUILD_ID] if TESTING_GUILD_ID else None)
    @commands.has_role(CIVIL_SERVANT_ROLE_ID)
    async def edit_session(
        self,
        interaction: Interaction,
        session_id: int = SlashOption(description="Session ID (see /session_list)", min_value=1),
        name: Optional[str] = SlashOption(description="New name", required=False),
        operation: Optional[str] = SlashOption(description="New operation", required=False),
        description: Optional[str] = SlashOption(description="New description", required=False),
        timeline: Optional[str] = SlashOption(description="New timeline", required=False),
        start: Optional[str] = SlashOption(description="New start, UTC YYYY-MM-DD HH:MM", required=False),
        end: Optional[str] = SlashOption(description="New end, UTC YYYY-MM-DD HH:MM", required=False),
    ):
        await interaction.response.defer(ephemeral=True)
        if name is not None and not name.strip():
            await interaction.followup.send("❌ Session name can't be blank.")
            return
        times = {}
        for key, value in (("start_at", start), ("end_at", end)):
            if value:
                try:
                    times[key] = datetime.datetime.strptime(value, "%Y-%m-%d %H:%M").replace(tzinfo=datetime.timezone.utc)
                except ValueError:
                    await interaction.followup.send(f"❌ {key[:-3].capitalize()} must look like `2026-11-20 19:00` (UTC).")
                    return
        changes = {"session_name": name and name.strip(), "operation": operation, "description": description,
                   "timeline": timeline and timeline.strip() or None, **times}
        status, row = await update_session(session_id, **changes)
        messages = {
            "updated": lambda: f"✅ Session **{row['session_name']}** (id {session_id}) updated: "
                               + ", ".join(k for k, v in changes.items() if v is not None) + ".",
            "no_changes": lambda: "ℹ️ Nothing to change, give at least one field.",
            "not_found": lambda: f"❌ No session with id {session_id}.",
            "bad_dates": lambda: "❌ End can't be before the start. Nothing changed.",
            "error": lambda: "❌ Database error, nothing changed.",
        }
        await interaction.followup.send(messages[status]())

# Function to set up the Cog
def setup(bot):
    bot.add_cog(GuildEvent(bot))
