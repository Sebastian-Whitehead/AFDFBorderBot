"""
Settings management commands for AFDFBorderBot.

Provides Discord slash commands to view and modify bot settings.
"""

import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption

from ..config import LEADERSHIP_ROLE_ID, TESTING_GUILD_ID, get_setting, update_setting

class SettingsManagement(commands.Cog):
    """Commands for managing bot settings."""
    
    def __init__(self, bot):
        self.bot = bot

    @nextcord.slash_command(
        name="settings",
        description="Manage bot settings",
        guild_ids=[TESTING_GUILD_ID] if TESTING_GUILD_ID else None
    )
    async def settings(self, interaction: Interaction):
        """Base command for settings management."""
        pass

    @settings.subcommand(
        name="list",
        description="List all current bot settings"
    )
    async def settings_list(self, interaction: Interaction):
        """List all current bot settings."""
        
        # Check if user has leadership role
        if LEADERSHIP_ROLE_ID and not any(role.id == LEADERSHIP_ROLE_ID for role in interaction.user.roles):
            embed = nextcord.Embed(
                title="❌ Permission Denied",
                description="You need the Leadership role to use this command.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            settings_to_check = [
                ('listen-for-join-leave', 'Join/Leave Messages'),
                ('listen-for-border-officer', 'Border Officer Monitor'),
                ('listen-for-event-start', 'Event Start Listener')
            ]
            
            embed = nextcord.Embed(
                title="🔧 Bot Settings",
                description="Current configuration stored in database",
                color=0x0099ff
            )
            
            for key, description in settings_to_check:
                value = get_setting(key, None)
                if value is not None:
                    status = "✅ Enabled" if value else "❌ Disabled"
                    embed.add_field(
                        name=description,
                        value=f"`{key}`: {status}",
                        inline=False
                    )
            
            embed.set_footer(text="Use /settings set to modify these values")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = nextcord.Embed(
                title="❌ Error",
                description=f"Failed to retrieve settings: {str(e)}",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @settings.subcommand(
        name="set",
        description="Set a bot setting value"
    )
    async def settings_set(
        self,
        interaction: Interaction,
        setting: str = SlashOption(
            description="Setting to modify",
            choices=[
                "listen-for-join-leave",
                "listen-for-border-officer", 
                "listen-for-event-start"
            ]
        ),
        value: bool = SlashOption(description="Value to set (true/false)")
    ):
        """Set a bot setting value."""
        
        # Check if user has leadership role
        if LEADERSHIP_ROLE_ID and not any(role.id == LEADERSHIP_ROLE_ID for role in interaction.user.roles):
            embed = nextcord.Embed(
                title="❌ Permission Denied",
                description="You need the Leadership role to use this command.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            # Update the setting
            success = update_setting(setting, value)
            
            if success:
                status = "✅ Enabled" if value else "❌ Disabled"
                embed = nextcord.Embed(
                    title="✅ Setting Updated",
                    description=f"Setting `{setting}` has been {status.lower()}",
                    color=0x00ff00 if value else 0xff0000
                )
                embed.add_field(
                    name="New Value",
                    value=status,
                    inline=True
                )
                embed.set_footer(text="Setting saved to database")
            else:
                embed = nextcord.Embed(
                    title="❌ Error",
                    description=f"Failed to update setting `{setting}`",
                    color=0xff0000
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = nextcord.Embed(
                title="❌ Error",
                description=f"Failed to update setting: {str(e)}",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


def setup(bot):
    """Set up the Settings Management cog."""
    bot.add_cog(SettingsManagement(bot))
