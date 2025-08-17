import nextcord
from nextcord.ext import commands
from nextcord import Member, Interaction, SlashOption

from ..config import JOIN_ROLE_ID, ENABLE_JOIN_LEAVE, WELCOME_CHANNEL_ID
from ..utils import send_processed_embed

class JoinLeaveHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Store the current state in memory (you might want to persist this to a config file)
        self.join_leave_enabled = ENABLE_JOIN_LEAVE

    @commands.Cog.listener()
    async def on_member_join(self, member: Member):
        # Check if join/leave listening is enabled
        if not self.join_leave_enabled:
            return
            
        # Check if join role is configured
        if JOIN_ROLE_ID:
            role_to_add = member.guild.get_role(JOIN_ROLE_ID)
            if role_to_add:
                await member.add_roles(role_to_add)
        
        # Send welcome embed
        if WELCOME_CHANNEL_ID:
            welcome_channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
            if welcome_channel:
                replacements = {
                    '{user}': member.mention,
                    '{username}': member.display_name,
                    '{User}': member.mention,
                    '{Username}': member.display_name,
                    '{userid}': str(member.id),
                    '{usertag}': str(member),
                }
                await send_processed_embed(welcome_channel, 'member_join.json', replacements)

    @commands.Cog.listener()
    async def on_member_remove(self, member: Member):
        # Check if join/leave listening is enabled
        if not self.join_leave_enabled:
            return
            
        # Send leave embed to welcome channel
        if WELCOME_CHANNEL_ID:
            welcome_channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
            if welcome_channel:
                replacements = {
                    '{user}': member.mention,
                    '{username}': member.display_name,
                    '{User}': member.mention,
                    '{Username}': member.display_name,
                    '{userid}': str(member.id),
                    '{usertag}': str(member),
                }
                await send_processed_embed(welcome_channel, 'member_leave.json', replacements)

    @nextcord.slash_command(name="joinleave", description="Toggle join/leave message functionality")
    async def toggle_join_leave(
        self, 
        interaction: Interaction,
        action: str = SlashOption(
            description="Enable or disable join/leave messages",
            choices={"Enable": "enable", "Disable": "disable", "Status": "status"}
        )
    ):
        """Toggle join/leave message functionality on or off."""
        # Check if user has permission (you might want to add role checks here)
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "❌ You don't have permission to manage join/leave settings. You need 'Manage Server' permission.",
                ephemeral=True
            )
            return

        if action == "enable":
            self.join_leave_enabled = True
            embed = nextcord.Embed(
                title="✅ Join/Leave Messages Enabled",
                description="Join and leave messages will now be sent to the welcome channel.",
                color=0x00ff00
            )
            await interaction.response.send_message(embed=embed)
            
        elif action == "disable":
            self.join_leave_enabled = False
            embed = nextcord.Embed(
                title="❌ Join/Leave Messages Disabled",
                description="Join and leave messages have been disabled.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed)
            
        elif action == "status":
            status = "✅ Enabled" if self.join_leave_enabled else "❌ Disabled"
            embed = nextcord.Embed(
                title="📊 Join/Leave Messages Status",
                description=f"Current status: {status}",
                color=0x00ff00 if self.join_leave_enabled else 0xff0000
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
            await interaction.response.send_message(embed=embed)

# Function to set up the Cog
def setup(bot):
    bot.add_cog(JoinLeaveHandler(bot))