import discord
from discord.ext.commands import Context, errors
from discord.ext.commands.converter import Converter, GuildConverter, UserConverter

__all__ = ["UserGuildConverter"]


class UserGuildConverter(Converter[discord.Member | discord.User | discord.Guild | str]):
    """Convert argument to User or Guild"""

    async def convert(self, ctx: Context, argument: str) -> discord.User | discord.Member | discord.Guild | str:
        argument = argument.lstrip()

        if not argument:
            return "public"
        try:
            return await UserConverter().convert(ctx, argument)
        except errors.BadArgument:
            pass
        try:
            return await GuildConverter().convert(ctx, argument)
        except errors.GuildNotFound:
            raise errors.BadArgument
