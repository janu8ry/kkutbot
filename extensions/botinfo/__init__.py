import core
from .help import Help
from .invite import Invite


async def setup(bot: core.Kkutbot):
    await bot.add_cog(Help(bot=bot))
    await bot.add_cog(Invite(bot=bot))
