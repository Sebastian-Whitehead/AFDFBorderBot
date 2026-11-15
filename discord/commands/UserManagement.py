"""
User Management Commands for AFDFBorderBot

This module contains commands for managing members, promotions, and user profiles.
Includes functionality for adding members, promoting users, and managing user data.
"""

import nextcord
from nextcord.ext import commands
from nextcord import SlashOption
from typing import Optional
import logging

from database import create_user, get_user_info, modify_user, set_steam_id, create_service_record
from database.rank_codes import rank_choices, rank_index
from ..utils import RankManager
from ..utils.steam import resolve_steam_id
from ..config import TESTING_GUILD_ID as GUILD_ID

logger = logging.getLogger(__name__)


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
        name: str = SlashOption(description="Member's name"),
        steam_id: str = SlashOption(description="Member's SteamID64 or Steam profile URL"),
        discord_user: Optional[nextcord.User] = SlashOption(description="Discord user (optional)", required=False),
        rank: str = SlashOption(description="Starting rank", default="EN0", choices=rank_choices()),
        notes: Optional[str] = SlashOption(description="Additional notes", required=False)
    ):
        """Add a new member to the database."""
        try:
            steam_id = await resolve_steam_id(steam_id)
            if steam_id is None:
                await interaction.response.send_message(
                    "❌ Steam ID must be numeric (SteamID64) or a Steam profile link that can be resolved.",
                    ephemeral=True
                )
                return

            discord_id = str(discord_user.id) if discord_user else None

            # Check if user already exists
            existing_user = await get_user_info(discord_id) if discord_id else None
            existing_user = existing_user or await get_user_info(steam_id)

            if existing_user:
                await interaction.response.send_message(
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
                notes=notes
            )
            if new_user is None:
                await interaction.response.send_message(
                    "❌ Failed to add member (already exists or invalid data).",
                    ephemeral=True
                )
                return

            embed = nextcord.Embed(
                title="✅ Member Added Successfully",
                color=0x00ff00,
                description=f"Added **{name}** to the database"
            )
            embed.add_field(name="Steam ID", value=steam_id, inline=True)
            embed.add_field(name="Discord", value=discord_user.mention if discord_user else "Not linked", inline=True)
            embed.add_field(name="Rank", value=self._rank_text(rank), inline=True)
            
            if notes:
                embed.add_field(name="Notes", value=notes, inline=False)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error adding member: {e}")
            await interaction.response.send_message(
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
        result = await create_service_record(str(user.id), rank)
        messages = {
            "created": f"✅ Service record created for {user.mention} at {self._rank_text(rank)}.",
            "already_exists": f"❌ {user.mention} already has a service record.",
            "no_identity": f"❌ {user.mention} has no player record yet. Approve them (or /add_member) first.",
            "error": "❌ Database error, nothing changed.",
        }
        await interaction.response.send_message(messages[result], ephemeral=result != "created")

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
        steam_id = await resolve_steam_id(steam_url)
        if steam_id is None:
            await interaction.response.send_message(
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
        await interaction.response.send_message(messages[result], ephemeral=result not in ("updated", "already_set"))

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
        try:
            member = await get_user_info(str(user.id))

            if not member:
                await interaction.response.send_message(
                    f"❌ {user.mention} is not found in the database. Use `/add_member` first.",
                    ephemeral=True
                )
                return

            # Validate promotion
            if not self.rank_manager.is_valid_promotion(member["rank"], new_rank):
                await interaction.response.send_message(
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
                
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message(
                    "❌ Failed to update rank in database.", 
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error promoting member: {e}")
            await interaction.response.send_message(
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
        try:
            member = await get_user_info(str(user.id))

            if not member:
                await interaction.response.send_message(
                    f"❌ {user.mention} is not found in the database.",
                    ephemeral=True
                )
                return

            if rank_index(new_rank) >= rank_index(member["rank"]):
                await interaction.response.send_message(
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
                
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message(
                    "❌ Failed to update rank in database.", 
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error demoting member: {e}")
            await interaction.response.send_message(
                f"❌ Failed to demote member: {str(e)}", 
                ephemeral=True
            )

    @nextcord.slash_command(
        name="profile",
        description="View a member's profile and statistics",
        guild_ids=[GUILD_ID] if GUILD_ID else None
    )
    async def view_profile(
        self,
        interaction: nextcord.Interaction,
        user: nextcord.User = SlashOption(description="User to view profile for")
    ):
        """View a member's profile and statistics."""
        try:
            member = await get_user_info(str(user.id))

            if not member:
                await interaction.response.send_message(
                    f"❌ {user.mention} is not found in the database.",
                    ephemeral=True
                )
                return

            embed = nextcord.Embed(
                title=f"👤 Profile: {member['name']}",
                color=0x0099ff
            )

            # Basic info
            embed.add_field(name="Name", value=member["name"], inline=True)
            embed.add_field(name="Discord", value=user.mention, inline=True)
            embed.add_field(name="Steam ID", value=member["steam_id"], inline=True)
            
            # Rank and service
            embed.add_field(
                name="Rank", 
                value=self._rank_text(member["rank"]), 
                inline=True
            )
            embed.add_field(name="Deaths", value=str(member["deaths"]), inline=True)

            # Dates
            if member["joined_at"]:
                embed.add_field(
                    name="Joined",
                    value=member["joined_at"].strftime("%Y-%m-%d"),
                    inline=True
                )

            if member["enlisted_at"]:
                embed.add_field(
                    name="Enlisted",
                    value=member["enlisted_at"].strftime("%Y-%m-%d"),
                    inline=True
                )

            if member["last_death"]:
                embed.add_field(
                    name="Last Death",
                    value=member["last_death"].strftime("%Y-%m-%d"),
                    inline=True
                )

            # Achievements
            if member["achievements"]:
                achievements_text = "\n".join([f"• {achievement}" for achievement in member["achievements"]])
                embed.add_field(name="Achievements", value=achievements_text[:1024], inline=False)

            # Notes
            if member["notes"]:
                embed.add_field(name="Notes", value=member["notes"][:1024], inline=False)
            
            embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error viewing profile: {e}")
            await interaction.response.send_message(
                f"❌ Failed to load profile: {str(e)}", 
                ephemeral=True
            )


def setup(bot):
    """Add the UserManagement cog to the bot."""
    bot.add_cog(UserManagement(bot))