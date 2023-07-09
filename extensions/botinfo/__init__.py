import core
from .help import Help


async def setup(bot: core.Kkutbot):
    await bot.add_cog(Help(bot=bot))
