import core

from .game import Game


async def setup(bot: core.Kkutbot):
    await bot.add_cog(Game(bot=bot))
