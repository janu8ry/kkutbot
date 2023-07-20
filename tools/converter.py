import random
import re

import discord
from discord.ext.commands import Context, errors
from discord.ext.commands.converter import Converter, GuildConverter, MemberConverter, UserConverter

from database.models import User

__all__ = ["KkutbotUserConverter", "UserGuildConverter"]


class KkutbotUserConverter(Converter[discord.Member | discord.User]):
    """User & Member Converter without Member Intents"""

    async def convert(self, ctx: Context, argument: str) -> discord.User | discord.Member:
        argument = argument.lstrip()

        if not argument:
            return ctx.author

        try:
            return await MemberConverter().convert(ctx, argument)
        except errors.MemberNotFound:
            pass
        try:
            return await UserConverter().convert(ctx, argument)
        except errors.UserNotFound:
            pass

        if argument.isdecimal():
            user: User = await ctx.bot.db.get_user(int(argument))
            return await ctx.bot.fetch_user(user.id)
        else:
            if re.match(r"<@!?(\d+)>$", argument):
                return await ctx.bot.fetch_user(int(re.findall(r"\d+", argument)[0]))
            else:
                users = await User.find(User.name == str(argument)).to_list()
                if users:
                    user = random.choice(users)
                    return await ctx.bot.fetch_user(user.id)
                else:
                    raise errors.BadArgument


class UserGuildConverter(Converter[discord.Member | discord.User | discord.Guild | str]):
    """Convert argument to User or Guild"""

    async def convert(self, ctx: Context, argument: str) -> discord.User | discord.Member | discord.Guild | str:
        argument = argument.lstrip()

        if not argument:
            return "public"
        try:
            return await KkutbotUserConverter().convert(ctx, argument)
        except errors.BadArgument:
            pass
        try:
            return await GuildConverter().convert(ctx, argument)
        except errors.GuildNotFound:
            raise errors.BadArgument
