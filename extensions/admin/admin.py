import os
import re
from datetime import datetime

import discord
from discord.ext import commands

from config import config
from core import Kkutbot
from tools.converter import UserGuildConverter
from tools.utils import fmt, is_admin, split_string

from .views import ModifyData, SendAnnouncement


class Admin(commands.Cog, name="관리자"):
    """관리자 전용 명령어들입니다."""

    __slots__ = ("bot",)

    def __init__(self, bot: Kkutbot):
        self.bot = bot

    def cog_check(self, ctx: commands.Context):
        return is_admin(ctx)

    @commands.command(name="$로그", usage="ㄲ$로그 <날짜>")
    async def get_log(self, ctx: commands.Context, date: str = commands.parameter(default=None)):
        """해당 날짜의 로그 파일을 확인합니다."""
        if date is None:
            path = "logs/latest.log"  # noqa
        else:
            now = datetime.now()
            try:
                parts = [int(p) for p in re.split(r"[-/]", date)]
                if not 1 <= len(parts) <= 3:
                    raise ValueError
                if len(parts) == 1:
                    parts = [now.year, now.month, *parts]
                elif len(parts) == 2:
                    parts = [now.year, *parts]
                normalized = datetime(*parts).strftime("%Y-%m-%d")
            except TypeError, ValueError:
                await ctx.reply("날짜 형식이 올바르지 않습니다. (예: `2026-07-05`, `07/05`, `5`)")
                return
            path = f"logs/{normalized}.log.gz"
        if not os.path.isfile(path):
            await ctx.reply(fmt("{denied} 해당 날짜의 로그 파일이 존재하지 않습니다."))
            return
        await ctx.reply(file=discord.File(path))

    @commands.command(name="$백업", usage="ㄲ$백업")
    async def backup_now(self, ctx: commands.Context):
        """현재 데이터베이스를 백업하여 파일로 전송합니다."""
        fp = f"backup/{datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}.gz"
        async with ctx.typing():
            if error := await self.bot.dump_data(fp):
                await ctx.reply(fmt(f"{{denied}} 데이터베이스 백업에 실패했습니다.\n```\n{error}```"))
                return
            try:
                await ctx.reply(file=discord.File(fp))
            finally:
                os.remove(fp)

    @commands.command(name="$정보", usage="ㄲ$정보 <유저>", rest_is_raw=False)
    async def user_info(self, ctx: commands.Context, *, user: discord.User = commands.parameter(default=None)):
        """유저의 (상세)정보를 출력합니다."""
        if user is None:
            public_data = await self.bot.db.get_public()  # noqa
            sorted_data = sorted(public_data.commands.items(), key=lambda item: item[1], reverse=True)
            for content in split_string("\n".join(f"{k}: `{v}`회" for k, v in sorted_data)):
                await ctx.reply(content)
            public_data = public_data.model_dump()
            del public_data["commands"]
            for content in split_string("\n".join(f"{k}: `{v}`" for k, v in public_data.items())):
                await ctx.reply(content)
        else:
            user_data = await self.bot.db.get_user(user)
            if not user_data.registered:
                await ctx.reply(f"`{user.name}`님은 끝봇의 유저가 아닙니다.")
                return
            for content in split_string("\n".join(f"{k}: `{v}`" for k, v in user_data.model_dump().items())):
                await ctx.reply(content)

    @commands.command(name="$서버정보", usage="ㄲ$서버정보 <서버>")
    async def guild_info(self, ctx: commands.Context, *, guild: discord.Guild = commands.CurrentGuild):
        """끝봇을 이용하는 서버의 상세 정보를 출력합니다."""
        guild_data = await self.bot.db.get_guild(guild)
        if not guild_data.invited:
            await ctx.reply(fmt("{denied} 해당 서버는 끝봇을 사용 중인 서버가 아닙니다."))
            return
        guild_data = guild_data.model_dump()
        guild_data["name"] = guild.name
        for content in split_string("\n".join(f"{k}: `{v}`" for k, v in guild_data.items())):
            await ctx.reply(content)

    @commands.command(name="$포인트", usage="ㄲ$포인트 <포인트> <유저>")
    async def give_point(self, ctx: commands.Context, amount: int = 1000, *, user: discord.User = commands.Author):
        """관리자 권한으로 포인트를 지급합니다."""
        if user.bot:
            await ctx.reply(fmt("{denied} 봇에게는 지급할 수 없습니다."))
            return
        user_data = await self.bot.db.get_user(user)
        user_data.points += amount
        await self.bot.db.save(user_data)
        await ctx.reply(fmt("{done} 완료!"))

    @commands.command(name="$메달", usage="ㄲ$메달 <메달> <유저>")
    async def give_medal(self, ctx: commands.Context, amount: int = 10, *, user: discord.User = commands.Author):
        """관리자 권한으로 메달을 지급합니다."""
        if user.bot:
            await ctx.reply(fmt("{denied} 봇에게는 지급할 수 없습니다."))
            return
        user_data = await self.bot.db.get_user(user)
        user_data.medals += amount
        await self.bot.db.save(user_data)
        await ctx.reply(fmt("{done} 완료!"))

    @commands.command(name="$정보수정", usage="ㄲ$정보수정 <대상>")
    async def modify_data(
        self,
        ctx: commands.Context,
        *,
        target: discord.User | discord.Guild = commands.parameter(converter=UserGuildConverter, default="public"),
    ):
        """
        대상의 정보를 수정합니다.
        대상이 주어지지 않았다면 공용 데이터를 수정합니다.
        """
        embed = discord.Embed(title="데이터 수정하기", description=f"대상: {target}", color=config.colors.green)
        view = ModifyData(ctx=ctx, target=target)
        view.message = await ctx.reply(embed=embed, view=view)

    @commands.command(name="$통계삭제", usage="ㄲ$통계삭제 <유저>")
    async def delete_user_data(self, ctx: commands.Context, *, user: discord.User = commands.Author):
        """유저의 데이터를 초기화합니다."""
        data = await self.bot.db.get_user(user)
        if data.registered:
            await data.delete()
            await ctx.reply(fmt("{done} 완료!"))
        else:
            await ctx.reply(fmt("{denied} 해당 유저는 끝봇의 유저가 아닙니다."))

    @commands.command(name="$서버통계삭제", usage="ㄲ$서버통계삭제 <서버>")
    async def delete_guild_data(self, ctx: commands.Context, *, guild: discord.Guild = commands.CurrentGuild):
        """서버의 데이터를 초기화합니다."""
        data = await self.bot.db.get_guild(guild)
        if data.invited:
            await data.delete()
            await ctx.reply(fmt("{done} 완료!"))
        else:
            await ctx.reply(fmt("{denied} 해당 서버는 끝봇을 사용 중인 서버가 아닙니다."))

    @commands.command(name="$서버탈퇴", usage="ㄲ$서버탈퇴 <서버>", aliases=("$탈퇴", "$나가기"))
    async def leave_guild(self, ctx: commands.Context, *, guild: discord.Guild = commands.CurrentGuild):
        """서버를 나갑니다."""
        data = await self.bot.db.get_guild(guild)
        if data.invited:
            await guild.leave()
            await data.delete()
            await ctx.reply(fmt("{done} 완료!"))
        else:
            await ctx.reply(fmt("{denied} 해당 서버는 끝봇을 사용 중인 서버가 아닙니다."))

    @commands.command(name="$공지", usage="ㄲ$공지")
    async def announce_users(self, ctx: commands.Context):
        """끝봇의 유저들에게 공지를 전송합니다."""
        view = SendAnnouncement(ctx=ctx)
        view.message = await ctx.reply("버튼 눌러 공지 작성하기", view=view)
