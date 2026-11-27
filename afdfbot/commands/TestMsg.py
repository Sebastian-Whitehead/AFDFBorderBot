from typing import Optional

import discord
from discord import Interaction, app_commands
from discord.ext import commands

from ..config import LEADERSHIP_ROLE_ID
from ..utils import send_processed_embed, member_replacements
from ..utils.choices import to_choices


class JohnDoe:
    """Stand-in member: plain-text mention so nobody gets pinged."""
    id = 0
    mention = "@John Doe"
    display_name = "John Doe"

    def __str__(self):
        return "John Doe#0000"


# msg type -> embed file (all use member_replacements)
MESSAGES = {
    "join": "member_join.json",
    "approve": "newcitizen-main.json",
    "enlist": "enlist-welcome.json",
}


class TestMsg(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="test-msg", description="Send a welcome message for a fake member (John Doe)")
    @app_commands.checks.has_role(LEADERSHIP_ROLE_ID)
    @app_commands.describe(msg_type="Which welcome message", channel="Where to send it (default: this channel)")
    @app_commands.choices(msg_type=to_choices(list(MESSAGES)))
    async def test_msg(self, ctx: Interaction, msg_type: str, channel: Optional[discord.TextChannel] = None):
        await ctx.response.defer(ephemeral=True)
        target = channel or ctx.channel
        if await send_processed_embed(target, MESSAGES[msg_type], member_replacements(JohnDoe())):
            await ctx.followup.send(f"✅ Sent the `{msg_type}` message in {target.mention}.", ephemeral=True)
        else:
            await ctx.followup.send(f"❌ Could not send the `{msg_type}` message in {target.mention}.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(TestMsg(bot))
