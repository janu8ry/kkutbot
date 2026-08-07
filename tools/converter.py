import discord
from discord.ext import commands
from discord.ext.commands.converter import CONVERTER_MAPPING, Converter, GuildConverter  # noqa

__all__ = ["SearchUser", "UserGuildConverter"]


class SearchUser(commands.UserConverter):
    async def convert(self, ctx: commands.Context, argument: str) -> discord.User:
        try:
            return await super().convert(ctx, argument)
        except commands.UserNotFound:
            pass
        try:
            member = await commands.MemberConverter().convert(ctx, argument)
            return member._user  # noqa
        except commands.MemberNotFound:
            pass
        recent = [("latest_usage", -1)]
        doc = await ctx.bot.db.client.user.find_one({"name": argument}, {"_id": 1}, sort=recent) or await ctx.bot.db.client.user.find_one(
            {"global_name": argument}, {"_id": 1}, sort=recent
        )
        if doc:
            if user := ctx.bot.get_user(doc["_id"]):
                return user
            try:
                return await ctx.bot.fetch_user(doc["_id"])
            except discord.NotFound:
                pass
        raise commands.UserNotFound(argument)


CONVERTER_MAPPING[discord.User] = SearchUser


class UserGuildConverter(Converter[discord.Member | discord.User | discord.Guild | str]):
    async def convert(self, ctx: commands.Context, argument: str) -> discord.User | discord.Member | discord.Guild | str:
        argument = argument.lstrip()

        if not argument:
            return "public"
        try:
            return await SearchUser().convert(ctx, argument)
        except commands.UserNotFound:
            pass
        try:
            return await GuildConverter().convert(ctx, argument)
        except commands.GuildNotFound:
            raise commands.BadArgument
