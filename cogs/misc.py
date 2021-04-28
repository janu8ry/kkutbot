import asyncio
from datetime import datetime

import discord
from discord.ext import commands
from discord.ext.commands.errors import BadArgument
from discord.utils import escape_markdown as e_mk
from pymongo import DESCENDING, cursor

from ext import utils
from ext.core import Kkutbot, KkutbotContext
from ext.db import config, get, read, write


class Misc(commands.Cog, name="기타"):
    """끝봇의 기타 명령어들에 대한 카테고리입니다."""

    __slots__ = ("bot", )

    def __init__(self, bot: Kkutbot):
        self.bot = bot

    @commands.command(name="핑", usage="ㄲ핑")
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def ping(self, ctx: KkutbotContext):
        """끝봇의 응답 속도를 확인합니다."""
        message = await ctx.send("걸린 시간: `---`ms")
        ms = (message.created_at - ctx.message.created_at).total_seconds() * 1000
        await message.edit(content=f'걸린 시간: `{round(ms)}`**ms**')

    async def get_user_name(self, user_id: int) -> str:
        user = self.bot.get_user(user_id)
        if hasattr(user, 'name'):
            username = user.name
        else:
            if read(user_id, '_name'):
                username = read(user_id, '_name')
            else:
                username = (await self.bot.fetch_user(user_id)).name
        if len(username) >= 15:
            username = username[:12] + "..."
        return username

    async def format_rank(self, rank: cursor.Cursor, query: str) -> list:
        rank = list(rank)
        names = await asyncio.gather(*[self.get_user_name(i['_id']) for i in rank])
        return [f"**{idx + 1}**. {e_mk(names[idx])} : `{get(i, query.split('.'))}`" for idx, i in enumerate(rank)]

    @commands.command(name="랭킹", usage="ㄲ랭킹 <분야>", aliases=("ㄹ", "리더보드", "순위", "ㄹㅋ"))  # todo: 서버랭킹
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def ranking(self, ctx: KkutbotContext, *, event="솔로"):
        """여러 분야의 top10 랭킹을 확입합니다.

        **<분야>**
        일반 - 포인트, 출석, 메달, 명령어

        게임 - 솔로, 멀티, 쿵쿵따, 온라인, 앞말잇기, 서버

        랭킹에 등재되려면 끝말잇기 게임을 20번 이상 플레이해야 합니다."""
        await ctx.trigger_typing()
        eventlist = {"포인트": 'points', "메달": 'medal', "출석": 'daily_times', "명령어": 'command_used'}
        modelist = {"솔로": 'rank_solo', "멀티": 'rank_multi', "쿵쿵따": 'kkd', "온라인": 'online_multi', "앞말잇기": 'apmal'}
        rank_query = {
                'banned': False,
                '_id': {
                    '$nin': config('bot_whitelist'),
                    '$ne': self.bot.owner_id
                }  # 'game.rank_solo.tier': {'$nin': ["언랭크", "뉴비"]}
        }
        if event in eventlist:
            rank = self.bot.db.user.find(rank_query).sort(eventlist[event], DESCENDING).limit(15)
            embed = discord.Embed(title=f"랭킹 top 15 | {event}", description="\n".join(await self.format_rank(rank, eventlist[event])), color=config('colors.help'))
        elif event in modelist:
            embed = discord.Embed(title=f"랭킹 top 15 | 끝말잇기 - {event} 모드", color=config('colors.help'))
            # rank_winrate = self.bot.db.user.find(rank_query).sort({f"game.{modelist[event]}.win": DESCENDING}).limit(15)  # noqa todo: 승률 랭킹 개선
            rank = await asyncio.gather(
                # self.format_rank(self.bot.db.user.find(rank_query).where(f"this.game.{modelist[event]}.win / this.game.{modelist[event]}.times * 100")),
                self.format_rank(self.bot.db.user.find(rank_query).sort(f"game.{modelist[event]}.win", DESCENDING).limit(15), f"game.{modelist[event]}.win"),
                self.format_rank(self.bot.db.user.find(rank_query).sort(f"game.{modelist[event]}.best", DESCENDING).limit(15), f"game.{modelist[event]}.best")
            )
            # embed.add_field(name="승률", value="\n".join(rank[0]))
            embed.add_field(name="승리수", value="\n".join(rank[1]))
            embed.add_field(name="최고점수", value="\n".join(rank[2]))
        else:
            raise BadArgument
        await ctx.send(embed=embed)

    @commands.command(name="메일", usage="ㄲ메일", aliases=("ㅁ", "ㅁㅇ", "메일함", "알림", "공지"))
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def mail(self, ctx: KkutbotContext):
        """끝봇의 공지와 업데이트 소식, 개인 알림 등을 확인합니다.

        수신한지 2주가 지난 미확인 메일은 자동으로 삭제됩니다."""
        if not read(ctx.author, 'mail'):
            embed = discord.Embed(title=f"**{ctx.author.name}** 님의 메일함", description="> 읽지 않은 메일이 없습니다.", color=config('colors.general'))
            return await ctx.send(embed=embed)
        embed = discord.Embed(title=f"**{ctx.author.name}** 님의 메일함", description=f"> 2주 동안 읽지 않은 메일 `{len(read(ctx.author, 'mail'))}` 개", color=config('colors.general'))
        for x in read(ctx.author, 'mail'):
            if (datetime.now() - x['time']).days <= 14:
                embed.add_field(name=f"{x['title']} - `{utils.time_convert(datetime.now() - x['time'])} 전`", value=x['value'], inline=False)
        write(ctx.author, 'mail', list())
        write(ctx.author, 'alert.mail', True)
        await ctx.send(embed=embed)


def setup(bot: Kkutbot):
    bot.add_cog(Misc(bot))
