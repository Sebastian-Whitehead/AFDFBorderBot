"""
User Management Commands for AFDFBorderBot

This module contains commands for managing members, promotions, and user profiles.
Includes functionality for adding members, promoting users, and managing user data.
"""

import nextcord
from nextcord.ext import commands
from nextcord import SlashOption
from typing import Optional
from decimal import Decimal
import logging

from ..utils import get_db_manager, RankManager
from ..config import GUILD_ID

logger = logging.getLogger(__name__)


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
    async def add_member(
        self,
        interaction: nextcord.Interaction,
        name: str = SlashOption(description="Member's name"),
        steam_id: str = SlashOption(description="Member's Steam ID"),
        discord_user: Optional[nextcord.User] = SlashOption(description="Discord user (optional)", required=False),
        rank: int = SlashOption(description="Starting rank (0-10)", default=0, min_value=0, max_value=10),
        notes: Optional[str] = SlashOption(description="Additional notes", required=False)
    ):
        """Add a new member to the database."""
        try:
            # Validate rank
            if not self.rank_manager.is_valid_rank(rank):
                await interaction.response.send_message(
                    f"❌ Invalid rank level: {rank}. Must be between 0-10.", 
                    ephemeral=True
                )
                return
            
            db = await get_db_manager()
            discord_id = str(discord_user.id) if discord_user else None
            
            # Check if user already exists
            existing_user = None
            if discord_id:
                existing_user = await db.get_user_by_discord_id(discord_id)
            if not existing_user:
                existing_user = await db.get_user_by_steam_id(steam_id)
            
            if existing_user:
                await interaction.response.send_message(
                    f"❌ User already exists in database: {existing_user.name}",
                    ephemeral=True
                )
                return
            
            # Create new user
            new_user = await db.create_user(
                name=name,
                steam_id=steam_id,
                discord_id=discord_id,
                rank=rank,
                notes=notes
            )
            
            rank_info = self.rank_manager.get_rank_info(rank)
            embed = nextcord.Embed(
                title="✅ Member Added Successfully",
                color=0x00ff00,
                description=f"Added **{name}** to the database"
            )
            embed.add_field(name="Steam ID", value=steam_id, inline=True)
            embed.add_field(name="Discord", value=discord_user.mention if discord_user else "Not linked", inline=True)
            embed.add_field(name="Rank", value=f"{rank_info['name']} ({rank_info['code']})", inline=True)
            
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
        name="promote",
        description="Promote a member to a higher rank",
        guild_ids=[GUILD_ID] if GUILD_ID else None
    )
    async def promote_member(
        self,
        interaction: nextcord.Interaction,
        user: nextcord.User = SlashOption(description="User to promote"),
        new_rank: int = SlashOption(description="New rank level (0-10)", min_value=0, max_value=10),
        reason: Optional[str] = SlashOption(description="Reason for promotion", required=False)
    ):
        """Promote a member to a higher rank."""
        try:
            db = await get_db_manager()
            member = await db.get_user_by_discord_id(str(user.id))
            
            if not member:
                await interaction.response.send_message(
                    f"❌ {user.mention} is not found in the database. Use `/add_member` first.",
                    ephemeral=True
                )
                return
            
            # Validate promotion
            if not self.rank_manager.can_promote_to(member.rank, new_rank):
                current_rank = self.rank_manager.get_rank_info(member.rank)
                target_rank = self.rank_manager.get_rank_info(new_rank)
                await interaction.response.send_message(
                    f"❌ Cannot promote from {current_rank['name']} to {target_rank['name']}. "
                    f"Invalid rank progression.",
                    ephemeral=True
                )
                return
            
            # Update rank in database
            notes = f"Promoted to {self.rank_manager.get_rank_info(new_rank)['name']}"
            if reason:
                notes += f" - Reason: {reason}"
            
            success = await db.update_user_rank(member.id, new_rank, notes)
            
            if success:
                old_rank_info = self.rank_manager.get_rank_info(member.rank)
                new_rank_info = self.rank_manager.get_rank_info(new_rank)
                
                embed = nextcord.Embed(
                    title="🎉 Promotion Successful",
                    color=0x00ff00,
                    description=f"**{member.name}** has been promoted!"
                )
                embed.add_field(
                    name="Previous Rank", 
                    value=f"{old_rank_info['name']} ({old_rank_info['code']})", 
                    inline=True
                )
                embed.add_field(
                    name="New Rank", 
                    value=f"{new_rank_info['name']} ({new_rank_info['code']})", 
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
        new_rank: int = SlashOption(description="New rank level (0-10)", min_value=0, max_value=10),
        reason: str = SlashOption(description="Reason for demotion")
    ):
        """Demote a member to a lower rank."""
        try:
            db = await get_db_manager()
            member = await db.get_user_by_discord_id(str(user.id))
            
            if not member:
                await interaction.response.send_message(
                    f"❌ {user.mention} is not found in the database.",
                    ephemeral=True
                )
                return
            
            if new_rank >= member.rank:
                await interaction.response.send_message(
                    f"❌ New rank must be lower than current rank ({member.rank}).",
                    ephemeral=True
                )
                return
            
            # Update rank in database
            notes = f"Demoted to {self.rank_manager.get_rank_info(new_rank)['name']} - Reason: {reason}"
            success = await db.update_user_rank(member.id, new_rank, notes)
            
            if success:
                old_rank_info = self.rank_manager.get_rank_info(member.rank)
                new_rank_info = self.rank_manager.get_rank_info(new_rank)
                
                embed = nextcord.Embed(
                    title="⬇️ Demotion Applied",
                    color=0xff9900,
                    description=f"**{member.name}** has been demoted."
                )
                embed.add_field(
                    name="Previous Rank", 
                    value=f"{old_rank_info['name']} ({old_rank_info['code']})", 
                    inline=True
                )
                embed.add_field(
                    name="New Rank", 
                    value=f"{new_rank_info['name']} ({new_rank_info['code']})", 
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
            db = await get_db_manager()
            member = await db.get_user_by_discord_id(str(user.id))
            
            if not member:
                await interaction.response.send_message(
                    f"❌ {user.mention} is not found in the database.",
                    ephemeral=True
                )
                return
            
            rank_info = self.rank_manager.get_rank_info(member.rank)
            
            embed = nextcord.Embed(
                title=f"👤 Profile: {member.name}",
                color=0x0099ff
            )
            
            # Basic info
            embed.add_field(name="Name", value=member.name, inline=True)
            embed.add_field(name="Discord", value=user.mention, inline=True)
            embed.add_field(name="Steam ID", value=member.steam_id, inline=True)
            
            # Rank and service
            embed.add_field(
                name="Rank", 
                value=f"{rank_info['name']} ({rank_info['code']})", 
                inline=True
            )
            embed.add_field(name="Money", value=f"${member.money:,.2f}", inline=True)
            embed.add_field(name="Deaths", value=str(member.deaths), inline=True)
            
            # Dates
            if member.joined_at:
                embed.add_field(
                    name="Joined", 
                    value=member.joined_at.strftime("%Y-%m-%d"), 
                    inline=True
                )
            
            if member.enlisted_at:
                embed.add_field(
                    name="Enlisted", 
                    value=member.enlisted_at.strftime("%Y-%m-%d"), 
                    inline=True
                )
            
            if member.last_death:
                embed.add_field(
                    name="Last Death", 
                    value=member.last_death.strftime("%Y-%m-%d"), 
                    inline=True
                )
            
            # Achievements
            if member.achievements:
                achievements_text = "\n".join([f"• {achievement}" for achievement in member.achievements])
                embed.add_field(name="Achievements", value=achievements_text[:1024], inline=False)
            
            # Notes
            if member.notes:
                embed.add_field(name="Notes", value=member.notes[:1024], inline=False)
            
            embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error viewing profile: {e}")
            await interaction.response.send_message(
                f"❌ Failed to load profile: {str(e)}", 
                ephemeral=True
            )

    @nextcord.slash_command(
        name="give_money",
        description="Give money to a member",
        guild_ids=[GUILD_ID] if GUILD_ID else None
    )
    async def give_money(
        self,
        interaction: nextcord.Interaction,
        user: nextcord.User = SlashOption(description="User to give money to"),
        amount: float = SlashOption(description="Amount to give"),
        reason: Optional[str] = SlashOption(description="Reason for giving money", required=False)
    ):
        """Give money to a member."""
        try:
            if amount <= 0:
                await interaction.response.send_message(
                    "❌ Amount must be positive.", 
                    ephemeral=True
                )
                return
            
            db = await get_db_manager()
            member = await db.get_user_by_discord_id(str(user.id))
            
            if not member:
                await interaction.response.send_message(
                    f"❌ {user.mention} is not found in the database.",
                    ephemeral=True
                )
                return
            
            success = await db.update_user_money(member.id, Decimal(str(amount)), "add")
            
            if success:
                embed = nextcord.Embed(
                    title="💰 Money Given",
                    color=0x00ff00,
                    description=f"Successfully gave **${amount:,.2f}** to {user.mention}"
                )
                
                if reason:
                    embed.add_field(name="Reason", value=reason, inline=False)
                
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message(
                    "❌ Failed to update money in database.", 
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error giving money: {e}")
            await interaction.response.send_message(
                f"❌ Failed to give money: {str(e)}", 
                ephemeral=True
            )

    @nextcord.slash_command(
        name="leaderboard",
        description="Show top members by money or rank",
        guild_ids=[GUILD_ID] if GUILD_ID else None
    )
    async def leaderboard(
        self,
        interaction: nextcord.Interaction,
        category: str = SlashOption(
            description="Leaderboard category",
            choices=["money", "rank"],
            default="money"
        ),
        limit: int = SlashOption(description="Number of members to show", default=10, min_value=1, max_value=25)
    ):
        """Show leaderboard of top members."""
        try:
            db = await get_db_manager()
            
            if category == "money":
                users = await db.get_top_users_by_money(limit)
                embed = nextcord.Embed(
                    title="💰 Money Leaderboard",
                    color=0xffd700
                )
                
                leaderboard_text = ""
                for i, user in enumerate(users, 1):
                    emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                    leaderboard_text += f"{emoji} **{user.name}** - ${user.money:,.2f}\n"
                
                embed.description = leaderboard_text or "No users found."
                
            elif category == "rank":
                rank_counts = await db.get_user_count_by_rank()
                embed = nextcord.Embed(
                    title="🎖️ Rank Distribution",
                    color=0x4169e1
                )
                
                rank_text = ""
                for rank in sorted(rank_counts.keys(), reverse=True):
                    rank_info = self.rank_manager.get_rank_info(rank)
                    count = rank_counts[rank]
                    rank_text += f"**{rank_info['name']}** ({rank_info['code']}) - {count} member{'s' if count != 1 else ''}\n"
                
                embed.description = rank_text or "No ranks found."
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error showing leaderboard: {e}")
            await interaction.response.send_message(
                f"❌ Failed to load leaderboard: {str(e)}", 
                ephemeral=True
            )


def setup(bot):
    """Add the UserManagement cog to the bot."""
    bot.add_cog(UserManagement(bot))