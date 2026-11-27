"""Session commands: create, end, edit and list rows of military.sessions."""

from typing import Optional

from discord import Interaction, app_commands
from discord.ext import commands

from database.session_functions import create_session as create_session_row, end_latest_session, get_session_for_delete, delete_session as delete_session_row, list_sessions, update_session, PAGE_SIZE
from ..utils import load_embeds
from ..utils.confirm import confirm
from ..utils.parse import parse_utc
from ..config import CIVIL_SERVANT_ROLE_ID


class Session(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="create_session", description="Create a session record")
    @app_commands.checks.has_role(CIVIL_SERVANT_ROLE_ID)
    @app_commands.describe(name="Session name", operation="Operation name", description="Description", start="Start time in UTC, YYYY-MM-DD HH:MM (default: now)", external_event_id="Discord scheduled event ID to link (optional)", timeline="Timeline (default A)")
    async def create_session(
        self,
        interaction: Interaction,
        name: str,
        operation: Optional[str] = None,
        description: Optional[str] = None,
        start: Optional[str] = None,
        external_event_id: Optional[str] = None,
        timeline: str = "A",
    ):
        """Create a row in military.sessions."""
        await interaction.response.defer(ephemeral=True)
        if not name.strip():
            await interaction.followup.send("❌ Session name can't be blank.")
            return
        start_at = None
        if start:
            start_at = parse_utc(start)
            if start_at is None:
                await interaction.followup.send("❌ Start must look like `2026-11-20 19:00` (UTC).")
                return
        new_id = await create_session_row(name.strip(), operation, description, start_at, external_event_id, timeline.strip() or "A")
        if new_id is None:
            await interaction.followup.send("❌ Database error, nothing changed.")
            return
        await interaction.followup.send(f"✅ Session **{name.strip()}** created (id {new_id}).")

    @app_commands.command(name="end_session", description="End the most recently started open session")
    @app_commands.checks.has_role(CIVIL_SERVANT_ROLE_ID)
    @app_commands.describe(end="End time in UTC, YYYY-MM-DD HH:MM (default: now)")
    async def end_session(
        self,
        interaction: Interaction,
        end: Optional[str] = None,
    ):
        """Set end_at on the open session with the latest start time."""
        await interaction.response.defer(ephemeral=True)
        end_at = None
        if end:
            end_at = parse_utc(end)
            if end_at is None:
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
        await interaction.edit_original_response(content=messages[status](), embeds=[], view=None)

    @app_commands.command(name="session_list", description="List sessions, 10 per page (newest first)")
    @app_commands.describe(timeline="Timeline (default A)", page="Page number (default 1)")
    async def session_list(
        self,
        interaction: Interaction,
        timeline: str = "A",
        page: app_commands.Range[int, 1, None] = 1,
    ):
        await interaction.response.defer(ephemeral=True)
        result = await list_sessions(timeline.strip(), page)
        if result is None:
            await interaction.followup.send("❌ Database error.")
            return
        rows, total = result
        if not rows:
            await interaction.followup.send(f"No sessions on page {page} for timeline **{timeline}** ({total} total).")
            return
        fmt = "%Y-%m-%d %H:%M"  # DB times are UTC
        # plain markdown list (no code block) so long lines wrap cleanly
        lines = [f"{(page - 1) * PAGE_SIZE + n:>2}. **{r['session_name'][:40]}**" + (f" ({r['operation'][:40]})" if r["operation"] else "")
                 + f"\n↳ {r['start_at'].strftime(fmt)} -> " + (r["end_at"].strftime(fmt) if r["end_at"] else "open")
                 for n, r in enumerate(rows, 1)]
        pages = -(-total // PAGE_SIZE)
        await interaction.followup.send(embeds=load_embeds("session_list.json", {
            "{timeline}": timeline, "{table}": "\n".join(lines), "{page}": str(page), "{pages}": str(pages), "{total}": str(total)}))

    @app_commands.command(name="edit_session", description="Edit an existing session (only the fields you give are changed)")
    @app_commands.checks.has_role(CIVIL_SERVANT_ROLE_ID)
    @app_commands.describe(session_id="Session ID (see /session_list)", name="New name", operation="New operation", description="New description", timeline="New timeline", start="New start, UTC YYYY-MM-DD HH:MM", end="New end, UTC YYYY-MM-DD HH:MM")
    async def edit_session(
        self,
        interaction: Interaction,
        session_id: app_commands.Range[int, 1, None],
        name: Optional[str] = None,
        operation: Optional[str] = None,
        description: Optional[str] = None,
        timeline: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ):
        await interaction.response.defer(ephemeral=True)
        if name is not None and not name.strip():
            await interaction.followup.send("❌ Session name can't be blank.")
            return
        times = {}
        for key, value in (("start_at", start), ("end_at", end)):
            if value:
                times[key] = parse_utc(value)
                if times[key] is None:
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

    @app_commands.command(name="delete_session", description="Permanently delete a session that has no attendance")
    @app_commands.checks.has_role(CIVIL_SERVANT_ROLE_ID)
    @app_commands.describe(session_id="Session ID (see /session_list)")
    async def delete_session(
        self,
        interaction: Interaction,
        session_id: app_commands.Range[int, 1, None],
    ):
        await interaction.response.defer(ephemeral=True)
        status, row = await get_session_for_delete(session_id)
        if status == "not_found":
            await interaction.followup.send(f"❌ No session with id {session_id}.")
            return
        if status == "error":
            await interaction.followup.send("❌ Database error, nothing changed.")
            return
        if row["attendance_count"]:
            await interaction.followup.send(
                f"❌ Session **{row['session_name']}** (id {session_id}) has {row['attendance_count']} attendance row(s) "
                "and can't be deleted. Nothing changed.")
            return
        if not await confirm(interaction, "delete_session_warning.json",
                             {"{session_name}": row["session_name"], "{session_id}": str(session_id),
                              "{attendance_count}": str(row["attendance_count"])},
                             declined="↩️ Session not deleted.", timed_out="⌛ Timed out, session not deleted."):
            return
        messages = {
            "deleted": f"✅ Session **{row['session_name']}** (id {session_id}) deleted.",
            "not_found": f"❌ No session with id {session_id}.",
            "blocked": "❌ Attendance was recorded for this session meanwhile, so it can't be deleted. Nothing changed.",
            "error": "❌ Database error, nothing changed.",
        }
        await interaction.edit_original_response(content=messages[await delete_session_row(session_id)], embeds=[], view=None)


async def setup(bot):
    await bot.add_cog(Session(bot))
