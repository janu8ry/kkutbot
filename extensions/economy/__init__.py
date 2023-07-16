import core
from .point import Reward


async def setup(bot: core.Kkutbot):
    await bot.add_cog(Reward(bot=bot))
