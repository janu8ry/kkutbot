import time

import discord
from discord.ext import commands

from config import config
from core import Kkutbot
from tools.utils import fmt, time_convert
from views import Paginator


class Announcement(commands.Cog, name="공지"):
    __slots__ = ("bot",)

    def __init__(self, bot: Kkutbot):
        self.bot = bot

    @commands.hybrid_command(name="공지", usage="{email}", aliases=("ㄱ", "ㄱㅈ", "메일", "알림"))
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def announcement(self, ctx: commands.Context):
        """
        끝봇의 공지와 업데이트 소식을 확인합니다.

        --사용법
        `/공지`를 사용하여 공지사항을 확인합니다.
        """
        user = await self.bot.db.get_user(ctx.author)
        public = await self.bot.db.get_public()
        msgs = sorted(public.announcements, key=lambda item: item["time"], reverse=True)
        pages = []
        if msgs:
            for msg in msgs:
                embed = discord.Embed(title=fmt("{email} 끝봇 공지사항"), color=config.colors.green)
                embed.add_field(name=f"🔹 {msg['title']} - `{time_convert(time.time() - msg['time'])} 전`", value=msg["value"], inline=False)
                pages.append(embed)
        else:
            embed = discord.Embed(title=fmt("{email} 끝봇 공지사항"), description=fmt("{denied} 공지사항이 없습니다."), color=config.colors.green)
            pages.append(embed)
        user.alerts.announcements = True
        await self.bot.db.save(user)
        paginator = Paginator(ctx, pages=pages)
        await paginator.run()
