import logging

import nextcord
from nextcord.ext import commands
from nextcord import Member, Interaction, SlashOption

from ..config import JOIN_ROLE_ID, WELCOME_CHANNEL_ID, get_setting, update_setting, LEADERSHIP_ROLE_ID, TESTING_GUILD_ID
from ..utils import send_processed_embed, member_replacements

logger = logging.getLogger(__name__)


class JoinLeaveHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: Member):
        # Check if join/leave listening is enabled using centralized config
        if not get_setting('listen-for-join-leave', True):
            return
            
        # Check if join role is configured
        if JOIN_ROLE_ID:
            role_to_add = member.guild.get_role(JOIN_ROLE_ID)
            if role_to_add:
                try:
                    await member.add_roles(role_to_add)
                except nextcord.HTTPException as e:  # e.g. Forbidden: bot role below the join role
                    logger.error(f"Could not give join role to {member.id}: {e}")
        
        # Send welcome embed
        if WELCOME_CHANNEL_ID:
            welcome_channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
            if welcome_channel:
                await send_processed_embed(welcome_channel, 'member_join.json', member_replacements(member))

    @commands.Cog.listener()
    async def on_member_remove(self, member: Member):
        # Check if join/leave listening is enabled using centralized config
        if not get_setting('listen-for-join-leave', True):
            return
            
        # Send leave embed to welcome channel
        if WELCOME_CHANNEL_ID:
            welcome_channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
            if welcome_channel:
                await send_processed_embed(welcome_channel, 'member_leave.json', member_replacements(member))

    @nextcord.slash_command(
        name="toggle_joinleave", 
        description="Toggle join/leave message functionality",
        guild_ids=[TESTING_GUILD_ID] if TESTING_GUILD_ID else None,
    )
    async def toggle_join_leave(
        self, 
        interaction: Interaction,
        action: str = SlashOption(
            description="Enable or disable join/leave messages",
            choices={"Enable": "enable", "Disable": "disable", "Status": "status"}
        )
    ):
        """Toggle join/leave message functionality on or off."""
        # Check if command is being used in the testing guild
        if TESTING_GUILD_ID and interaction.guild_id != TESTING_GUILD_ID:
            embed = nextcord.Embed(
                title="❌ Command Not Available",
                description="This command can only be used in the testing guild.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        # Check if user has leadership role
        if LEADERSHIP_ROLE_ID and not any(role.id == LEADERSHIP_ROLE_ID for role in interaction.user.roles):
            embed = nextcord.Embed(
                title="❌ Permission Denied",
                description="You need the Leadership role to use this command.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if action == "enable":
            if await update_setting('listen-for-join-leave', True):
                embed = nextcord.Embed(
                    title="✅ Join/Leave Messages Enabled",
                    description="Join and leave messages will now be sent to the welcome channel.\n*Setting saved to database*",
                    color=0x00ff00
                )
            else:
                embed = nextcord.Embed(
                    title="❌ Error",
                    description="Failed to save setting to database",
                    color=0xff0000
                )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        elif action == "disable":
            if await update_setting('listen-for-join-leave', False):
                embed = nextcord.Embed(
                    title="❌ Join/Leave Messages Disabled",
                    description="Join and leave messages have been disabled.\n*Setting saved to database*",
                    color=0xff0000
                )
            else:
                embed = nextcord.Embed(
                    title="❌ Error",
                    description="Failed to save setting to database",
                    color=0xff0000
                )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        elif action == "status":
            current_enabled = get_setting('listen-for-join-leave', True)
            status = "✅ Enabled" if current_enabled else "❌ Disabled"
            embed = nextcord.Embed(
                title="📊 Join/Leave Messages Status",
                description=f"Current status: {status}",
                color=0x00ff00 if current_enabled else 0xff0000
            )
            embed.add_field(
                name="Welcome Channel", 
                value=f"<#{WELCOME_CHANNEL_ID}>" if WELCOME_CHANNEL_ID else "Not configured",
                inline=False
            )
            if JOIN_ROLE_ID:
                embed.add_field(
                    name="Auto-assign Role", 
                    value=f"<@&{JOIN_ROLE_ID}>",
                    inline=False
                )
            await interaction.response.send_message(embed=embed, ephemeral=True)

# Function to set up the Cog
def setup(bot):
    bot.add_cog(JoinLeaveHandler(bot))