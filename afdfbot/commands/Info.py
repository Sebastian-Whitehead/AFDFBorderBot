"""Help and info commands."""

import logging
import random

import discord
from discord import app_commands
from discord.ext import commands

from database import get_user_info, get_service_events
from database.rank_codes import RANKS
from ..utils import RankManager

logger = logging.getLogger(__name__)


class Info(commands.Cog):
    """Cog for help and info commands."""

    def __init__(self, bot):
        self.bot = bot
        self.rank_manager = RankManager()

    @app_commands.command(
        name="ping",
        description="Check that the bot is alive"
    )
    async def ping(self, interaction: discord.Interaction):
        msg = "PONG! (╯°□°)╯︵ ┻━┻" if random.randint(1, 50) == 3 else "Pong!"
        await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(
        name="ranks",
        description="Show the rank hierarchy"
    )
    async def ranks(self, interaction: discord.Interaction):
        """List all ranks, highest first."""
        lines = [f"`{c}` **{r['abbr']}** – {r['name']}" for c, r in reversed(RANKS.items())]
        await interaction.response.send_message(
            embed=discord.Embed(title="Rank Hierarchy", description="\n".join(lines), color=0x0099ff),
            ephemeral=True
        )

    @app_commands.command(
        name="profile",
        description="View a member's profile and statistics"
    )
    @app_commands.describe(user="User to view profile for")
    async def view_profile(
        self,
        interaction: discord.Interaction,
        user: discord.User
    ):
        """View a member's profile and statistics."""
        await interaction.response.defer(ephemeral=True)
        try:
            member = await get_user_info(str(user.id))

            if not member:
                await interaction.followup.send(
                    f"❌ {user.mention} is not found in the database.",
                    ephemeral=True
                )
                return

            embed = discord.Embed(
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
                value=self.rank_manager.rank_text(member["rank"]), 
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
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error viewing profile: {e}")
            await interaction.followup.send(
                f"❌ Failed to load profile: {str(e)}", 
                ephemeral=True
            )

    @app_commands.command(
        name="service_record",
        description="Show a member's latest service record events"
    )
    @app_commands.describe(user="Member to look up", rows="How many events to show (default 10)")
    async def service_record(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        rows: app_commands.Range[int, 1, 20] = 10
    ):
        await interaction.response.defer(ephemeral=True)
        events = await get_service_events(str(user.id), rows)
        if events is None:
            await interaction.followup.send(
                f"❌ {user.mention} has no service record (or the database is unavailable).", ephemeral=True)
            return
        if not events:
            await interaction.followup.send(f"{user.mention} has no events on their service record.")
            return
        # Discord doesn't render markdown tables, so pad the columns inside a code block.
        table = [("ID", "Date", "Event", "Rank", "Notes")] + [
            (str(e["id"]), e["occured_at"].strftime("%Y-%m-%d"), e["event_type"], e["rank"] or "-",
             " ".join((e["notes"] or "-").split())[:30]) for e in events]
        w = [max(len(r[i]) for r in table) for i in range(5)]
        lines = ["| " + " | ".join(c.ljust(w[i]) for i, c in enumerate(r)) + " |" for r in table]
        lines.insert(1, "|" + "|".join("-" * (n + 2) for n in w) + "|")
        await interaction.followup.send(
            f"Last {len(events)} service events for {user.mention}:\n```\n" + "\n".join(lines) + "\n```")


async def setup(bot):
    """Add the Info cog to the bot."""
    await bot.add_cog(Info(bot))
