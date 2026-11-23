"""
Settings management commands for AFDFBorderBot.

Provides Discord slash commands to view and modify bot settings.
"""

import logging

import nextcord
from nextcord.ext import commands, application_checks
from nextcord import Interaction, SlashOption

from ..config import LEADERSHIP_ROLE_ID, TESTING_GUILD_ID, get_setting, update_setting, load_settings

logger = logging.getLogger(__name__)

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
    @application_checks.has_role(LEADERSHIP_ROLE_ID)
    async def settings_list(self, interaction: Interaction):
        """List all current bot settings."""
        # update the cache
        await load_settings()
        try:
            settings_to_check = [
                ('listen-for-join-leave', 'Join/Leave Messages'),
                ('new-citizen-welcome', 'New Citizen Welcome (on /approve)'),
                ('enlist-welcome', 'Enlistment Welcome (on /enlist)'),
                ('listen-for-border-officer', 'Border Officer Monitor'),
                ('border-officer-check-interval', 'Border Officer Check Interval (seconds)')
            ]
            
            embed = nextcord.Embed(
                title="🔧 Bot Settings",
                description="Current configuration stored in database",
                color=0x0099ff
            )
            
            for key, description in settings_to_check:
                value = get_setting(key, None)
                if value is not None:
                    if key == 'border-officer-check-interval':
                        # Special handling for numeric settings
                        embed.add_field(
                            name=description,
                            value=f"`{key}`: {value} seconds ({value//60} minutes)",
                            inline=False
                        )
                    else:
                        # Boolean settings
                        status = "✅ Enabled" if value else "❌ Disabled"
                        embed.add_field(
                            name=description,
                            value=f"`{key}`: {status}",
                            inline=False
                        )
            
            modpack_url = get_setting('modpack-url', None)
            if modpack_url:
                embed.add_field(name="Modpack Link (enlist welcome)", value=f"`modpack-url`: {modpack_url}", inline=False)

            embed.set_footer(text="Use /settings set for boolean values, /settings set-interval for check interval, /settings set-modpack-url for the modpack link")
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
    @application_checks.has_role(LEADERSHIP_ROLE_ID)
    async def settings_set(
        self,
        interaction: Interaction,
        setting: str = SlashOption(
            description="Setting to modify",
            choices=[
                "listen-for-join-leave",
                "new-citizen-welcome",
                "enlist-welcome",
                "listen-for-border-officer"
            ]
        ),
        value: bool = SlashOption(description="Value to set (true/false)")
    ):
        """Set a bot setting value."""
        
        try:
            # Update the setting
            success = await update_setting(setting, value)
            
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

    @settings.subcommand(
        name="set-interval",
        description="Set the Border Officer Monitor check interval"
    )
    @application_checks.has_role(LEADERSHIP_ROLE_ID)
    async def settings_set_interval(
        self,
        interaction: Interaction,
        minutes: int = SlashOption(
            description="Check interval in minutes (minimum 1, maximum 60)",
            min_value=1,
            max_value=60
        )
    ):
        """Set the Border Officer Monitor check interval."""
        
        try:
            # Convert minutes to seconds
            seconds = minutes * 60
            
            # Update the setting
            success = await update_setting('border-officer-check-interval', seconds)
            
            if success:
                # Try to immediately update the BorderOfficerMonitor if it's loaded
                try:
                    border_monitor = self.bot.get_cog('BorderOfficerMonitor')
                    if border_monitor:
                        border_monitor.update_check_interval()
                        footer_text = "Setting saved to database and applied immediately."
                    else:
                        footer_text = "Setting saved to database. The change will take effect on the next check cycle."
                except Exception:
                    logger.exception("Could not apply check interval to BorderOfficerMonitor")
                    footer_text = "Setting saved to database. The change will take effect on the next check cycle."
                
                embed = nextcord.Embed(
                    title="✅ Setting Updated",
                    description=f"Border Officer Monitor check interval has been set to {minutes} minutes",
                    color=0x00ff00
                )
                embed.add_field(
                    name="New Interval",
                    value=f"{minutes} minutes ({seconds} seconds)",
                    inline=True
                )
                embed.set_footer(text=footer_text)
            else:
                embed = nextcord.Embed(
                    title="❌ Error",
                    description="Failed to update the check interval setting",
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

    @settings.subcommand(
        name="set-modpack-url",
        description="Set the modpack link used in the /enlist welcome"
    )
    @application_checks.has_role(LEADERSHIP_ROLE_ID)
    async def settings_set_modpack_url(
        self,
        interaction: Interaction,
        url: str = SlashOption(description="Full link starting with http:// or https://")
    ):
        """Set the modpack link shown in the enlist welcome embed."""
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            await interaction.response.send_message("❌ The link must start with http:// or https://", ephemeral=True)
            return
        if await update_setting('modpack-url', url):
            await interaction.response.send_message(f"✅ Modpack link set to {url}", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Failed to update the modpack link", ephemeral=True)


def setup(bot):
    """Set up the Settings Management cog."""
    bot.add_cog(SettingsManagement(bot))
