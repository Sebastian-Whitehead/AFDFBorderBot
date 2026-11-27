"""
Settings management commands for AFDFBorderBot.

Provides Discord slash commands to view and modify bot settings.
"""

import logging

import discord
from discord import Interaction, app_commands
from discord.ext import commands

from ..config import LEADERSHIP_ROLE_ID, get_setting, update_setting, load_settings
from ..utils.choices import to_choices

logger = logging.getLogger(__name__)

class SettingsManagement(commands.Cog):
    """Commands for managing bot settings."""
    
    def __init__(self, bot):
        self.bot = bot

    settings = app_commands.Group(name="settings", description="Manage bot settings")

    @settings.command(
        name="list",
        description="List all current bot settings"
    )
    @app_commands.checks.has_role(LEADERSHIP_ROLE_ID)
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
            
            embed = discord.Embed(
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
            
            embed.add_field(
                name="Office Hours Warning",
                value=f"`office-hours-enabled`: {'✅ Enabled' if get_setting('office-hours-enabled', False) else '❌ Disabled'}\n"
                      f"{get_setting('office-hours-start', 9):02d}:00-{get_setting('office-hours-end', 17):02d}:00 UTC",
                inline=False
            )

            modpack_url = get_setting('modpack-url', None)
            if modpack_url:
                embed.add_field(name="Modpack Link (enlist welcome)", value=f"`modpack-url`: {modpack_url}", inline=False)

            embed.set_footer(text="Use /settings set for boolean values, /settings set-interval for check interval, /settings set-modpack-url for the modpack link")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to retrieve settings: {str(e)}",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @settings.command(
        name="set",
        description="Set a bot setting value"
    )
    @app_commands.checks.has_role(LEADERSHIP_ROLE_ID)
    @app_commands.describe(setting="Setting to modify", value="Value to set (true/false)")
    @app_commands.choices(setting=to_choices([
        "listen-for-join-leave",
        "new-citizen-welcome",
        "enlist-welcome",
        "listen-for-border-officer",
        "office-hours-enabled"
    ]))
    async def settings_set(self, interaction: Interaction, setting: str, value: bool):
        """Set a bot setting value."""
        
        try:
            # Update the setting
            success = await update_setting(setting, value)
            
            if success:
                status = "✅ Enabled" if value else "❌ Disabled"
                embed = discord.Embed(
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
                embed = discord.Embed(
                    title="❌ Error",
                    description=f"Failed to update setting `{setting}`",
                    color=0xff0000
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to update setting: {str(e)}",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @settings.command(
        name="set-interval",
        description="Set the check interval for the Border Officer Monitor and office hours"
    )
    @app_commands.checks.has_role(LEADERSHIP_ROLE_ID)
    @app_commands.describe(minutes="Check interval in minutes (minimum 1, maximum 60)")
    async def settings_set_interval(self, interaction: Interaction, minutes: app_commands.Range[int, 1, 60]):
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
                
                embed = discord.Embed(
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
                embed = discord.Embed(
                    title="❌ Error",
                    description="Failed to update the check interval setting",
                    color=0xff0000
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to update setting: {str(e)}",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @settings.command(
        name="set-office-hours",
        description="Set the office hours (UTC); outside them a warning is posted in the checkpoint"
    )
    @app_commands.checks.has_role(LEADERSHIP_ROLE_ID)
    @app_commands.describe(start="Opening hour, UTC (0-23)", end="Closing hour, UTC (0-23)")
    async def settings_set_office_hours(self, interaction: Interaction, start: app_commands.Range[int, 0, 23], end: app_commands.Range[int, 0, 23]):
        """Set the office hours used by the Office Hours Monitor."""
        if start == end:
            await interaction.response.send_message("❌ Start and end must differ.", ephemeral=True)
            return
        if await update_setting('office-hours-start', start) and await update_setting('office-hours-end', end):
            await interaction.response.send_message(f"✅ Office hours set to {start:02d}:00-{end:02d}:00 UTC", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Failed to update the office hours", ephemeral=True)

    @settings.command(
        name="set-modpack-url",
        description="Set the modpack link used in the /enlist welcome"
    )
    @app_commands.checks.has_role(LEADERSHIP_ROLE_ID)
    @app_commands.describe(url="Full link starting with http:// or https://")
    async def settings_set_modpack_url(self, interaction: Interaction, url: str):
        """Set the modpack link shown in the enlist welcome embed."""
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            await interaction.response.send_message("❌ The link must start with http:// or https://", ephemeral=True)
            return
        if await update_setting('modpack-url', url):
            await interaction.response.send_message(f"✅ Modpack link set to {url}", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Failed to update the modpack link", ephemeral=True)


async def setup(bot):
    """Set up the Settings Management cog."""
    await bot.add_cog(SettingsManagement(bot))
