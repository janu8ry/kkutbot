from copy import deepcopy

import discord
from discord.ext import commands

from config import config
from core import Kkutbot, KkutbotContext
from tools.converter import KkutbotUserConverter, UserGuildConverter
from tools.utils import is_admin, split_string
from .views import SendAnnouncement, ModifyData


class Admin(commands.Cog, name="관리자"):
    """관리자 전용 명령어들입니다."""

    __slots__ = ("bot",)

    def __init__(self, bot: Kkutbot):
        self.bot = bot

    def cog_check(self, ctx: KkutbotContext):
        return is_admin(ctx)

    @commands.command(name="$로그", usage="ㄲ$로그 <날짜>")
    async def get_log(self, ctx: KkutbotContext, date: str = None):
        """해당 날짜의 로그 파일을 확인합니다."""
        if date is None:
            path = "logs/latest.log"
        else:
            path = f"logs/{date}.log.gz"
        await ctx.reply(file=discord.File(path))

    @commands.command(name="$정보", usage="ㄲ$정보 <유저>", rest_is_raw=False)
    async def user_info(self, ctx: KkutbotContext, *, user: discord.Member = commands.parameter(converter=KkutbotUserConverter, default=None)):
        """유저의 (상세)정보를 출력합니다."""
        if user is None:
            public_data = await self.bot.db.get_public()
            cmd_data = public_data.commands
            if "jisahku" not in cmd_data:
                cmd_data["jishaku"] = 0
            for k, v in cmd_data.copy().items():
                if k.startswith("jishaku "):
                    cmd_data["jishaku"] += v
                    del cmd_data[k]
            sorted_data = sorted(cmd_data.items(), key=lambda item: item[1], reverse=True)
            for content in split_string("\n".join(f"{k.replace('_', '$')}: `{v}`회" for k, v in sorted_data)):
                await ctx.reply(content, escape_emoji_formatting=True, mention_author=True)
            public_data = deepcopy(public_data.dict())
            del public_data["commands"]
            del public_data["announcements"]
            for content in split_string("\n".join(f"{k}: `{v}`" for k, v in public_data.items())):
                await ctx.reply(content, escape_emoji_formatting=True, mention_author=True)
            return

        user_data = await self.bot.db.get_user(user, safe=False)
        if not user_data:
            return await ctx.reply(f"`{getattr(user, 'name', None)}`님은 끝봇의 유저가 아닙니다.")
        for content in split_string("\n".join(f"{k}: `{v}`" for k, v in user_data.dict().items())):
            await ctx.reply(content, escape_emoji_formatting=True, mention_author=True)

    @commands.command(name="$서버정보", usage="ㄲ$서버정보 <서버>")
    async def guild_info(self, ctx: KkutbotContext, *, guild: discord.Guild = commands.CurrentGuild):
        """끝봇을 이용하는 서버의 상세 정보를 출력합니다."""
        guild_data = await self.bot.db.get_guild(guild, safe=False)
        if not guild_data:
            return await ctx.reply("{denyed} 해당 서버는 끝봇을 사용 중인 서버가 아닙니다.")
        guild_data = guild_data.dict()
        guild_data["name"] = guild.name
        for content in split_string("\n".join(f"{k}: `{v}`" for k, v in guild_data.items())):
            await ctx.reply(content, escape_emoji_formatting=True)

    @commands.command(name="$포인트", usage="ㄲ$포인트 <포인트> <유저>")
    async def give_point(self, ctx: KkutbotContext, amount: int = 1000, *, user: discord.Member = commands.parameter(converter=KkutbotUserConverter, default=None)):
        """관리자 권한으로 포인트를 지급합니다."""
        user_data = await self.bot.db.get_user(user)
        user_data.points += amount
        await self.bot.db.save(user_data)
        await ctx.reply("{done} 완료!")

    @commands.command(name="$메달", usage="ㄲ$메달 <메달> <유저>")
    async def give_medal(self, ctx: KkutbotContext, amount: int = 10, *, user: discord.Member = commands.parameter(converter=KkutbotUserConverter, default=None)):
        """관리자 권한으로 메달을 지급합니다."""
        user_data = await self.bot.db.get_user(user)
        user_data.medals += amount
        await self.bot.db.save(user_data)
        await ctx.reply("{done} 완료!")

    @commands.command(name="$정보수정", usage="ㄲ$정보수정 <대상>")
    async def modify_data(self, ctx: KkutbotContext, *, target: discord.User | discord.Guild | str = commands.parameter(converter=UserGuildConverter, default="public")):
        """
        대상의 정보를 수정합니다.
        대상이 주어지지 않았다면 공용 데이터를 수정합니다.
        """
        embed = discord.Embed(
            title="데이터 수정하기",
            description=f"대상: {target}",
            color=config.colors.help
        )
        view = ModifyData(ctx=ctx, target=target)
        view.message = await ctx.reply(embed=embed, view=view)

    @commands.command(name="$통계삭제", usage="ㄲ$통계삭제 <유저>")
    async def delete_userdata(self, ctx: KkutbotContext, *, user: discord.Member = commands.parameter(converter=KkutbotUserConverter, default=None)):
        """유저의 데이터를 초기화합니다."""
        if data := await self.bot.db.get_user(user, safe=False):
            await data.delete()
            await ctx.reply("{done} 완료!")
        else:
            await ctx.reply("{denyed} 해당 유저는 끝봇의 유저가 아닙니다.")

    @commands.command(name="$서버통계삭제", usage="ㄲ$서버통계삭제 <서버>")
    async def delete_guilddata(self, ctx: KkutbotContext, *, guild: discord.Guild = commands.CurrentGuild):
        """서버의 데이터를 초기화합니다."""
        if data := await self.bot.db.get_guild(guild, safe=False):
            await data.delete()
            await ctx.reply("{done} 완료!")
        else:
            await ctx.reply("{denyed} 해당 서버는 끝봇을 사용 중인 서버가 아닙니다.")

    @commands.command(name="$서버탈퇴", usage="ㄲ$서버탈퇴 <서버>", aliases=("$탈퇴", "$나가기"))
    async def leave_guild(self, ctx: KkutbotContext, *, guild: discord.Guild = commands.CurrentGuild):
        """서버를 나갑니다."""
        if data := await self.bot.db.get_guild(guild, safe=False):
            await guild.leave()
            await data.delete()
            await ctx.reply("{done} 완료!")
        else:
            await ctx.reply("{denyed} 해당 서버는 끝봇을 사용 중인 서버가 아닙니다.")

    @commands.command(name="$공지", usage="ㄲ$공지")
    async def announce_users(self, ctx: KkutbotContext):
        """끝봇의 유저들에게 공지를 전송합니다."""
        view = SendAnnouncement(ctx=ctx)
        view.message = await ctx.reply("버튼 눌러 공지 작성하기", view=view)
