import core

from .announcement import Announcement
from .ranking import Ranking


async def setup(bot: core.Kkutbot):
    await bot.add_cog(Announcement(bot=bot))
    await bot.add_cog(Ranking(bot=bot))
