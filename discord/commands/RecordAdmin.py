"""Leadership commands to correct records: service events, ranks, member name/notes."""

from typing import Optional

import nextcord
from nextcord import Interaction, slash_command, SlashOption
from nextcord.ext import application_checks, commands

from database.rank_codes import rank_choices
from database.record_functions import get_service_event, update_service_event, delete_service_event, set_member_rank, update_member
from ..utils import RankManager
from ..utils.confirm import confirm
from ..utils.parse import parse_utc, valid_json_object, DATE_OR_DATETIME_FMT
from ..utils.rank_roles import sync_rank_roles
from ..config import TESTING_GUILD_ID, LEADERSHIP_ROLE_ID

GUILDS = [TESTING_GUILD_ID] if TESTING_GUILD_ID else None
DB_ERROR = "❌ Database error, nothing changed."


class RecordAdmin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.rank_manager = RankManager()

    @slash_command(description="Edit a service event (only the fields you give are changed)", guild_ids=GUILDS)
    @application_checks.has_role(LEADERSHIP_ROLE_ID)
    async def edit_service_event(
        self,
        interaction: Interaction,
        event_id: int = SlashOption(description="Event ID (shown in /service_record)", min_value=1),
        notes: Optional[str] = SlashOption(description="New notes", required=False),
        status: Optional[str] = SlashOption(description="New status", required=False),
        rank: Optional[str] = SlashOption(description="New rank", choices=rank_choices(), required=False),
        date: Optional[str] = SlashOption(description="New date, UTC: YYYY-MM-DD or YYYY-MM-DD HH:MM", required=False),
        details: Optional[str] = SlashOption(description="New details as a JSON object (replaces the old ones)", required=False),
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

    @slash_command(description="Delete a service event", guild_ids=GUILDS)
    @application_checks.has_role(LEADERSHIP_ROLE_ID)
    async def delete_service_event(
        self,
        interaction: Interaction,
        event_id: int = SlashOption(description="Event ID (shown in /service_record)", min_value=1),
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
        await interaction.edit_original_message(content=messages[result], embeds=[], view=None)

    @slash_command(description="Set a member's rank directly (no promotion rules)", guild_ids=GUILDS)
    @application_checks.has_role(LEADERSHIP_ROLE_ID)
    async def set_rank(
        self,
        interaction: Interaction,
        user: nextcord.Member = SlashOption(description="Member to change"),
        rank: str = SlashOption(description="Rank to set", choices=rank_choices()),
        reason: Optional[str] = SlashOption(description="Reason (optional)", required=False),
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

    @slash_command(description="Edit a member's name and/or notes", guild_ids=GUILDS)
    @application_checks.has_role(LEADERSHIP_ROLE_ID)
    async def edit_member(
        self,
        interaction: Interaction,
        user: nextcord.Member = SlashOption(description="Member to edit"),
        name: Optional[str] = SlashOption(description="New name", required=False),
        notes: Optional[str] = SlashOption(description="New notes (replaces the old ones)", required=False),
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


def setup(bot):
    bot.add_cog(RecordAdmin(bot))
