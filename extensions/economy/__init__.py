import core

from .attendance import Attendance
from .point import Reward
from .quest import Quest


async def setup(bot: core.Kkutbot):
    await bot.add_cog(Reward(bot=bot))
    await bot.add_cog(Attendance(bot=bot))
    await bot.add_cog(Quest(bot=bot))
