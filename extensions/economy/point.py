import random
import time

import discord
from discord.ext import commands

from config import config
from core import Kkutbot
from database.models import User
from tools import fmt

from .views import KoreanBotsVote

__all__ = ["Reward", "is_reward_claimable"]

REWARD_COOLDOWN = 43200
STREAK_KEEP = 129600
STREAK_BONUS_CYCLE = 7


def is_reward_claimable(user: User) -> bool:
    return user.reward.latest is None or round(time.time()) - user.reward.latest >= REWARD_COOLDOWN


class Reward(commands.Cog, name="포인트"):
    __slots__ = ("bot",)

    def __init__(self, bot: Kkutbot):
        self.bot = bot

    @commands.hybrid_command(name="포인트", usage="{points}", aliases=("ㅍㅇㅌ", "지원금", "ㅈㅇㄱ"))
    @commands.bot_has_permissions(external_emojis=True)
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def reward(self, ctx: commands.Context):
        """
        한국 디스코드 리스트에서 하트 추가 후 포인트를 받습니다.

        포인트는 12시간마다 한번씩 수령 가능합니다.
        연속으로 수령하면 연속 횟수가 쌓이고, 7회마다 추가 보상을 받습니다.
         - 한국 디스코드 리스트: https://koreanbots.dev/bots/703956235900420226/vote

        --사용법
        한국 디스코드 리스트에서 하트를 누른 후 `/포인트` 를 사용하여 포인트를 받습니다.
        """
        user = await self.bot.db.get_user(ctx.author)
        if not await self.bot.if_koreanbots_voted(ctx.author):
            embed = discord.Embed(
                description=fmt("{denied} 한국 디스코드 리스트에서 **하트 추가**를 누른 후 사용해 주세요!\n반영까지 1-2분 정도 소요될 수 있습니다."),
                color=config.colors.red,
            )
            await ctx.reply(embed=embed, view=KoreanBotsVote())
            return

        now = round(time.time())
        latest = user.reward.latest or 0
        elapsed = now - latest
        if elapsed < REWARD_COOLDOWN:
            embed = discord.Embed(
                description=fmt(f"{{denied}} 이미 포인트를 받았습니다.\n<t:{latest + REWARD_COOLDOWN}:R>에 다시 수령 가능합니다!"),
                color=config.colors.red,
            )
            await ctx.reply(embed=embed)
            return

        points = random.randint(200, 300)
        user.reward.streak = user.reward.streak + 1 if elapsed <= STREAK_KEEP else 1
        user.points += points
        embed = discord.Embed(
            title="포인트 수령 성공!",
            description=fmt(f"+`{points}` {{points}} 를 받았습니다!\n🔹 연속 수령 `{user.reward.streak}`회"),
            color=config.colors.green,
        )
        if user.reward.streak % STREAK_BONUS_CYCLE == 0:
            bonus = random.randint(400, 600)
            user.points += bonus
            embed.add_field(name="🔸 연속 수령 보너스", value=fmt(f"`{user.reward.streak}`회 연속 수령!\n+`{bonus}` {{points}}"), inline=False)
        embed.set_footer(text=f"{REWARD_COOLDOWN // 3600}시간 후에 다시 수령할 수 있어요!")
        embed.set_thumbnail(url=self.bot.emoji("bonus").url)

        user.reward.latest = now
        user.alerts.reward = False
        public = await self.bot.db.get_public()
        public.reward += 1
        await self.bot.db.save(user)
        await self.bot.db.save(public)
        await ctx.reply(embed=embed)
