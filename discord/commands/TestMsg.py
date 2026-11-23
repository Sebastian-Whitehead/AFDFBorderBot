from typing import Optional

import nextcord
from nextcord import Interaction, SlashOption
from nextcord.ext import application_checks, commands

from ..config import LEADERSHIP_ROLE_ID, TESTING_GUILD_ID
from ..utils import send_processed_embed, member_replacements


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

    @nextcord.slash_command(name="test-msg", description="Send a welcome message for a fake member (John Doe)",
                            guild_ids=[TESTING_GUILD_ID] if TESTING_GUILD_ID else None)
    @application_checks.has_role(LEADERSHIP_ROLE_ID)
    async def test_msg(self, ctx: Interaction,
                       msg_type: str = SlashOption(name="msg_type", description="Which welcome message", choices=list(MESSAGES)),
                       channel: Optional[nextcord.TextChannel] = SlashOption(description="Where to send it (default: this channel)", required=False, default=None)):
        await ctx.response.defer(ephemeral=True)
        target = channel or ctx.channel
        if await send_processed_embed(target, MESSAGES[msg_type], member_replacements(JohnDoe())):
            await ctx.followup.send(f"✅ Sent the `{msg_type}` message in {target.mention}.", ephemeral=True)
        else:
            await ctx.followup.send(f"❌ Could not send the `{msg_type}` message in {target.mention}.", ephemeral=True)


def setup(bot):
    bot.add_cog(TestMsg(bot))
