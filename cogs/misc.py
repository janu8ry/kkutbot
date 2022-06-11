import asyncio
from datetime import datetime

import discord
from discord.ext import commands
from discord.ext.commands.errors import BadArgument
from discord.utils import escape_markdown as e_mk
from motor.motor_asyncio import AsyncIOMotorCursor  # noqa

from core import Kkutbot, KkutbotContext
from tools.db import read, write
from tools.utils import time_convert
from tools.config import config, get_nested_dict
from tools.paginator import Paginator


class Misc(commands.Cog, name="기타"):
    """끝봇의 기타 명령어들입니다."""

    __slots__ = ("bot", )

    def __init__(self, bot: Kkutbot):
        self.bot = bot

    @commands.command(name="핑", usage="ㄲ핑")
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def ping(self, ctx: KkutbotContext):
        """끝봇의 응답 속도를 확인합니다.
        핑이 지속적으로 400ms 이상일 경우, 관리자에게 제보 부탁드립니다.
        """
        message = await ctx.reply("걸린 시간: `---`ms")
        ms = (message.created_at - ctx.message.created_at).total_seconds() * 1000
        await message.edit(content=f'걸린 시간: `{round(ms)}`**ms**')

    # async def get_user_name(self, user_id: int) -> str:
    #     user = self.bot.get_user(user_id)
    #     if hasattr(user, 'name'):
    #         username = user.name
    #     else:
    #         if await read(user_id, 'name'):
    #             username = await read(user_id, 'name')
    #         else:
    #             username = (await self.bot.fetch_user(user_id)).name
    #     if len(username) >= 15:
    #         username = username[:12] + "..."
    #     return username
    #
    # async def format_rank(self, rank: AsyncIOMotorCursor, query: str) -> list:
    #     rank = await rank.to_list(length=15)
    #     names = await asyncio.gather(*[self.get_user_name(i['_id']) for i in rank])
    #     return [f"**{idx + 1}**. {e_mk(names[idx])} : `{get_nested_dict(i, query.split('.'))}`" for idx, i in enumerate(rank)]
    #
    # @commands.command(name="랭킹", usage="ㄲ랭킹 <분야>", aliases=("ㄹ", "리더보드", "순위", "ㄹㅋ"))
    # @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    # async def ranking(self, ctx: KkutbotContext, *, event="솔로"):
    #     """여러 분야의 TOP 15 랭킹을 확인합니다.
    #     랭킹에 등재되려면 끝말잇기 '솔로' 모드의 티어가 **브론즈** 이상이여야 합니다.
    #
    #     **<분야>**
    #     일반 - 포인트, 출석, 메달, 명령어
    #
    #     게임 - 솔로, 멀티, 쿵쿵따, 온라인, 앞말잇기
    #
    #     **<예시>**
    #     ㄲ랭킹 or ㄲ랭킹 솔로- '솔로' 분야의 랭킹을 확인합니다.
    #     ㄲ랭킹 포인트 - '포인트'가 많은 순서의 랭킹을 확인합니다.
    #     ㄲ랭킹 쿵쿵따 - '쿵쿵따' 분야의 랭킹을 확인합니다.
    #     """
    #     await ctx.typing()
    #     eventlist = {"포인트": 'points', "메달": 'medals', "출석": 'daily_times', "명령어": 'command_used'}
    #     modelist = {"솔로": 'rank_solo', "멀티": 'rank_multi', "쿵쿵따": 'kkd', "온라인": 'online_multi', "앞말잇기": 'apmal'}
    #     rank_query = {
    #         'banned': False,
    #         '_id': {
    #             '$nin': config('bot_whitelist'),
    #             '$ne': self.bot.owner_id
    #         },
    #         'game.rank_solo.tier': {
    #             '$nin': ["언랭크", "뉴비"]
    #         }
    #     }
    #     if event in eventlist:
    #         rank = self.bot.db.user.find(rank_query).sort(eventlist[event], -1)
    #         embed = discord.Embed(
    #             title=f"랭킹 top 15 | {event}",
    #             description="\n".join(await self.format_rank(rank, eventlist[event])),
    #             color=config('colors.help')
    #         )
    #     elif event in modelist:
    #         embed = discord.Embed(title=f"랭킹 top 15 | 끝말잇기 - {event} 모드", color=config('colors.help'))
    #         rank = await asyncio.gather(
    #
    #             self.format_rank(self.bot.db.user.find(rank_query).sort(f"game.{modelist[event]}.winrate", -1), f"game.{modelist[event]}.winrate"),
    #             self.format_rank(self.bot.db.user.find(rank_query).sort(f"game.{modelist[event]}.win", -1), f"game.{modelist[event]}.win"),
    #             self.format_rank(self.bot.db.user.find(rank_query).sort(f"game.{modelist[event]}.best", -1), f"game.{modelist[event]}.best")
    #         )
    #         embed.add_field(name="승률", value="\n".join(rank[0]))
    #         embed.add_field(name="승리수", value="\n".join(rank[1]))
    #         embed.add_field(name="최고점수", value="\n".join(rank[2]))
    #     else:
    #         raise BadArgument
    #     await ctx.send(embed=embed)

    @commands.command(name="메일", usage="ㄲ메일", aliases=("ㅁ", "ㅁㅇ", "메일함", "알림", "공지"))
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def mail(self, ctx: KkutbotContext):
        """끝봇의 공지와 업데이트 소식, 개인 알림 등을 확인합니다."""
        mails = sorted(await read(ctx.author, 'mails') + await read(None, 'announcements'), key=lambda item: item["time"], reverse=True)
        pages = []
        if mails:
            for mail in mails:
                embed = discord.Embed(title=f"{{email}} {ctx.author.name} 님의 메일함", color=config("colors.help"))
                embed.add_field(
                    name=f"🔹 {mail['title']} - `{time_convert(datetime.now() - mail['time'])} 전`",
                    value=mail['value'],
                    inline=False
                )
                pages.append(embed)
        else:
            embed = discord.Embed(
                    title=f"{{email}} {ctx.author.name} 님의 메일함",
                    description="{denyed} 메일함이 비어있습니다!",
                    color=config("colors.help")
                )
            pages.append(embed)
        await write(ctx.author, 'alerts.mails', True)
        await write(ctx.author, 'alerts.announcements', True)
        paginator = Paginator(ctx, pages=pages)
        await paginator.run()

    @commands.command(name="뱝", usage="ㄲ뱝", aliases=("고래뱝", "뱝뱝", "ㄸ뜌"), hidden=True)
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def byab(self, ctx: KkutbotContext):
        """🐳 안녕하세요!"""
        await ctx.send("""
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
""")


async def setup(bot: Kkutbot):
    await bot.add_cog(Misc(bot))
