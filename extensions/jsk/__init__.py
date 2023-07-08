import core
from .jishaku import CustomJSK


async def setup(bot: core.Kkutbot):
    await bot.add_cog(CustomJSK(bot=bot))
