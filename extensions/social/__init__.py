import core
from .announcement import Announcement


async def setup(bot: core.Kkutbot):
    await bot.add_cog(Announcement(bot=bot))
