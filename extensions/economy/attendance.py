import random
from datetime import datetime

import discord
from discord.ext import commands

from config import config
from core import Kkutbot, KkutbotContext


class Attendance(commands.Cog, name="출석"):
    __slots__ = ("bot",)

    def __init__(self, bot: Kkutbot):
        self.bot = bot

    @commands.hybrid_command(name="출석", usage="{attendance}", aliases=("ㅊ", "ㅊㅅ", "ㅊㅊ"))
    @commands.bot_has_permissions(external_emojis=True)
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.user)
    async def attendance(self, ctx: KkutbotContext):
        """
        출석체크를 하고 포인트를 획득합니다.

        일주일동안 매일 출석하면 일요일 출석시 추가 보상을 받을 수 있습니다!

        --사용법
        `/출석`을 사용하여 출석체크를 합니다.
        """
        user = await self.bot.db.get_user(ctx.author)
        user.alerts.attendance = True
        today = datetime.today().toordinal()
        week_today = datetime.today().weekday()
        weekdays = [divmod(today - 1, 7)[0] * 7 + i + 1 for i in range(7)]
        bonus = False

        if user.attendance[str(week_today)] == today:
            embed = discord.Embed(description="{denyed} 이미 출석했습니다. 내일 0시 이후에 다시 시도해 주세요.", color=config.colors.error)
        else:
            user.points += 100
            user.attendance["times"] += 1
            user.attendance[str(week_today)] = today
            public = await self.bot.db.get_public()
            public.attendance += 1
            embed = discord.Embed(title="출석 완료!", description="+`100` {points} 를 받았습니다!", color=config.colors.help)
            embed.add_field(name="", value="")
            weekly = [user.attendance[str(i)] == weekdays[i] for i in range(7)]
            if week_today == 6 and all(weekly):
                bonus = True
                bonus_point = random.randint(100, 200)
                bonus_medal = random.randint(1, 5)
                user.points += bonus_point
                user.medals += bonus_medal
                embed.add_field(name="🔸 보너스 보상", value="일주일동안 모두 출석했습니다!", inline=False)
                embed.add_field(name="", value=f"+`{bonus_point}`{{points}}", inline=False)
                embed.add_field(name="", value=f"+`{bonus_medal}` {{medals}}", inline=True)
                embed.set_thumbnail(url=self.bot.get_emoji(config.emojis["bonus"]).url)
            else:
                embed.set_thumbnail(url=self.bot.get_emoji(config.emojis["attendance"]).url)
                embed.set_footer(text="일주일 동안 매일 출석하고 추가 보상을 받아가세요!")
            await self.bot.db.save(user)
            await self.bot.db.save(public)

        weekly_stats = []
        for i in range(week_today + 1):
            if user.attendance[str(i)] == weekdays[i]:
                weekly_stats.append(":white_check_mark:")
            else:
                weekly_stats.append(":x:")
        for _ in range(6 - week_today):
            weekly_stats.append(":white_square_button:")

        if not bonus:
            embed.add_field(name="🔹 주간 출석 현황", value=" ".join(weekly_stats), inline=False)
        await ctx.reply(embed=embed)
