"""
User Management Commands for AFDFBorderBot

This module contains commands for managing members, promotions, and user profiles.
Includes functionality for adding members, promoting users, and managing user data.
"""

import nextcord
from nextcord.ext import commands
from nextcord import SlashOption
from typing import Optional
import datetime
import json
import logging

from database import create_user, get_user_info, modify_user, set_steam_id, create_service_record, add_reprimand, add_service_event
from database.rank_codes import rank_choices, rank_index
from ..utils import RankManager
from ..utils.steam import resolve_steam_id
from ..config import TESTING_GUILD_ID as GUILD_ID

logger = logging.getLogger(__name__)

EVENT_TYPES = ['enlisted', 'rank_changed', 'discharged', 'reenlisted', 'retired', 'reprimand']  # service_events_type_check


class UserManagement(commands.Cog):
    """Cog for user management commands."""
    
    def __init__(self, bot):
        self.bot = bot
        self.rank_manager = RankManager()

    def _rank_text(self, code: str) -> str:
        info = self.rank_manager.get_rank(code)
        return f"{info['name']} ({info['code']})"

    @nextcord.slash_command(
        name="add_member",
        description="Add a new member to the database",
        guild_ids=[GUILD_ID] if GUILD_ID else None
    )
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
        await interaction.response.defer()
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
                embed.add_field(name="Rank", value=self._rank_text(rank), inline=True)
            
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
    async def create_service_record_cmd(
        self,
        interaction: nextcord.Interaction,
        user: nextcord.User = SlashOption(description="Player to create the record for"),
        rank: str = SlashOption(description="Starting rank", choices=rank_choices())
    ):
        """Create just the service record (no enlistment event, no Discord role changes)."""
        await interaction.response.defer()
        result = await create_service_record(str(user.id), rank)
        messages = {
            "created": f"✅ Service record created for {user.mention} at {self._rank_text(rank)}.",
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
    async def add_steam(
        self,
        interaction: nextcord.Interaction,
        user: nextcord.User = SlashOption(description="Member to update"),
        steam_url: str = SlashOption(description="Steam profile URL (/profiles/ or /id/) or SteamID64")
    ):
        """Attach a Steam ID to an existing player identity."""
        await interaction.response.defer()
        steam_id = await resolve_steam_id(steam_url)
        if steam_id is None:
            await interaction.followup.send(
                "❌ Couldn't get a Steam ID from that. Use a steamcommunity.com profile link "
                "(public profile) or the SteamID64.",
                ephemeral=True
            )
            return
        result = await set_steam_id(str(user.id), steam_id)
        messages = {
            "updated": f"✅ Steam ID `{steam_id}` added to {user.mention}.",
            "already_set": f"ℹ️ {user.mention} already has that Steam ID.",
            "no_identity": f"❌ {user.mention} has no player record yet. Approve them (or /add_member) first.",
            "different_steam": f"❌ {user.mention} already has a different Steam ID. Not overwritten.",
            "steam_in_use": "❌ That Steam ID already belongs to another player.",
            "error": "❌ Database error, nothing changed.",
        }
        await interaction.followup.send(messages[result], ephemeral=result not in ("updated", "already_set"))

    @nextcord.slash_command(
        name="promote",
        description="Promote a member to a higher rank",
        guild_ids=[GUILD_ID] if GUILD_ID else None
    )
    async def promote_member(
        self,
        interaction: nextcord.Interaction,
        user: nextcord.User = SlashOption(description="User to promote"),
        new_rank: str = SlashOption(description="New rank", choices=rank_choices()),
        reason: Optional[str] = SlashOption(description="Reason for promotion", required=False)
    ):
        """Promote a member to a higher rank."""
        await interaction.response.defer()
        try:
            member = await get_user_info(str(user.id))

            if not member:
                await interaction.followup.send(
                    f"❌ {user.mention} is not found in the database. Use `/add_member` first.",
                    ephemeral=True
                )
                return

            # Validate promotion
            if not self.rank_manager.is_valid_promotion(member["rank"], new_rank):
                await interaction.followup.send(
                    f"❌ Cannot promote from {self.rank_manager.get_rank(member['rank'])['name']} "
                    f"to {self.rank_manager.get_rank(new_rank)['name']}. "
                    f"Invalid rank progression.",
                    ephemeral=True
                )
                return
            
            # Update rank in database
            notes = f"Promoted to {self.rank_manager.get_rank(new_rank)['name']}"
            if reason:
                notes += f" - Reason: {reason}"

            success = await modify_user(str(user.id), rank=new_rank, reason=notes)

            if success:

                embed = nextcord.Embed(
                    title="🎉 Promotion Successful",
                    color=0x00ff00,
                    description=f"**{member['name']}** has been promoted!"
                )
                embed.add_field(
                    name="Previous Rank", 
                    value=self._rank_text(member["rank"]), 
                    inline=True
                )
                embed.add_field(
                    name="New Rank", 
                    value=self._rank_text(new_rank), 
                    inline=True
                )
                embed.add_field(name="Member", value=user.mention, inline=True)
                
                if reason:
                    embed.add_field(name="Reason", value=reason, inline=False)
                
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(
                    "❌ Failed to update rank in database.", 
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error promoting member: {e}")
            await interaction.followup.send(
                f"❌ Failed to promote member: {str(e)}", 
                ephemeral=True
            )

    @nextcord.slash_command(
        name="demote",
        description="Demote a member to a lower rank",
        guild_ids=[GUILD_ID] if GUILD_ID else None
    )
    async def demote_member(
        self,
        interaction: nextcord.Interaction,
        user: nextcord.User = SlashOption(description="User to demote"),
        new_rank: str = SlashOption(description="New rank", choices=rank_choices()),
        reason: str = SlashOption(description="Reason for demotion")
    ):
        """Demote a member to a lower rank."""
        await interaction.response.defer()
        try:
            member = await get_user_info(str(user.id))

            if not member:
                await interaction.followup.send(
                    f"❌ {user.mention} is not found in the database.",
                    ephemeral=True
                )
                return

            if rank_index(new_rank) >= rank_index(member["rank"]):
                await interaction.followup.send(
                    f"❌ New rank must be lower than current rank ({member['rank']}).",
                    ephemeral=True
                )
                return

            # Update rank in database
            notes = f"Demoted to {self.rank_manager.get_rank(new_rank)['name']} - Reason: {reason}"
            success = await modify_user(str(user.id), rank=new_rank, reason=notes)

            if success:

                embed = nextcord.Embed(
                    title="⬇️ Demotion Applied",
                    color=0xff9900,
                    description=f"**{member['name']}** has been demoted."
                )
                embed.add_field(
                    name="Previous Rank", 
                    value=self._rank_text(member["rank"]), 
                    inline=True
                )
                embed.add_field(
                    name="New Rank", 
                    value=self._rank_text(new_rank), 
                    inline=True
                )
                embed.add_field(name="Member", value=user.mention, inline=True)
                embed.add_field(name="Reason", value=reason, inline=False)
                
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(
                    "❌ Failed to update rank in database.", 
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error demoting member: {e}")
            await interaction.followup.send(
                f"❌ Failed to demote member: {str(e)}", 
                ephemeral=True
            )

    @nextcord.slash_command(
        name="reprimand",
        description="Log a reprimand on a member's service record",
        guild_ids=[GUILD_ID] if GUILD_ID else None
    )
    async def reprimand(
        self,
        interaction: nextcord.Interaction,
        user: nextcord.User = SlashOption(description="Member to reprimand"),
        reason: str = SlashOption(description="Reason for the reprimand")
    ):
        """Add a reprimand event to the member's service record."""
        await interaction.response.defer()
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
        when = None
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                when = datetime.datetime.strptime(date, fmt).replace(tzinfo=datetime.timezone.utc)
                break
            except ValueError:
                pass
        if when is None:
            await interaction.followup.send("❌ Date must look like `2026-11-20` or `2026-11-20 19:00` (UTC).")
            return
        if details:
            try:
                if not isinstance(json.loads(details), dict):
                    raise ValueError
            except ValueError:
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