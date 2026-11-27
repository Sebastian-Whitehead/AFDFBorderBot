"""Leadership commands to correct records: service events, ranks, member name/notes."""

from typing import Optional

import discord
from discord import Interaction, app_commands
from discord.ext import commands

from database.rank_codes import rank_choices
from database.record_functions import get_service_event, update_service_event, delete_service_event, set_member_rank, update_member
from ..utils import RankManager
from ..utils.choices import to_choices
from ..utils.confirm import confirm
from ..utils.parse import parse_utc, valid_json_object, DATE_OR_DATETIME_FMT
from ..utils.rank_roles import sync_rank_roles
from ..config import LEADERSHIP_ROLE_ID

DB_ERROR = "❌ Database error, nothing changed."


class RecordAdmin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.rank_manager = RankManager()

    @app_commands.command(description="Edit a service event (only the fields you give are changed)")
    @app_commands.checks.has_role(LEADERSHIP_ROLE_ID)
    @app_commands.describe(
        event_id="Event ID (shown in /service_record)",
        notes="New notes",
        status="New status",
        rank="New rank",
        date="New date, UTC: YYYY-MM-DD or YYYY-MM-DD HH:MM",
        details="New details as a JSON object (replaces the old ones)",
    )
    @app_commands.choices(rank=to_choices(rank_choices()))
    async def edit_service_event(
        self,
        interaction: Interaction,
        event_id: app_commands.Range[int, 1],
        notes: Optional[str] = None,
        status: Optional[str] = None,
        rank: Optional[str] = None,
        date: Optional[str] = None,
        details: Optional[str] = None,
    ):
        await interaction.response.defer(ephemeral=True)
        when = parse_utc(date, DATE_OR_DATETIME_FMT) if date else None
        if date and when is None:
            await interaction.followup.send("❌ Date must look like `2026-11-20` or `2026-11-20 19:00` (UTC).")
            return
        if details and not valid_json_object(details):
            await interaction.followup.send("❌ Details must be a JSON object, e.g. `{\"key\": \"value\"}`.")
            return
        changes = {"notes": notes, "status": status, "rank": rank, "occured_at": when, "details": details or None}
        result = await update_service_event(event_id, **changes)
        messages = {
            "updated": f"✅ Event {event_id} updated: " + ", ".join(k for k, v in changes.items() if v is not None) + ".",
            "no_changes": "ℹ️ Nothing to change, give at least one field.",
            "not_found": f"❌ No service event with id {event_id}.",
            "error": DB_ERROR,
        }
        await interaction.followup.send(messages[result])

    @app_commands.command(description="Delete a service event")
    @app_commands.checks.has_role(LEADERSHIP_ROLE_ID)
    @app_commands.describe(event_id="Event ID (shown in /service_record)")
    async def delete_service_event(
        self,
        interaction: Interaction,
        event_id: app_commands.Range[int, 1],
    ):
        await interaction.response.defer(ephemeral=True)
        status, event = await get_service_event(event_id)
        if status != "ok":
            await interaction.followup.send(f"❌ No service event with id {event_id}." if status == "not_found" else DB_ERROR)
            return
        if not await confirm(interaction, "delete_service_event_warning.json",
                             {"{event_id}": str(event_id), "{event_type}": event["event_type"],
                              "{date}": f"{event['occured_at']:%Y-%m-%d %H:%M} UTC"},
                             declined="↩️ Event not deleted.", timed_out="⌛ Timed out, event not deleted."):
            return
        result = await delete_service_event(event_id)
        messages = {
            "deleted": f"✅ Event {event_id} (`{event['event_type']}`) deleted.",
            "not_found": f"❌ No service event with id {event_id}.",
            "error": DB_ERROR,
        }
        await interaction.edit_original_response(content=messages[result], embeds=[], view=None)

    @app_commands.command(description="Set a member's rank directly (no promotion rules)")
    @app_commands.checks.has_role(LEADERSHIP_ROLE_ID)
    @app_commands.describe(user="Member to change", rank="Rank to set", reason="Reason (optional)")
    @app_commands.choices(rank=to_choices(rank_choices()))
    async def set_rank(
        self,
        interaction: Interaction,
        user: discord.Member,
        rank: str,
        reason: Optional[str] = None,
    ):
        await interaction.response.defer(ephemeral=True)
        name = self.rank_manager.get_rank(rank)["name"]
        status, old_rank = await set_member_rank(str(user.id), rank, reason or f"Rank set to {name}")
        if status != "ok":
            await interaction.followup.send({
                "no_record": f"❌ {user.mention} has no service record, nothing changed.",
                "same_rank": f"ℹ️ {user.mention} is already {name} ({rank}).",
                "error": DB_ERROR,
            }[status])
            return
        try:
            await sync_rank_roles(interaction.guild, user, old_rank, rank)
        except Exception as e:
            await interaction.followup.send(
                f"⚠️ {user.mention} is now {name} ({rank}) in the database, but the Discord roles could not be updated: {e}")
            return
        await interaction.followup.send(f"✅ {user.mention} set from {old_rank} to {name} ({rank}).")

    @app_commands.command(description="Edit a member's name and/or notes")
    @app_commands.checks.has_role(LEADERSHIP_ROLE_ID)
    @app_commands.describe(user="Member to edit", name="New name", notes="New notes (replaces the old ones)")
    async def edit_member(
        self,
        interaction: Interaction,
        user: discord.Member,
        name: Optional[str] = None,
        notes: Optional[str] = None,
    ):
        await interaction.response.defer(ephemeral=True)
        if name is not None and not name.strip():
            await interaction.followup.send("❌ Name can't be blank.")
            return
        result = await update_member(str(user.id), name and name.strip(), notes)
        messages = {
            "updated": f"✅ {user.mention} updated: " + ", ".join(k for k, v in (("name", name), ("notes", notes)) if v is not None) + ".",
            "no_changes": "ℹ️ Nothing to change, give a name or notes.",
            "no_identity": f"❌ {user.mention} has no player record.",
            "error": DB_ERROR,
        }
        await interaction.followup.send(messages[result])


async def setup(bot):
    await bot.add_cog(RecordAdmin(bot))
