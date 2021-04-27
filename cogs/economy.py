import random
import time

import discord
from discord.ext import commands

from ext.core import Kkutbot, KkutbotContext
from ext.db import add, config, read, write


class Economy(commands.Cog, name="경제"):
    """끝봇의 포인트에 관련된 명령어들이 있는 카테고리입니다."""

    __slots__ = ("bot", )

    def __init__(self, bot: Kkutbot):
        self.bot = bot

    @commands.command(name="지원금", usage="ㄲ지원금")
    @commands.bot_has_permissions(external_emojis=True)
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def get_start_point(self, ctx: KkutbotContext):
        """[koreanbots](https://koreanbots.dev/bots/703956235900420226) 에서 **하트 추가**를 누르고 지원금을 받아가세요!"""
        write(ctx.author, 'alert.start_point', True)
        if await self.bot.if_koreanbots_voted(ctx.author):
            if not read(ctx.author, 'start_point'):
                add(ctx.author, 'points', 300)
                await ctx.send("+300 {points} 를 받았습니다!")
                write(ctx.author, 'start_point', True)
            else:
                await ctx.send("{denyed} 이미 지원금을 받았습니다.")
        else:
            embed = discord.Embed(
                description="{denyed} "
                            f"[이곳]({config('links.koreanbots')})에서 **하트 추가**를 누른 후 사용해 주세요!\n"
                            "반영까지 1-2분정도 소요 될 수 있습니다.",
                color=config('colors.error')
            )
            await ctx.send(embed=embed)

    @commands.command(name="출석", usage="ㄲ출석", aliases=("ㅊ", "ㅊㅅ"))  # todo: 출석 방식 변경
    @commands.bot_has_permissions(external_emojis=True)
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def daily_check(self, ctx: KkutbotContext):
        """출석체크를 하고 100포인트를 획득합니다."""
        write(ctx.author, 'alert.daily', True)
        options = ''
        week_daily = list()
        week_data = read(ctx.author, 'daily')
        if read(ctx.author, f'daily.{time.localtime().tm_wday}'):
            msg = "{denyed} 이미 출석했습니다. 내일 0시 이후에 다시 시도 해 주세요."
        else:
            add(ctx.author, 'points', 100)
            add(ctx.author, 'daily_times', 1)
            write(ctx.author, f'daily.{time.localtime().tm_wday}', True)
            add(None, 'daily', 1)
            msg = "+100 {points} 를 받았습니다!"
            if all(week_data.values()):
                bonus = random.randint(50, 150)
                add(ctx.author, 'points', bonus)
                options = f"""
                {ctx.author.mention}님은 일주일 동안 모두 출석했습니다!
                
                **추가 보상**
                +{bonus}{{points}}
                """

        week_data = read(ctx.author, 'daily')
        for i in range(time.localtime().tm_wday + 1):
            if week_data[str(i)]:
                week_daily.append(":white_check_mark:")
            else:
                week_daily.append(":x:")
        for _ in range(7 - len(week_daily)):
            week_daily.append(":white_square_button:")

        await ctx.send(f"{msg}\n\n**주간 출석 현황**\n{' '.join(week_daily)}\n\n{options}")

    # @commands.command(name="퀘스트", usage="ㄲ퀘스트", aliases=("과제", "데일리", "미션"), hidden=True)  # todo: 퀘스트 만들기
    # @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    # async def quest(self, ctx: KkutbotContext):
    #     """매일 퀘스트를 클리어하고 보상을 획득합니다."""
    #     embed = discord.Embed(title="데일리 퀘스트", color=config('colors.help'))


def setup(bot: Kkutbot):
    bot.add_cog(Economy(bot))
