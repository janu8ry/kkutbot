import re
from typing import Union

import discord
from discord.ext.commands import Context, errors
from discord.ext.commands.converter import (Converter, MemberConverter,
                                            UserConverter)


class SpecialMemberConverter(Converter):
    """User & Member Converter without Member Intents"""

    async def convert(self, ctx: Context, argument: str) -> Union[discord.User, discord.Member]:
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

        if argument.isdecimal():  # if argument is user id
            user = await ctx.bot.db.user.find_one({'_id': int(argument)})
            return await ctx.bot.fetch_user(user['_id'])
        else:
            if re.match(r"<@!?([0-9]+)>$", argument):  # if argument is mention
                return await ctx.bot.fetch_user(int(re.findall(r'\d+', argument)[0]))
            else:
                user = await ctx.bot.db.user.find_one({'_name': str(argument)})
                if user:  # if argument is user name
                    return await ctx.bot.fetch_user(user['_id'])
                else:
                    raise errors.BadArgument
