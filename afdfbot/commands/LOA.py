from discord import Interaction, app_commands
from discord.ext import commands
from datetime import datetime, timezone
import logging
from typing import Optional

from ..config import LOA_CHANNEL_ID
from ..utils import send_processed_embed, member_replacements
from database.loa_functions import LOAManager

logger = logging.getLogger(__name__)

async def _wrong_channel(interaction) -> bool:
    """Reply and return True when used outside the configured LOA channel."""
    if LOA_CHANNEL_ID and interaction.channel.id != LOA_CHANNEL_ID:
        await interaction.response.send_message(
            f"❌ This command can only be used in <#{LOA_CHANNEL_ID}>.", ephemeral=True
        )
        return True
    return False


class LOA(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="loa", description="Submit a Leave of Absence request")
    @app_commands.describe(
        start_date="First day of your LOA, or the only day if no end date is given (YYYY-MM-DD, DD/MM/YYYY or DD/MM)",
        end_date="Last day of your LOA (optional; leave empty for a single-day LOA)",
        reason="Reason for your Leave of Absence (optional)"
    )
    async def loa_command(
        self,
        interaction: Interaction,
        start_date: str,
        end_date: Optional[str] = None,
        reason: Optional[str] = None
    ):
        """Submit a Leave of Absence request."""
        
        if await _wrong_channel(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        
        try:
            # One date means a single-day LOA
            end_date = end_date or start_date
            parsed_start_date = await LOAManager.parse_end_date(start_date)
            parsed_end_date = await LOAManager.parse_end_date(end_date)
            if parsed_start_date is None or parsed_end_date is None:
                await interaction.followup.send(
                    "❌ Invalid date format. Please use YYYY-MM-DD, DD/MM/YYYY or DD/MM format.",
                    ephemeral=True
                )
                return

            if parsed_end_date < parsed_start_date:
                await interaction.followup.send("❌ End date cannot be before the start date.", ephemeral=True)
                return

            if parsed_end_date < datetime.now(timezone.utc).date():
                await interaction.followup.send(
                    "❌ End date cannot be in the past. Please choose a date from today onwards.",
                    ephemeral=True
                )
                return

            # Create or update LOA in database
            discord_id = str(interaction.user.id)
            username = interaction.user.display_name
            
            is_update, action_text = await LOAManager.create_or_update_loa(
                discord_id, username, end_date, reason, start_date=start_date
            )
            
            # If updating and no reason provided, get the current reason for the embed
            display_reason = reason
            if is_update and reason is None:
                existing_loa = await LOAManager.get_active_loa_by_discord_id(discord_id)
                display_reason = existing_loa['reason'] if existing_loa else None
            
            # Prepare replacements for the embed
            replacements = {
                **member_replacements(interaction.user),
                '{avatar_url}': interaction.user.display_avatar.url,
                '{end_date}': str(parsed_end_date),
                '{period}': (f"is for {parsed_start_date} (1 day)" if parsed_start_date == parsed_end_date
                             else f"runs from {parsed_start_date} until {parsed_end_date} "
                                  f"({(parsed_end_date - parsed_start_date).days + 1} days)"),
                '{reason}': display_reason if display_reason else "No reason provided",
                '{submitted_date}': datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            }
            
            # Send the processed embed publicly to the channel
            await send_processed_embed(interaction.channel, 'loa.json', replacements)
            
            # Send a confirmation to the user privately
            await interaction.followup.send(f"✅ Your LOA request has been {action_text}!", ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error processing LOA command: {e}")
            await interaction.followup.send(
                "❌ An error occurred while processing your LOA request. Please try again.", 
                ephemeral=True
            )

    @app_commands.command(name="loa_list", description="List all current active LOAs")
    async def loa_list_command(self, interaction: Interaction):
        """List all current active Leave of Absence requests."""
        
        if await _wrong_channel(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Clean up expired LOAs first
            await LOAManager.cleanup_expired_loas()
            
            # Get all active LOAs from database
            active_loas_data = await LOAManager.get_all_active_loas()
            
            if not active_loas_data:
                await interaction.followup.send("📋 **Current LOAs**\nNo active LOAs found.", ephemeral=True)
                return
            
            # Get today's date for comparison
            today = datetime.now(timezone.utc).date()
            
            # Process LOAs and filter active ones
            active_loas = []
            for loa_data in active_loas_data:
                try:
                    end_date = await LOAManager.parse_end_date(loa_data['end_date'])
                    # Active = ends today or later
                    if end_date and end_date >= today:
                        active_loas.append({
                            'username': loa_data['username'],
                            'end_date': end_date,
                            'end_date_str': loa_data['end_date'],
                            'reason': loa_data['reason'],
                            'start_date': str(loa_data['start_date'])
                        })
                except Exception as e:
                    logger.warning(f"Error processing LOA data: {e}")
                    continue
            
            if not active_loas:
                await interaction.followup.send("📋 **Current LOAs**\nNo active LOAs found.", ephemeral=True)
                return
            
            # Create text message with active LOAs
            message = f"📋 **Current Active LOAs** ({len(active_loas)} active)\n\n"
            
            for loa in active_loas:
                user_name = loa['username']
                start_date = loa['start_date']
                end_date_display = loa['end_date_str']
                reason = loa['reason'] if loa['reason'] else "No reason provided"
                
                # Calculate days remaining if possible
                days_remaining = ""
                if loa['end_date']:
                    days_diff = (loa['end_date'] - today).days
                    if days_diff == 0:
                        days_remaining = " (ends today)"
                    elif days_diff == 1:
                        days_remaining = " (1 day remaining)"
                    else:
                        days_remaining = f" ({days_diff} days remaining)"
                
                message += f"**{user_name}**\n"
                message += f"Start: {start_date} | End: {end_date_display}{days_remaining}\n"
                message += f"Reason: {reason}\n\n"
            
            message += f"*As of {today.strftime('%Y-%m-%d')}*"
            
            await interaction.followup.send(message, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error processing LOA list command: {e}")
            await interaction.followup.send(
                "❌ An error occurred while fetching LOA list. Please try again.", 
                ephemeral=True
            )

    @app_commands.command(name="loa_cancel", description="Cancel your active Leave of Absence")
    async def loa_cancel_command(self, interaction: Interaction):
        """Cancel your active Leave of Absence request."""
        
        if await _wrong_channel(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        
        try:
            discord_id = str(interaction.user.id)
            
            # Try to cancel the LOA
            was_cancelled = await LOAManager.cancel_loa(discord_id)
            
            if not was_cancelled:
                await interaction.followup.send(
                    "❌ You don't have an active LOA to cancel.", 
                    ephemeral=True
                )
                return
            
            # Send public cancellation message
            cancel_message = f"📋 **LOA Canceled**\n{interaction.user.mention} has canceled their Leave of Absence."
            await interaction.channel.send(cancel_message)
            
            # Send private confirmation
            await interaction.followup.send(
                "✅ Your LOA has been successfully canceled!", 
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error processing LOA cancel command: {e}")
            await interaction.followup.send(
                "❌ An error occurred while canceling your LOA. Please try again.", 
                ephemeral=True
            )

# Function to set up the Cog
async def setup(bot):
    await bot.add_cog(LOA(bot))
