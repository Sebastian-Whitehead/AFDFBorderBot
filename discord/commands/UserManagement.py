"""
User Management Commands for AFDFBorderBot

This module contains commands for managing members, promotions, and user profiles.
Includes functionality for adding members, promoting users, and managing user data.
"""

import nextcord
from nextcord.ext import application_checks, commands
from nextcord import SlashOption
from typing import Optional
import logging

from database import create_user, get_user_info, merge_identities, merge_service_records, get_merge_preview, create_service_record, add_reprimand, add_service_event
from database.rank_codes import rank_choices
from ..utils import RankManager
from ..utils.steam import resolve_steam_id
from ..utils.confirm import confirm
from ..utils.parse import parse_utc, valid_json_object, DATE_OR_DATETIME_FMT
from ..config import TESTING_GUILD_ID as GUILD_ID, LEADERSHIP_ROLE_ID

logger = logging.getLogger(__name__)

_BOTH_RECORDS = ("❌ Both identities have a service record. Run `/merge_service_records` first, "
                 "then `/force_merge`.")

EVENT_TYPES = ['enlisted', 'rank_changed', 'discharged', 'reenlisted', 'retired', 'reprimand']  # service_events_type_check


class UserManagement(commands.Cog):
    """Cog for user management commands."""
    
    def __init__(self, bot):
        self.bot = bot
        self.rank_manager = RankManager()

    @nextcord.slash_command(
        name="add_member",
        description="Add a new member to the database",
        guild_ids=[GUILD_ID] if GUILD_ID else None
    )
    @application_checks.has_role(LEADERSHIP_ROLE_ID)
    async def add_member(
        self,
        interaction: nextcord.Interaction,
        user: nextcord.User = SlashOption(description="Member to add"),
        steam_id: Optional[str] = SlashOption(description="Member's SteamID64 or Steam profile URL (optional)", required=False),
        service_record: bool = SlashOption(description="Also create a military service record (default: no)", default=False),
        rank: Optional[str] = SlashOption(description="Starting rank (only with service_record)", required=False, choices=rank_choices()),
        notes: Optional[str] = SlashOption(description="Additional notes", required=False)
    ):
        """Add a player identity; a military service record only if service_record is true."""
        await interaction.response.defer(ephemeral=True)
        if rank and not service_record:
            await interaction.followup.send("❌ Rank only applies with `service_record: True`.", ephemeral=True)
            return
        rank = rank or "EN0"
        try:
            if steam_id:
                steam_id = await resolve_steam_id(steam_id)
                if steam_id is None:
                    await interaction.followup.send(
                        "❌ Steam ID must be numeric (SteamID64) or a Steam profile link that can be resolved.",
                        ephemeral=True
                    )
                    return

            name = user.global_name or user.name
            discord_id = str(user.id)

            # Check if user already exists
            existing_user = await get_user_info(discord_id)
            existing_user = existing_user or (await get_user_info(steam_id) if steam_id else None)

            if existing_user:
                await interaction.followup.send(
                    f"❌ User already exists in database: {existing_user['name']}",
                    ephemeral=True
                )
                return

            # Create new user
            new_user = await create_user(
                name=name,
                steam_id=steam_id,
                discord_id=discord_id,
                rank=rank,
                notes=notes,
                service_record=service_record
            )
            if new_user is None:
                await interaction.followup.send(
                    "❌ Failed to add member (already exists or invalid data).",
                    ephemeral=True
                )
                return

            embed = nextcord.Embed(
                title="✅ Member Added Successfully",
                color=0x00ff00,
                description=f"Added **{name}** to the database"
            )
            embed.add_field(name="Steam ID", value=steam_id or "Not set", inline=True)
            embed.add_field(name="Discord", value=user.mention, inline=True)
            if service_record:
                embed.add_field(name="Rank", value=self.rank_manager.rank_text(rank), inline=True)
            
            if notes:
                embed.add_field(name="Notes", value=notes, inline=False)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error adding member: {e}")
            await interaction.followup.send(
                f"❌ Failed to add member: {str(e)}", 
                ephemeral=True
            )

    @nextcord.slash_command(
        name="create_service_record",
        description="Create a service record for an existing player",
        guild_ids=[GUILD_ID] if GUILD_ID else None
    )
    @application_checks.has_role(LEADERSHIP_ROLE_ID)
    async def create_service_record_cmd(
        self,
        interaction: nextcord.Interaction,
        user: nextcord.User = SlashOption(description="Player to create the record for"),
        rank: str = SlashOption(description="Starting rank", choices=rank_choices())
    ):
        """Create just the service record (no enlistment event, no Discord role changes)."""
        await interaction.response.defer(ephemeral=True)
        result = await create_service_record(str(user.id), rank)
        messages = {
            "created": f"✅ Service record created for {user.mention} at {self.rank_manager.rank_text(rank)}.",
            "already_exists": f"❌ {user.mention} already has a service record.",
            "no_identity": f"❌ {user.mention} has no player record yet. Approve them (or /add_member) first.",
            "error": "❌ Database error, nothing changed.",
        }
        await interaction.followup.send(messages[result], ephemeral=result != "created")

    @nextcord.slash_command(
        name="add_steam",
        description="Add a Steam ID to an existing member",
        guild_ids=[GUILD_ID] if GUILD_ID else None
    )
    @application_checks.has_role(LEADERSHIP_ROLE_ID)
    async def add_steam(
        self,
        interaction: nextcord.Interaction,
        user: nextcord.User = SlashOption(description="Member to update"),
        steam_url: str = SlashOption(description="Steam profile URL (/profiles/ or /id/) or SteamID64")
    ):
        """Attach a Steam ID to an existing player identity."""
        await interaction.response.defer(ephemeral=True)
        steam_id = await resolve_steam_id(steam_url)
        if steam_id is None:
            await interaction.followup.send(
                "❌ Couldn't get a Steam ID from that. Use a steamcommunity.com profile link "
                "(public profile) or the SteamID64.",
                ephemeral=True
            )
            return
        result = await merge_identities(str(user.id), steam_id)
        messages = {
            "linked": f"✅ Steam ID `{steam_id}` linked to {user.mention}.",
            "merged": f"✅ Steam ID `{steam_id}` merged into {user.mention}'s player record (bank accounts moved over).",
            "already_linked": f"ℹ️ {user.mention} already has that Steam ID.",
            "no_identity": f"❌ {user.mention} has no player record yet. Approve them (or /add_member) first.",
            "different_steam": f"❌ {user.mention} already has a different Steam ID. Not overwritten (see /force_merge).",
            "steam_linked_to_other_discord": "❌ That Steam ID already belongs to another Discord user (see /force_merge).",
            "service_record_conflict": _BOTH_RECORDS,
            "error": "❌ Database error, nothing changed.",
        }
        await interaction.followup.send(messages[result], ephemeral=result not in ("linked", "merged", "already_linked"))

    @staticmethod
    def _side(r) -> str:
        if r is None:
            return "none (no identity)"
        return (f"id {r.id}, alias {r.alias or '-'}, Steam {r.steam_id or '-'}, Discord {r.discord_id or '-'}, "
                f"{f'rank {r.current_rank} / {r.service_status}' if r.sr_id else 'no service record'}")

    @staticmethod
    async def _confirm_merge(interaction, user, steam_url, embed_file, check):
        """Resolve the Steam ID, load both sides, run check(preview) -> error text or None, then ask to confirm.
        Returns (steam_id, preview) once approved, else None (the user has been told why)."""
        await interaction.response.defer(ephemeral=True)
        steam_id = await resolve_steam_id(steam_url)
        if steam_id is None:
            await interaction.followup.send("❌ Couldn't get a Steam ID from that. Use a steamcommunity.com profile "
                                            "link (public profile) or the SteamID64.", ephemeral=True)
            return None
        prev = await get_merge_preview(str(user.id), steam_id)
        err = "❌ Database error, nothing changed." if prev is None else check(prev)
        if err:
            await interaction.followup.send(err, ephemeral=True)
            return None
        st, dc = prev["steam"], prev["discord"]
        side = UserManagement._side
        old_rank = dc.current_rank if dc and dc.sr_id else "-"
        repl = {"{steam_id}": steam_id, "{member}": user.mention, "{steam_side}": side(st), "{discord_side}": side(dc),
                "{survivor}": prev["survivor"],
                "{new_rank}": st.current_rank if st and st.sr_id else "-", "{new_status}": st.service_status if st and st.sr_id else "-",
                "{old_rank}": old_rank, "{old_status}": dc.service_status if dc and dc.sr_id else "-"}
        if not await confirm(interaction, embed_file, repl, declined="↩️ Nothing changed.", timed_out="⌛ Timed out, nothing changed."):
            return None
        return steam_id, prev

    @nextcord.slash_command(
        name="force_merge",
        description="Force-merge a member's identity with a Steam identity (overwrites existing IDs)",
        guild_ids=[GUILD_ID] if GUILD_ID else None
    )
    @application_checks.has_role(LEADERSHIP_ROLE_ID)
    async def force_merge(
        self,
        interaction: nextcord.Interaction,
        user: nextcord.User = SlashOption(description="Member to merge"),
        steam_url: str = SlashOption(description="Steam profile URL (/profiles/ or /id/) or SteamID64")
    ):
        """Merge the Discord and Steam identities, ignoring IDs either side already has."""
        got = await self._confirm_merge(
            interaction, user, steam_url, "force_merge_warning.json",
            lambda p: None if p["steam"] or p["discord"] else f"❌ Neither {user.mention} nor that Steam ID has a player record.")
        if got is None:
            return
        steam_id, _ = got
        result = await merge_identities(str(user.id), steam_id, force=True)
        messages = {
            "merged": f"✅ Identities merged. {user.mention} now has Steam ID `{steam_id}`.",
            "linked": f"✅ Steam ID `{steam_id}` linked to {user.mention}.",
            "already_linked": f"ℹ️ {user.mention} already has that Steam ID.",
            "no_identity": f"❌ Neither {user.mention} nor that Steam ID has a player record.",
            "service_record_conflict": _BOTH_RECORDS,
            "error": "❌ Database error, nothing changed.",
        }
        await interaction.edit_original_message(content=messages.get(result, "❌ Database error, nothing changed."), embeds=[], view=None)

    @nextcord.slash_command(
        name="merge_service_records",
        description="Merge the service record on a Steam ID into a member's record (Steam wins)",
        guild_ids=[GUILD_ID] if GUILD_ID else None
    )
    @application_checks.has_role(LEADERSHIP_ROLE_ID)
    async def merge_service_records_cmd(
        self,
        interaction: nextcord.Interaction,
        user: nextcord.User = SlashOption(description="Member whose record is kept"),
        steam_url: str = SlashOption(description="Steam profile URL (/profiles/ or /id/) or SteamID64")
    ):
        """Merge the Steam identity's service record into the member's; rank and status come from Steam."""
        def check(p):
            if not p["steam"] or not p["discord"]:
                return f"❌ Both {user.mention} and that Steam ID need a player record first."
            if not p["steam"].sr_id or not p["discord"].sr_id:
                return "❌ Both sides need a service record to merge."
            return None
        got = await self._confirm_merge(interaction, user, steam_url, "merge_service_records_warning.json", check)
        if got is None:
            return
        _, prev = got
        result = await merge_service_records(str(user.id), got[0])
        messages = {
            "merged": (f"✅ Service records merged. {user.mention} is now **{prev['steam'].current_rank}** / "
                       f"{prev['steam'].service_status} (was {prev['discord'].current_rank} / {prev['discord'].service_status}). "
                       "Discord rank roles were not changed; use `/set_rank` to fix them."),
            "no_identity": f"❌ Both {user.mention} and that Steam ID need a player record first.",
            "no_record": "❌ Both sides need a service record to merge.",
            "different_organization": "❌ The two records belong to different organizations.",
        }
        await interaction.edit_original_message(content=messages.get(result, "❌ Database error, nothing changed."), embeds=[], view=None)

    @nextcord.slash_command(
        name="reprimand",
        description="Log a reprimand on a member's service record",
        guild_ids=[GUILD_ID] if GUILD_ID else None
    )
    @application_checks.has_role(LEADERSHIP_ROLE_ID)
    async def reprimand(
        self,
        interaction: nextcord.Interaction,
        user: nextcord.User = SlashOption(description="Member to reprimand"),
        reason: str = SlashOption(description="Reason for the reprimand")
    ):
        """Add a reprimand event to the member's service record."""
        await interaction.response.defer(ephemeral=True)
        result = await add_reprimand(str(user.id), reason, str(interaction.user.id))
        messages = {
            "recorded": f"⚠️ Reprimand logged for {user.mention}: {reason}",
            "no_record": f"❌ {user.mention} has no service record, so nothing was logged.",
            "error": "❌ Database error, nothing changed.",
        }
        await interaction.followup.send(messages[result], ephemeral=result != "recorded")

    @nextcord.slash_command(
        name="create_service_event",
        description="Add an event to a member's service record",
        guild_ids=[GUILD_ID] if GUILD_ID else None
    )
    @application_checks.has_role(LEADERSHIP_ROLE_ID)
    async def create_service_event(
        self,
        interaction: nextcord.Interaction,
        user: nextcord.User = SlashOption(description="Member the event belongs to"),
        event_type: str = SlashOption(name="type", description="Event type", choices=EVENT_TYPES),
        date: str = SlashOption(description="When it happened, UTC: YYYY-MM-DD or YYYY-MM-DD HH:MM"),
        rank: Optional[str] = SlashOption(description="Rank at the time (optional)", choices=rank_choices(), required=False),
        status: Optional[str] = SlashOption(description="Status (optional)", required=False),
        notes: Optional[str] = SlashOption(description="Notes (optional)", required=False),
        details: Optional[str] = SlashOption(description="Extra details as a JSON object (optional)", required=False),
    ):
        """Insert a row in military.service_events."""
        await interaction.response.defer(ephemeral=True)
        when = parse_utc(date, DATE_OR_DATETIME_FMT)
        if when is None:
            await interaction.followup.send("❌ Date must look like `2026-11-20` or `2026-11-20 19:00` (UTC).")
            return
        if details and not valid_json_object(details):
            await interaction.followup.send("❌ Details must be a JSON object, e.g. `{\"key\": \"value\"}`.")
            return
        result = await add_service_event(str(user.id), event_type, when, rank, status, notes, details)
        messages = {
            "created": f"✅ `{event_type}` event added to {user.mention}'s service record ({date} UTC).",
            "no_record": f"❌ {user.mention} has no service record, so nothing was logged.",
            "error": "❌ Database error, nothing changed.",
        }
        await interaction.followup.send(messages[result])


def setup(bot):
    """Add the UserManagement cog to the bot."""
    bot.add_cog(UserManagement(bot))