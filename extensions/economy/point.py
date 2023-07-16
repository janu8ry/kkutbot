import random
from datetime import datetime

import discord
from discord.ext import commands

from config import config
from core import Kkutbot, KkutbotContext
from views import KoreanBotsVote


class Reward(commands.Cog, name="포인트"):
    __slots__ = ("bot",)

    def __init__(self, bot: Kkutbot):
        self.bot = bot

    @commands.hybrid_command(name="포인트", usage="<:points:715547592578170880>", aliases=("ㅍㅇㅌ", "지원금", "ㅈㅇㄱ"))
    @commands.bot_has_permissions(external_emojis=True)
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def reward(self, ctx: KkutbotContext):
        """
        한국 디스코드 리스트에서 하트 추가를 누르고 포인트를 받습니다.

        하루에 한번씩만 수령 가능합니다.
         - 한국 디스코드 리스트: https://koreanbots.dev/bots/703956235900420226/vote

        --사용법
        한국 디스코드 리스트에서 하트를 누른 후 `/포인트` 를 사용하여 포인트를 받습니다.
        """
        user = await self.bot.db.get_user(ctx.author)
        user.alerts.reward = True
        if await self.bot.if_koreanbots_voted(ctx.author):
            if (today := datetime.today().toordinal()) != user.latest_reward:
                points = random.randint(50, 150)
                user.points += points
                embed = discord.Embed(
                    title="포인트 수령 성공!",
                    description=f"+{points} {{points}} 를 받았습니다!",
                    color=config.colors.help
                )
                embed.set_thumbnail(url=self.bot.get_emoji(config.emojis["bonus"]).url)
                user.latest_reward = today
                public = await self.bot.db.get_public()
                public.reward += 1
                await self.bot.db.save(user)
                await self.bot.db.save(public)
                await ctx.reply(embed=embed)
            else:
                embed = discord.Embed(
                    description="{denyed} 이미 지원금을 받았습니다.\n내일 하트 추가 후 다시 수령 가능합니다!",
                    color=config.colors.error
                )
                await ctx.reply(embed=embed)
        else:
            embed = discord.Embed(
                description="{denyed} 한국 디스코드 리스트에서 **하트 추가**를 누른 후 사용해 주세요!\n"
                            "반영까지 1-2분 정도 소요될 수 있습니다.",
                color=config.colors.error
            )
            await ctx.reply(embed=embed, view=KoreanBotsVote())
