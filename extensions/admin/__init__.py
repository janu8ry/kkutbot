import core
from .admin import Admin


async def setup(bot: core.Kkutbot):
    await bot.add_cog(Admin(bot))
