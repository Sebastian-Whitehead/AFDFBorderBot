import logging
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks

from ..config import TESTING_GUILD_ID, CHECKPOINT_CHANNEL_ID, get_setting
from ..utils import send_processed_embed
from .BorderOfficerMonitor import DEFAULT_CHECK_INTERVAL

logger = logging.getLogger(__name__)

OFFICE_TITLE = "Outside office hours"  # must match embeds/office_hours.json


def in_office_hours(hour: int, start: int, end: int) -> bool:
    """True if `hour` is within [start, end); a range like 22-6 wraps past midnight."""
    return start <= hour < end if start < end else hour >= start or hour < end


class OfficeHoursMonitor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.msg = None

    async def cog_load(self):
        self.check_office_hours.start()

    async def cog_unload(self):
        self.check_office_hours.cancel()

    @tasks.loop(seconds=DEFAULT_CHECK_INTERVAL)
    async def check_office_hours(self):
        guild = self.bot.get_guild(TESTING_GUILD_ID) if TESTING_GUILD_ID else None
        channel = guild.get_channel(CHECKPOINT_CHANNEL_ID) if guild and CHECKPOINT_CHANNEL_ID else None
        if not channel:
            logger.warning("OfficeHoursMonitor: guild or checkpoint channel not found")
            return

        # Shares the border officer check interval; applies from the next cycle
        interval = get_setting('border-officer-check-interval', DEFAULT_CHECK_INTERVAL)
        if self.check_office_hours.seconds != interval:
            self.check_office_hours.change_interval(seconds=interval)

        enabled = get_setting('office-hours-enabled', False)
        hour = datetime.now(timezone.utc).hour
        closed = enabled and not in_office_hours(
            hour, get_setting('office-hours-start', 9), get_setting('office-hours-end', 17)
        )

        try:
            # Forget a warning that was deleted by hand, and recover one left over from before a restart
            if self.msg:
                try:
                    await channel.fetch_message(self.msg.id)
                except discord.NotFound:
                    self.msg = None
            else:
                async for m in channel.history(limit=50):
                    if m.author == self.bot.user and m.embeds and m.embeds[0].title == OFFICE_TITLE:
                        self.msg = m
                        break

            if closed and not self.msg:
                self.msg = await send_processed_embed(channel, "office_hours.json", {})
            elif not closed and self.msg:
                await self.msg.delete()
                self.msg = None
        except discord.NotFound:
            self.msg = None  # already gone, which is the state wanted when opening
        except discord.HTTPException:
            logger.exception("OfficeHoursMonitor: failed to update office hours message, will retry")

    @check_office_hours.error
    async def check_office_hours_error(self, error):
        logger.error("OfficeHoursMonitor: loop stopped by an unhandled error", exc_info=error)

    @check_office_hours.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(OfficeHoursMonitor(bot))
