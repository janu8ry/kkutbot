import core
from .point import Reward
from .attendance import Attendance


async def setup(bot: core.Kkutbot):
    await bot.add_cog(Reward(bot=bot))
    await bot.add_cog(Attendance(bot=bot))
