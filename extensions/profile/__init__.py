import core

from .profile import Profile


async def setup(bot: core.Kkutbot):
    await bot.add_cog(Profile(bot=bot))
