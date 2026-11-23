"""Help and info commands."""

import logging
import random

import nextcord
from nextcord import SlashOption
from nextcord.ext import commands

from database import get_user_info, get_service_events
from database.rank_codes import RANKS
from ..utils import RankManager
from ..config import TESTING_GUILD_ID as GUILD_ID

logger = logging.getLogger(__name__)


class Info(commands.Cog):
    """Cog for help and info commands."""

    def __init__(self, bot):
        self.bot = bot
        self.rank_manager = RankManager()

    @nextcord.slash_command(
        name="ping",
        description="Check that the bot is alive",
        guild_ids=[GUILD_ID] if GUILD_ID else None
    )
    async def ping(self, interaction: nextcord.Interaction):
        msg = "PONG! (╯°□°)╯︵ ┻━┻" if random.randint(1, 50) == 3 else "Pong!"
        await interaction.response.send_message(msg, ephemeral=True)

    @nextcord.slash_command(
        name="ranks",
        description="Show the rank hierarchy",
        guild_ids=[GUILD_ID] if GUILD_ID else None
    )
    async def ranks(self, interaction: nextcord.Interaction):
        """List all ranks, highest first."""
        lines = [f"`{c}` **{r['abbr']}** – {r['name']}" for c, r in reversed(RANKS.items())]
        await interaction.response.send_message(
            embed=nextcord.Embed(title="Rank Hierarchy", description="\n".join(lines), color=0x0099ff),
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
        await interaction.response.defer(ephemeral=True)
        try:
            member = await get_user_info(str(user.id))

            if not member:
                await interaction.followup.send(
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

    @nextcord.slash_command(
        name="service_record",
        description="Show a member's latest service record events",
        guild_ids=[GUILD_ID] if GUILD_ID else None
    )
    async def service_record(
        self,
        interaction: nextcord.Interaction,
        user: nextcord.User = SlashOption(description="Member to look up"),
        rows: int = SlashOption(description="How many events to show (default 10)", default=10, min_value=1, max_value=20)
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


def setup(bot):
    """Add the Info cog to the bot."""
    bot.add_cog(Info(bot))
