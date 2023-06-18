import time

import discord
from discord.ext import commands
from motor.motor_asyncio import AsyncIOMotorCursor  # noqa

from config import config
from core import Kkutbot, KkutbotContext
from tools.db import read, write
from tools.utils import time_convert
from views.general import Paginator
from views.social import RankMenu


class Social(commands.Cog, name="소셜"):
    """끝봇의 소셜 기능에 관련된 명령어들입니다."""

    __slots__ = ("bot",)

    def __init__(self, bot: Kkutbot):
        self.bot = bot

    @commands.hybrid_command(name="랭킹", usage="/랭킹", aliases=("ㄹ", "리더보드", "순위", "ㄹㅋ"))
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def ranking(self, ctx: KkutbotContext):
        """여러 분야의 랭킹을 확인합니다.
        끝말잇기 랭킹의 경우, 랭킹에 등재되려면 해당 모드를 50번 이상 플레이 해야 합니다.
        """
        view = RankMenu(ctx)
        view.message = await ctx.reply(embed=await view.get_home_embed(), view=view)

    @commands.hybrid_command(name="메일", usage="/메일", aliases=("ㅁ", "ㅁㅇ", "메일함", "알림", "공지"))
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def mail(self, ctx: KkutbotContext):
        """끝봇의 공지와 업데이트 소식, 개인 알림 등을 확인합니다."""
        mails = sorted(
            await read(ctx.author, "mails") + await read(None, "announcements"),
            key=lambda item: item["time"],
            reverse=True,
        )
        pages = []
        if mails:
            for mail in mails:
                embed = discord.Embed(
                    title=f"{{email}} {ctx.author.name} 님의 메일함",
                    color=config("colors.help"),
                )
                embed.add_field(
                    name=f"🔹 {mail['title']} - `{time_convert(time.time() - mail['time'])} 전`",
                    value=mail["value"],
                    inline=False,
                )
                pages.append(embed)
        else:
            embed = discord.Embed(
                title=f"{{email}} {ctx.author.name} 님의 메일함",
                description="{denyed} 메일함이 비어있습니다!",
                color=config("colors.help"),
            )
            pages.append(embed)
        await write(ctx.author, "alerts.mails", True)
        await write(ctx.author, "alerts.announcements", True)
        paginator = Paginator(ctx, pages=pages)
        await paginator.run()

    @commands.command(name="뱝", usage="ㄲ뱝", aliases=("고래뱝", "뱝뱝", "ㄸ뜌"), hidden=True)
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def byab(self, ctx: KkutbotContext):
        """🐳 안녕하세요!"""
        await ctx.reply(
            """
코로나19로 힘든 시기!
딩가딩가 놀 수만은 없죠.
도움이 필요하실 때에는 어떻게 한다?
우리 고래뱝을 쓴다!
미친듯이 안켜지지만 어쩔 수 없어요...

개발중이라 조금 불안정할 수 있어요!
씹덕봇은 아니니까 걱정하지 않으셔도 돼요.
망한 것 같지만, 좋은 봇입니다! 초대해봐요

**봇 초대 링크**

https://discord.com/oauth2/authorize?client_id=732773322286432416&permissions=336066630&scope=bot
"""
        )


async def setup(bot: Kkutbot):
    await bot.add_cog(Social(bot))
