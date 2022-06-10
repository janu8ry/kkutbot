import random
import time
from datetime import datetime

import discord
from discord.ext import commands

from core import Kkutbot, KkutbotContext
from tools.db import add, read, write
from tools.config import config
from tools.views import KoreanBotsVote


class Economy(commands.Cog, name="경제"):
    """끝봇의 포인트, 메달에 관련된 명령어들입니다."""

    __slots__ = ("bot",)

    def __init__(self, bot: Kkutbot):
        self.bot = bot

    @commands.command(name="포인트", usage="ㄲ포인트", aliases=("ㅍㅇㅌ", "지원금", "ㅈㅇㄱ"))
    @commands.bot_has_permissions(external_emojis=True)
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def get_heart_reward(self, ctx: KkutbotContext):
        """[한국 디스코드 리스트](https://koreanbots.dev/bots/703956235900420226) 에서 **하트 추가**를 누르고 포인트를 받습니다.
        하루에 한번씩만 수령 가능합니다.
        """
        await write(ctx.author, 'alerts.reward', True)
        if await self.bot.if_koreanbots_voted(ctx.author):
            if (today := datetime.today().toordinal()) != (await read(ctx.author, 'latest_reward')):
                points = random.randint(50, 150)
                await add(ctx.author, 'points', points)
                embed = discord.Embed(
                    title="포인트 수령 성공!",
                    description=f"+{points} {{points}} 를 받았습니다!",
                    color=config("colors.help")
                )
                embed.set_thumbnail(url=self.bot.get_emoji(config('emojis.bonus')).url)
                await write(ctx.author, 'latest_reward', today)
                await ctx.reply(embed=embed)
            else:
                embed = discord.Embed(
                    description="{denyed} 이미 지원금을 받았습니다.\n내일 하트 추가 후 다시 수령 가능합니다!",
                    color=config("colors.error")
                )
                await ctx.reply(embed=embed)
        else:
            embed = discord.Embed(
                description="{denyed} "
                            "한국 디스코드 리스트에서 **하트 추가**를 누른 후 사용해 주세요!\n"
                            "반영까지 1-2분 정도 소요될 수 있습니다.",
                color=config('colors.error')
            )
            await ctx.reply(embed=embed, view=KoreanBotsVote())

    @commands.command(name="출석", usage="ㄲ출석", aliases=("ㅊ", "ㅊㅅ"))
    @commands.bot_has_permissions(external_emojis=True)
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def daily_check(self, ctx: KkutbotContext):
        """출석체크를 하고 100포인트를 획득합니다.
        일주일동안 매일 출석하면 일요일 출석시 추가 보상을 받을 수 있습니다!
        """
        await write(ctx.author, 'alerts.attendance', True)
        bonus = False
        week_daily = []
        week_data = await read(ctx.author, 'attendance')
        today = datetime.today().toordinal()
        week_today = time.localtime().tm_wday
        if week_data[str(week_today)] == today:
            msg = "{denyed} 이미 출석했습니다. 내일 0시 이후에 다시 시도해 주세요."
            success = False
        else:
            await add(ctx.author, 'points', 100)
            await add(ctx.author, 'attendance_times', 1)
            await write(ctx.author, f'attendance.{week_today}', today)
            await add(None, 'attendance', 1)
            msg = "+100 {points} 를 받았습니다!"
            success = True
            week_data = await read(ctx.author, 'attendance')
            if (week_today == 6) and (list(week_data.values()) == [today - i + 1 for i in range(7, 0, -1)]):
                bonus_point = random.randint(100, 200)
                await add(ctx.author, 'points', bonus_point)
                await add(ctx.author, 'medals', 1)
                bonus = True

        for i in range(week_today + 1):
            if week_data[str(i)]:
                week_daily.append(":white_check_mark:")
            else:
                week_daily.append(":x:")
        for _ in range(7 - len(week_daily)):
            week_daily.append(":white_square_button:")

        embed = discord.Embed(
            description=f"{msg}",
            color=config(f"colors.{'help' if success else 'error'}")
        )
        embed.add_field(name="주간 출석 현황", value=' '.join(week_daily))
        if success:
            embed.set_thumbnail(url=self.bot.get_emoji(config('emojis.attendance')).url)
        await ctx.reply(embed=embed)
        if bonus:
            bonus_embed = discord.Embed(
                description="일주일 동안 모두 출석했습니다!",
                color=config("colors.info")
            )
            bonus_embed.add_field(name="추가 보상", value=f"+`{bonus_point}`{{points}}\n+`1`{{medals}}")  # noqa
            embed.set_thumbnail(url=self.bot.get_emoji(config('emojis.bonus')).url)
            await ctx.reply(embed=embed)

    @commands.command(name="퀘스트", usage="ㄲ퀘스트", aliases=("ㅋㅅㅌ", "ㅋ", "과제", "데일리", "미션"))
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def quest(self, ctx: KkutbotContext):
        """매일 퀘스트를 클리어하고 보상을 획득합니다.
        퀘스트 항목은 0시에 초기화됩니다."""
        embed = discord.Embed(
            title="데일리 퀘스트",
            description="끝봇을 사용하며 퀘스트를 클리어하고, 보상을 획득하세요!",
            color=config('colors.help')
        )
        for data, info in (await read(None, 'quests')).items():
            current = await read(ctx.author, data.replace("/", ".")) - await read(ctx.author, f'quest.cache.{data}')
            if current >= info['target']:
                desc = "이 퀘스트를 완료했습니다!"
                title = f"~~{info['name']}~~"
            else:
                desc = f"진행 상황: {round(current, 3)} / {info['target']} (`{round(current / info['target'] * 100, 1)}`%)"
                title = info['name']
            embed.add_field(
                name=f"🔹 {title} `{info['reward'][0]}`{{{info['reward'][1]}}}",
                value=desc,
                inline=False
            )
        embed.set_thumbnail(url=self.bot.get_emoji(config('emojis.quest')).url)
        await ctx.reply(embed=embed)


async def setup(bot: Kkutbot):
    await bot.add_cog(Economy(bot))
