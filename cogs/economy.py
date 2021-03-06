import random
import time
from datetime import datetime

import discord
from discord.ext import commands

from ext.core import Kkutbot, KkutbotContext
from ext.db import add, config, read, write


class Economy(commands.Cog, name="경제"):
    """끝봇의 포인트에 관련된 명령어들이 있는 카테고리입니다."""

    __slots__ = ("bot", )

    def __init__(self, bot: Kkutbot):
        self.bot = bot

    @commands.command(name="포인트", usage="ㄲ포인트", aliases=("ㅍㅇㅌ", "지원금", "ㅈㅇㄱ"))
    @commands.bot_has_permissions(external_emojis=True)
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def get_heart_reward(self, ctx: KkutbotContext):
        """[한국 디스코드봇 리스트](https://koreanbots.dev/bots/703956235900420226) 에서 **하트 추가**를 누르고 포인트를 받습니다.
        하루에 한번씩만 수령 가능합니다.
        """
        await write(ctx.author, 'alert.heart', True)
        if await self.bot.if_koreanbots_voted(ctx.author):
            if (today := datetime.today().toordinal()) != (await read(ctx.author, 'last_reward')):
                points = random.randint(50, 150)
                await add(ctx.author, 'points', points)
                await ctx.reply(f"+{points} {{points}} 를 받았습니다!")
                await write(ctx.author, 'last_reward', today)
            else:
                await ctx.reply("{denyed} 이미 지원금을 받았습니다.\n내일 하트 다시 수령 가능합니다!")
        else:
            embed = discord.Embed(
                description="{denyed} "
                            f"[이곳]({config('links.koreanbots')})에서 **하트 추가**를 누른 후 사용해 주세요!\n"
                            "반영까지 1-2분 정도 소요될 수 있습니다.",
                color=config('colors.error')
            )
            await ctx.reply(embed=embed)

    @commands.command(name="출석", usage="ㄲ출석", aliases=("ㅊ", "ㅊㅅ"))  # todo: 출석 방식 변경
    @commands.bot_has_permissions(external_emojis=True)
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def daily_check(self, ctx: KkutbotContext):
        """출석체크를 하고 100포인트를 획득합니다.
        일주일동안 매일 출석하면 일요일 출석시 추가 보상을 받을 수 있습니다!
        """
        await write(ctx.author, 'alert.daily', True)
        options = ''
        week_daily = []
        week_data = await read(ctx.author, 'daily')
        if await read(ctx.author, f'daily.{time.localtime().tm_wday}'):
            msg = "{denyed} 이미 출석했습니다. 내일 0시 이후에 다시 시도해 주세요."
        else:
            await add(ctx.author, 'points', 100)
            await add(ctx.author, 'daily_times', 1)
            await write(ctx.author, f'daily.{time.localtime().tm_wday}', True)
            await add(None, 'daily', 1)
            msg = "+100 {points} 를 받았습니다!"
            if all(week_data.values()):
                bonus = random.randint(50, 150)
                await add(ctx.author, 'points', bonus)
                options = f"""
{ctx.author.mention}님은 일주일 동안 모두 출석했습니다!
  
**추가 보상**
+`{bonus}`{{points}}
"""

        week_data = await read(ctx.author, 'daily')
        for i in range(time.localtime().tm_wday + 1):
            if week_data[str(i)]:
                week_daily.append(":white_check_mark:")
            else:
                week_daily.append(":x:")
        for _ in range(7 - len(week_daily)):
            week_daily.append(":white_square_button:")

        await ctx.reply(f"{msg}\n\n**주간 출석 현황**\n{' '.join(week_daily)}\n\n{options}")

    @commands.command(name="퀘스트", usage="ㄲ퀘스트", aliases=("ㅋㅅㅌ", "ㅋ", "과제", "데일리", "미션"))
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def quest(self, ctx: KkutbotContext):
        """매일 퀘스트를 클리어하고 보상을 획득합니다.
        퀘스트 항목은 0시에 초기화됩니다."""
        embed = discord.Embed(title="데일리 퀘스트", color=config('colors.help'))
        for data, info in (await read(None, 'quest')).items():
            current = await read(ctx.author, data.replace("/", ".")) - await read(ctx.author, f'quest.cache.{data}')
            if current >= info['target']:
                desc = "이미 완료한 퀘스트입니다."
                title = f"~~{info['name']}~~"
            else:
                desc = f"진행 상황: {round(current, 3)} / {info['target']} (`{round(current / info['target'] * 100, 1)}`%)"
                title = info['name']
            embed.add_field(
                name=f"{title} `{info['reward'][0]}`{{{info['reward'][1]}}}",
                value=desc,
                inline=False
            )
        await ctx.send(embed=embed)


def setup(bot: Kkutbot):
    bot.add_cog(Economy(bot))
