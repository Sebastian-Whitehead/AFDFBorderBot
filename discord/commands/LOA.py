import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption
from datetime import datetime

from ..utils import send_processed_embed

class LOA(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Store LOA requests in memory for now (will be replaced with database later)
        self.loa_requests = {}

    @nextcord.slash_command(name="loa", description="Submit a Leave of Absence request")
    async def loa_command(
        self,
        interaction: Interaction,
        end_date: str = SlashOption(
            description="End date of your LOA (format: YYYY-MM-DD or MM/DD/YYYY)"
        ),
        reason: str = SlashOption(
            description="Reason for your Leave of Absence (optional)",
            required=False,
            default=None
        )
    ):
        """Submit a Leave of Absence request."""
        
        # Check if user already has an active LOA
        user_id = interaction.user.id
        submit_date = datetime.now()
        
        if user_id in self.loa_requests:
            # Update existing LOA
            self.loa_requests[user_id]['end_date'] = end_date
            self.loa_requests[user_id]['reason'] = reason
            # Keep the original start date and submitted_at, but update a "last_modified" field
            self.loa_requests[user_id]['last_modified'] = submit_date
            action_text = "updated"
        else:
            # Create new LOA
            self.loa_requests[user_id] = {
                'user': interaction.user,
                'end_date': end_date,
                'reason': reason,
                'submitted_at': submit_date,
                'start_date': submit_date.strftime("%Y-%m-%d")
            }
            action_text = "submitted"
        
        # Prepare replacements for the embed
        replacements = {
            '{user}': interaction.user.mention,
            '{username}': interaction.user.display_name,
            '{User}': interaction.user.mention,
            '{Username}': interaction.user.display_name,
            '{userid}': str(interaction.user.id),
            '{usertag}': str(interaction.user),
            '{end_date}': end_date,
            '{reason}': reason if reason else "No reason provided",
            '{submitted_date}': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Send the processed embed publicly to the channel
        await send_processed_embed(interaction.channel, 'loa.json', replacements)
        
        # Send a confirmation to the user privately
        await interaction.response.send_message(f"✅ Your LOA request has been {action_text}!", ephemeral=True)

    @nextcord.slash_command(name="loa-list", description="List all current active LOAs")
    async def loa_list_command(self, interaction: Interaction):
        """List all current active Leave of Absence requests."""
        
        if not self.loa_requests:
            await interaction.response.send_message("📋 **Current LOAs**\nNo active LOAs found.", ephemeral=True)
            return
        
        # Get today's date for comparison
        today = datetime.now().date()
        
        # Filter active LOAs
        active_loas = []
        for user_id, loa_data in self.loa_requests.items():
            try:
                # Parse the end date (support multiple formats)
                end_date_str = loa_data['end_date']
                if '/' in end_date_str:  # MM/DD/YYYY format
                    end_date = datetime.strptime(end_date_str, "%m/%d/%Y").date()
                else:  # YYYY-MM-DD format
                    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                
                # Check if LOA is still active (end date is today or in the future)
                if end_date >= today:
                    active_loas.append({
                        'user': loa_data['user'],
                        'end_date': end_date,
                        'end_date_str': end_date_str,
                        'reason': loa_data['reason'],
                        'submitted_at': loa_data['submitted_at'],
                        'start_date': loa_data.get('start_date', loa_data['submitted_at'].strftime("%Y-%m-%d"))
                    })
            except ValueError:
                # If date parsing fails, assume it's still active and include it
                active_loas.append({
                    'user': loa_data['user'],
                    'end_date': None,
                    'end_date_str': end_date_str,
                    'reason': loa_data['reason'],
                    'submitted_at': loa_data['submitted_at'],
                    'start_date': loa_data.get('start_date', loa_data['submitted_at'].strftime("%Y-%m-%d"))
                })
        
        if not active_loas:
            await interaction.response.send_message("📋 **Current LOAs**\nNo active LOAs found.", ephemeral=True)
            return
        
        # Create text message with active LOAs
        message = f"📋 **Current Active LOAs** ({len(active_loas)} active)\n\n"
        
        for loa in active_loas:
            user_name = loa['user'].display_name
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
        
        await interaction.response.send_message(message, ephemeral=True)

    @nextcord.slash_command(name="loa-cancel", description="Cancel your active Leave of Absence")
    async def loa_cancel_command(self, interaction: Interaction):
        """Cancel your active Leave of Absence request."""
        
        user_id = interaction.user.id
        
        # Check if user has an active LOA
        if user_id not in self.loa_requests:
            await interaction.response.send_message(
                "❌ You don't have an active LOA to cancel.", 
                ephemeral=True
            )
            return
        
        # Get LOA details before removing
        loa_data = self.loa_requests[user_id]
        user_name = interaction.user.display_name
        
        # Remove the LOA
        del self.loa_requests[user_id]
        
        # Send public cancellation message
        cancel_message = f"📋 **LOA Canceled**\n{interaction.user.mention} has canceled their Leave of Absence."
        await interaction.channel.send(cancel_message)
        
        # Send private confirmation
        await interaction.response.send_message(
            "✅ Your LOA has been successfully canceled!", 
            ephemeral=True
        )

# Function to set up the Cog
def setup(bot):
    bot.add_cog(LOA(bot))
